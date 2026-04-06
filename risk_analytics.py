from collections import defaultdict
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


def get_latest_batch_id():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT batch_id FROM client_ppi_upload_batch ORDER BY batch_id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def get_previous_batch_id(current_batch_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT batch_id
        FROM client_ppi_upload_batch
        WHERE batch_id < %s
        ORDER BY batch_id DESC
        LIMIT 1
        """,
        (current_batch_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def fetch_risk_rows(batch_id=None):
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
            prov,
            city,
            daysarrears,
            lpeightw,
            principal,
            adjendbalprin,
            term,
            termpaid,
            cycle,
            savingsbal,
            ppiscore
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


def compute_risk_score(row):
    """
    Python analytical scoring model.
    Higher score = higher risk.
    Scaled roughly to 0-100.
    """
    days_arrears = clean_number(row.get("daysarrears"), 0)
    lpeightw = clean_number(row.get("lpeightw"), 0)
    principal = clean_number(row.get("principal"), 0)
    savingsbal = clean_number(row.get("savingsbal"), 0)
    term = clean_number(row.get("term"), 0)
    termpaid = clean_number(row.get("termpaid"), 0)
    cycle = clean_number(row.get("cycle"), 0)
    ppiscore = clean_number(row.get("ppiscore"), 0, 100)

    score = 0.0

    # 1. arrears pressure
    if days_arrears is not None:
        if days_arrears >= 90:
            score += 40
        elif days_arrears >= 60:
            score += 30
        elif days_arrears >= 30:
            score += 20
        elif days_arrears > 0:
            score += 10

    # 2. recent payment weakness
    if lpeightw is not None:
        if lpeightw <= 0:
            score += 20
        elif lpeightw < 2:
            score += 15
        elif lpeightw < 4:
            score += 8

    # 3. low savings buffer
    if savingsbal is not None:
        if savingsbal <= 0:
            score += 12
        elif savingsbal < 500:
            score += 8
        elif savingsbal < 2000:
            score += 4

    # 4. principal size pressure
    if principal is not None:
        if principal >= 100000:
            score += 10
        elif principal >= 50000:
            score += 7
        elif principal >= 20000:
            score += 4

    # 5. payment completion ratio
    if term is not None and term > 0 and termpaid is not None:
        progress = termpaid / term
        if progress < 0.25:
            score += 8
        elif progress < 0.50:
            score += 5
        elif progress < 0.75:
            score += 2

    # 6. early-cycle borrowers slightly riskier
    if cycle is not None:
        if cycle <= 1:
            score += 6
        elif cycle <= 2:
            score += 4
        elif cycle <= 3:
            score += 2

    # 7. poverty sensitivity factor
    if ppiscore is not None:
        if ppiscore <= 35:
            score += 10
        elif ppiscore <= 50:
            score += 5

    return round(min(score, 100), 2)


def classify_risk(score):
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def build_risk_profiles(rows):
    clients = {}

    for row in rows:
        client_key = get_client_key(row.get("cid"), row.get("memname"))
        if not client_key:
            continue

        row_score = compute_risk_score(row)

        if client_key not in clients:
            clients[client_key] = {
                "clientKey": client_key,
                "cid": clean_text(row.get("cid")),
                "name": clean_text(row.get("memname")),
                "area": clean_text(row.get("area_office")),
                "unit": clean_text(row.get("unit_office")),
                "center": clean_text(row.get("center_office")),
                "province": clean_text(row.get("prov")),
                "city": clean_text(row.get("city")),
                "scores": []
            }

        clients[client_key]["scores"].append(row_score)

    for client in clients.values():
        avg_score = round(mean(client["scores"]), 2) if client["scores"] else 0.0
        client["riskScore"] = avg_score
        client["riskLevel"] = classify_risk(avg_score)

    return clients


def apply_branch_filter(records, branch_level=None, branch_value=None):
    if not branch_level or not branch_value:
        return records

    field_map = {
        "area": "area",
        "unit": "unit",
        "center": "center"
    }

    if branch_level not in field_map:
        return records

    field = field_map[branch_level]
    target = str(branch_value).strip().lower()

    return [
        r for r in records
        if r.get(field) and str(r.get(field)).strip().lower() == target
    ]


def get_risk_dashboard(batch_id=None, branch_level=None, branch_value=None, top_limit=10):
    rows = fetch_risk_rows(batch_id=batch_id)
    clients = list(build_risk_profiles(rows).values())
    clients = apply_branch_filter(clients, branch_level=branch_level, branch_value=branch_value)

    total_clients = len(clients)
    low_count = sum(1 for c in clients if c["riskLevel"] == "Low")
    medium_count = sum(1 for c in clients if c["riskLevel"] == "Medium")
    high_count = sum(1 for c in clients if c["riskLevel"] == "High")

    low_pct = round((low_count / total_clients) * 100, 2) if total_clients > 0 else 0.0
    medium_pct = round((medium_count / total_clients) * 100, 2) if total_clients > 0 else 0.0
    high_pct = round((high_count / total_clients) * 100, 2) if total_clients > 0 else 0.0

    branch_groups = defaultdict(lambda: {
        "branch": None,
        "highRiskCount": 0,
        "mediumRiskCount": 0,
        "lowRiskCount": 0,
        "averageRiskScore": 0.0,
        "_scores": []
    })

    for client in clients:
        branch_name = client["unit"] or client["area"] or client["center"] or "Unassigned"
        branch_groups[branch_name]["branch"] = branch_name
        branch_groups[branch_name]["_scores"].append(client["riskScore"])

        if client["riskLevel"] == "High":
            branch_groups[branch_name]["highRiskCount"] += 1
        elif client["riskLevel"] == "Medium":
            branch_groups[branch_name]["mediumRiskCount"] += 1
        else:
            branch_groups[branch_name]["lowRiskCount"] += 1

    top_high_risk_branches = []
    for _, item in branch_groups.items():
        item["averageRiskScore"] = round(mean(item["_scores"]), 2) if item["_scores"] else 0.0
        del item["_scores"]
        top_high_risk_branches.append(item)

    top_high_risk_branches.sort(
        key=lambda x: (-x["highRiskCount"], -x["averageRiskScore"], x["branch"])
    )

    top_high_risk_clients = sorted(
        [c for c in clients if c["riskLevel"] == "High"],
        key=lambda x: (-x["riskScore"], x["name"] or "")
    )[:top_limit]

    geographic_risk_map = defaultdict(lambda: {
        "location": None,
        "totalClients": 0,
        "lowRisk": 0,
        "mediumRisk": 0,
        "highRisk": 0,
        "averageRiskScore": 0.0,
        "_scores": []
    })

    for client in clients:
        location = client["province"] or client["city"] or "Unknown"
        geographic_risk_map[location]["location"] = location
        geographic_risk_map[location]["totalClients"] += 1
        geographic_risk_map[location]["_scores"].append(client["riskScore"])

        if client["riskLevel"] == "High":
            geographic_risk_map[location]["highRisk"] += 1
        elif client["riskLevel"] == "Medium":
            geographic_risk_map[location]["mediumRisk"] += 1
        else:
            geographic_risk_map[location]["lowRisk"] += 1

    map_data = []
    for _, item in geographic_risk_map.items():
        item["averageRiskScore"] = round(mean(item["_scores"]), 2) if item["_scores"] else 0.0
        del item["_scores"]
        map_data.append(item)

    map_data.sort(key=lambda x: x["location"])

    return {
        "summary": {
            "totalClients": total_clients,
            "lowRiskPercentage": low_pct,
            "mediumRiskPercentage": medium_pct,
            "highRiskPercentage": high_pct,
            "lowRiskCount": low_count,
            "mediumRiskCount": medium_count,
            "highRiskCount": high_count
        },
        "topHighRiskBranches": top_high_risk_branches[:top_limit],
        "topHighRiskClients": top_high_risk_clients,
        "geographicRiskMap": map_data
    }


def get_risk_trend(current_batch_id=None, previous_batch_id=None):
    if current_batch_id is None:
        current_batch_id = get_latest_batch_id()

    if current_batch_id is None:
        return {
            "currentBatchId": None,
            "previousBatchId": None,
            "trend": []
        }

    if previous_batch_id is None:
        previous_batch_id = get_previous_batch_id(current_batch_id)

    current_clients = list(build_risk_profiles(fetch_risk_rows(batch_id=current_batch_id)).values())

    if previous_batch_id is None:
        current_summary = {
            "label": f"Batch {current_batch_id}",
            "low": sum(1 for c in current_clients if c["riskLevel"] == "Low"),
            "medium": sum(1 for c in current_clients if c["riskLevel"] == "Medium"),
            "high": sum(1 for c in current_clients if c["riskLevel"] == "High")
        }

        return {
            "currentBatchId": current_batch_id,
            "previousBatchId": None,
            "trend": [current_summary]
        }

    previous_clients = list(build_risk_profiles(fetch_risk_rows(batch_id=previous_batch_id)).values())

    previous_summary = {
        "label": f"Batch {previous_batch_id}",
        "low": sum(1 for c in previous_clients if c["riskLevel"] == "Low"),
        "medium": sum(1 for c in previous_clients if c["riskLevel"] == "Medium"),
        "high": sum(1 for c in previous_clients if c["riskLevel"] == "High")
    }

    current_summary = {
        "label": f"Batch {current_batch_id}",
        "low": sum(1 for c in current_clients if c["riskLevel"] == "Low"),
        "medium": sum(1 for c in current_clients if c["riskLevel"] == "Medium"),
        "high": sum(1 for c in current_clients if c["riskLevel"] == "High")
    }

    return {
        "currentBatchId": current_batch_id,
        "previousBatchId": previous_batch_id,
        "trend": [previous_summary, current_summary]
    }


def get_top_high_risk_clients(batch_id=None, branch_level=None, branch_value=None, limit=20):
    rows = fetch_risk_rows(batch_id=batch_id)
    clients = list(build_risk_profiles(rows).values())
    clients = apply_branch_filter(clients, branch_level=branch_level, branch_value=branch_value)

    high_risk_clients = [c for c in clients if c["riskLevel"] == "High"]
    high_risk_clients.sort(key=lambda x: (-x["riskScore"], x["name"] or ""))

    return high_risk_clients[:limit]