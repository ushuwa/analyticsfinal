from collections import defaultdict, Counter
from statistics import mean
from db import get_db_connection


def clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.lower() in {"nan", "none", "null"}:
        return None
    return value


def clean_number(value, min_value=None, max_value=None):
    if value is None:
        return None

    try:
        value = str(value).strip().replace("%", "").replace(",", "")
        if value == "" or value.lower() in {"nan", "none", "null"}:
            return None

        num = float(value)

        if min_value is not None and num < min_value:
            return None
        if max_value is not None and num > max_value:
            return None

        return num
    except Exception:
        return None


def get_client_key(cid, memname):
    cid_clean = clean_text(cid)
    memname_clean = clean_text(memname)
    return cid_clean if cid_clean else memname_clean


def classify_poverty(avg_ppi):
    avg_ppi = 0 if avg_ppi is None else avg_ppi
    return "Pagtalubo" if avg_ppi <= 35 else "Regular"


def poverty_likelihood_probability(avg_ppi):
    avg_ppi = 0 if avg_ppi is None else avg_ppi

    if avg_ppi <= 35:
        return round(0.80 + ((35 - avg_ppi) / 35) * 0.20, 4)
    if avg_ppi <= 50:
        return round(0.50 + ((50 - avg_ppi) / 15) * 0.29, 4)
    if avg_ppi <= 70:
        return round(0.20 + ((70 - avg_ppi) / 20) * 0.29, 4)

    return round(max(0.01, 0.20 - ((avg_ppi - 70) / 30) * 0.19), 4)


def get_latest_batch_id():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT batch_id FROM client_ppi_upload_batch ORDER BY batch_id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def normalize_education_level(value):
    text = clean_text(value)
    if not text:
        return "Unknown"

    t = text.lower()

    if "elementary" in t or "grade school" in t or "primary" in t or "elem" in t:
        return "Elementary"

    if "high school" in t or "junior high" in t or "senior high" in t or "secondary" in t or "hs" in t:
        return "High School"

    if "college" in t or "tertiary" in t or "university" in t:
        return "College/SLT High"

    if "vocational" in t or "tesda" in t or "technical" in t:
        return "College/SLT High"

    return "Other"


def education_priority_weight(education_level):
    mapping = {
        "Elementary": 50,
        "High School": 70,
        "College/SLT High": 90,
        "Other": 40,
        "Unknown": 20
    }
    return mapping.get(education_level, 20)


def fetch_scholarship_rows(batch_id=None):
    if batch_id is None:
        batch_id = get_latest_batch_id()

    if batch_id is None:
        return []

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            batch_id,
            cid,
            memname,
            area_office,
            unit_office,
            center_office,
            ppiscore,
            name,
            benage,
            bnstatus,
            education
        FROM client_ppi_raw
        WHERE batch_id = %s
        """,
        (batch_id,)
    )

    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    return [dict(zip(colnames, row)) for row in rows]


def build_client_profiles(rows):
    clients = {}

    for row in rows:
        client_key = get_client_key(row.get("cid"), row.get("memname"))
        if not client_key:
            continue

        ppi_value = clean_number(row.get("ppiscore"), 0, 100)

        if client_key not in clients:
            clients[client_key] = {
                "clientKey": client_key,
                "cid": clean_text(row.get("cid")),
                "clientName": clean_text(row.get("memname")),
                "area": clean_text(row.get("area_office")),
                "unit": clean_text(row.get("unit_office")),
                "center": clean_text(row.get("center_office")),
                "ppiValues": []
            }

        if ppi_value is not None:
            clients[client_key]["ppiValues"].append(ppi_value)

    for client in clients.values():
        avg_ppi = round(mean(client["ppiValues"]), 2) if client["ppiValues"] else 0.0
        client["averagePpi"] = avg_ppi
        client["povertyLikelihood"] = round(poverty_likelihood_probability(avg_ppi) * 100, 2)
        client["povertyClassification"] = classify_poverty(avg_ppi)

    return clients


def is_eligible_dependent(dependent):
    if not dependent["dependentName"]:
        return False

    if dependent["age"] is None:
        return False

    if dependent["educationLevel"] in {"Unknown", None}:
        return False

    # Scholarship-friendly age window
    if dependent["age"] < 5 or dependent["age"] > 24:
        return False

    return True


def compute_priority_score(dependent):
    poverty_likelihood = dependent["povertyLikelihood"]
    household_ppi = dependent["householdPpi"]
    education_weight = education_priority_weight(dependent["educationLevel"])

    inverse_ppi = max(0, 100 - household_ppi)

    # Weighted analytical ranking
    score = (
        poverty_likelihood * 0.55 +
        inverse_ppi * 0.30 +
        education_weight * 0.15
    )

    return round(score, 2)


def build_dependents(rows):
    clients = build_client_profiles(rows)
    dependents = {}
    batch_id = rows[0]["batch_id"] if rows else None

    for row in rows:
        client_key = get_client_key(row.get("cid"), row.get("memname"))
        if not client_key or client_key not in clients:
            continue

        dependent_name = clean_text(row.get("name"))
        age = clean_number(row.get("benage"), 0, 120)
        bnstatus = clean_text(row.get("bnstatus"))
        education_raw = clean_text(row.get("education"))
        education_level = normalize_education_level(education_raw)

        if not dependent_name:
            continue

        dependent_key = (
            client_key,
            dependent_name.lower(),
            int(age) if age is not None else None,
            (bnstatus or "").lower(),
            (education_raw or "").lower()
        )

        if dependent_key in dependents:
            continue

        client = clients[client_key]

        dependent = {
            "batchId": batch_id,
            "clientKey": client_key,
            "cid": client["cid"],
            "clientName": client["clientName"],
            "area": client["area"],
            "unit": client["unit"],
            "center": client["center"],
            "dependentName": dependent_name,
            "age": int(age) if age is not None else None,
            "bnstatus": bnstatus,
            "education": education_raw,
            "educationLevel": education_level,
            "householdPpi": client["averagePpi"],
            "povertyLikelihood": client["povertyLikelihood"],
            "povertyClassification": client["povertyClassification"]
        }

        dependent["eligible"] = is_eligible_dependent(dependent)
        dependent["priorityScore"] = compute_priority_score(dependent)

        dependent["priorityLevel"] = (
            "High Priority"
            if dependent["eligible"] and dependent["priorityScore"] >= 65
            else "Standard"
        )

        dependents[dependent_key] = dependent

    return list(dependents.values())


def apply_branch_filter(records, branch_level=None, branch_value=None):
    if not branch_level or not branch_value:
        return records

    branch_map = {
        "area": "area",
        "unit": "unit",
        "center": "center"
    }

    if branch_level not in branch_map:
        return records

    field = branch_map[branch_level]
    target = str(branch_value).strip().lower()

    return [
        r for r in records
        if r.get(field) and str(r.get(field)).strip().lower() == target
    ]


def get_scholarship_dashboard(batch_id=None, branch_level=None, branch_value=None, limit=100):
    rows = fetch_scholarship_rows(batch_id=batch_id)
    dependents = build_dependents(rows)
    dependents = apply_branch_filter(dependents, branch_level=branch_level, branch_value=branch_value)

    total_dependents = len(dependents)
    eligible_dependents = [d for d in dependents if d["eligible"]]
    high_priority_dependents = [d for d in eligible_dependents if d["priorityLevel"] == "High Priority"]

    education_counter = Counter()
    for dep in eligible_dependents:
        education_counter[dep["educationLevel"]] += 1

    education_distribution = [
        {"educationLevel": level, "count": count}
        for level, count in education_counter.items()
    ]
    education_distribution.sort(key=lambda x: (-x["count"], x["educationLevel"]))

    high_priority_table = sorted(
        high_priority_dependents,
        key=lambda x: (-x["priorityScore"], x["clientName"] or "", x["dependentName"] or "")
    )[:limit]

    return {
        "summary": {
            "totalDependents": total_dependents,
            "eligibleDependents": len(eligible_dependents),
            "highPriorityDependents": len(high_priority_dependents)
        },
        "educationLevelDistribution": education_distribution,
        "highPriorityDependents": [
            {
                "cid": d["cid"],
                "nameOfClient": d["clientName"],
                "dependentName": d["dependentName"],
                "age": d["age"],
                "education": d["education"],
                "educationLevel": d["educationLevel"],
                "area": d["area"],
                "unit": d["unit"],
                "center": d["center"],
                "householdPpi": d["householdPpi"],
                "povertyLikelihood": d["povertyLikelihood"],
                "priorityScore": d["priorityScore"],
                "priorityLevel": d["priorityLevel"]
            }
            for d in high_priority_table
        ]
    }


def get_scholarship_recommendations(batch_id=None, branch_level=None, branch_value=None, limit=100):
    rows = fetch_scholarship_rows(batch_id=batch_id)
    dependents = build_dependents(rows)
    dependents = apply_branch_filter(dependents, branch_level=branch_level, branch_value=branch_value)

    recommendations = [
        d for d in dependents
        if d["eligible"]
    ]

    recommendations.sort(
        key=lambda x: (
            -x["priorityScore"],
            0 if x["povertyClassification"] == "Pagtalubo" else 1,
            x["householdPpi"]
        )
    )

    return [
        {
            "cid": d["cid"],
            "nameOfClient": d["clientName"],
            "dependentName": d["dependentName"],
            "age": d["age"],
            "bnstatus": d["bnstatus"],
            "education": d["education"],
            "educationLevel": d["educationLevel"],
            "area": d["area"],
            "unit": d["unit"],
            "center": d["center"],
            "householdPpi": d["householdPpi"],
            "povertyLikelihood": d["povertyLikelihood"],
            "povertyClassification": d["povertyClassification"],
            "priorityScore": d["priorityScore"],
            "priorityLevel": d["priorityLevel"]
        }
        for d in recommendations[:limit]
    ]