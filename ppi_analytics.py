from collections import Counter, defaultdict
from statistics import mean
from db import get_db_connection

QUESTION_COLUMNS = [f"q{i}" for i in range(1, 11)]


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


#table ppilikrlihood
def get_ppi_likelihood_table(limit=1000, search=None, branch_level=None, branch_value=None, batch_id=None):
    if batch_id is None:
        batch_id = get_latest_batch_id()

    if batch_id is None:
        return []

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        WITH client_rows AS (
            SELECT
                COALESCE(NULLIF(BTRIM(cid), ''), NULLIF(BTRIM(memname), '')) AS client_key,
                NULLIF(BTRIM(cid), '') AS cid,
                NULLIF(BTRIM(memname), '') AS memname,
                NULLIF(BTRIM(area_office), '') AS area_office,
                NULLIF(BTRIM(unit_office), '') AS unit_office,
                NULLIF(BTRIM(center_office), '') AS center_office,
                CASE
                    WHEN NULLIF(BTRIM(ppiscore), '') IS NOT NULL
                         AND REPLACE(BTRIM(ppiscore), '%%', '') ~ '^[0-9]+(\\.[0-9]+)?$'
                    THEN CAST(REPLACE(BTRIM(ppiscore), '%%', '') AS NUMERIC)
                    ELSE NULL
                END AS ppi_value
            FROM client_ppi_raw
            WHERE batch_id = %s
        ),
        grouped AS (
            SELECT
                client_key,
                MAX(cid) AS cid,
                MAX(memname) AS memname,
                MAX(area_office) AS area_office,
                MAX(unit_office) AS unit_office,
                MAX(center_office) AS center_office,
                COALESCE(ROUND(AVG(ppi_value), 2), 0) AS avg_ppi
            FROM client_rows
            WHERE client_key IS NOT NULL
            GROUP BY client_key
        )
        SELECT
            client_key,
            cid,
            memname,
            area_office,
            unit_office,
            center_office,
            avg_ppi
        FROM grouped
        WHERE 1=1
        
    """

    params = [batch_id]

    if search:
        query += """
            AND (
                LOWER(COALESCE(cid, '')) LIKE %s
                OR LOWER(COALESCE(memname, '')) LIKE %s
            )
        """
        search_like = f"%{str(search).strip().lower()}%"
        params.extend([search_like, search_like])

    branch_map = {
        "area": "area_office",
        "unit": "unit_office",
        "center": "center_office"
    }

    if branch_level in branch_map and branch_value:
        query += f" AND LOWER(COALESCE({branch_map[branch_level]}, '')) = %s"
        params.append(str(branch_value).strip().lower())

    query += " ORDER BY avg_ppi DESC, memname ASC LIMIT %s"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    result = []
    for row in rows:
        client_key, cid, memname, area_office, unit_office, center_office, avg_ppi = row

        avg_ppi = float(avg_ppi or 0)
        classification = classify_poverty(avg_ppi)
        poverty_likelihood = round(poverty_likelihood_probability(avg_ppi) * 100, 2)
        predicted_label = "Pagtalubo" if poverty_likelihood >= 50 else "Regular"

        result.append({
            "clientKey": client_key,
            "cid": cid,
            "name": memname,
            "area": area_office,
            "unit": unit_office,
            "center": center_office,
            "ppiScore": avg_ppi,
            "classification": classification,
            "povertyLikelihood": poverty_likelihood,
            "predictedPovertyLikelihood": predicted_label
        })

    return result






# =========================================================
# PYTHON ANALYTICAL ENGINE
# =========================================================

def fetch_raw_rows(batch_id=None):
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT
            r.batch_id,
            b.reporting_date,
            b.file_name,
            b.uploaded_at AS batch_uploaded_at,
            r.region_code,
            r.area_office,
            r.unit_office,
            r.center_office,
            r.cid,
            r.memname,
            r.ppiscore,
            r.q1, r.q2, r.q3, r.q4, r.q5, r.q6, r.q7, r.q8, r.q9, r.q10
        FROM client_ppi_raw r
        JOIN client_ppi_upload_batch b ON r.batch_id = b.batch_id
    """

    params = []
    if batch_id is not None:
        query += " WHERE r.batch_id = %s"
        params.append(batch_id)

    cur.execute(query, params)
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    return [dict(zip(colnames, row)) for row in rows]



def get_client_key(cid, memname):
    cid_clean = clean_text(cid)
    memname_clean = clean_text(memname)
    return cid_clean if cid_clean else memname_clean


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
                "memname": clean_text(row.get("memname")),
                "area_office": clean_text(row.get("area_office")),
                "unit_office": clean_text(row.get("unit_office")),
                "center_office": clean_text(row.get("center_office")),
                "ppi_values": [],
                "question_answers": defaultdict(list)
            }

        if ppi_value is not None:
            clients[client_key]["ppi_values"].append(ppi_value)

        for q in QUESTION_COLUMNS:
            answer = clean_text(row.get(q))
            if answer is not None:
                clients[client_key]["question_answers"][q].append(answer)

    for client in clients.values():
        avg_ppi = round(mean(client["ppi_values"]), 2) if client["ppi_values"] else 0.0
        client["avg_ppi"] = avg_ppi
        client["category"] = classify_poverty(avg_ppi)
        client["poverty_probability"] = poverty_likelihood_probability(avg_ppi)

    return clients



def get_dashboard_summary(batch_id=None):
    if batch_id is None:
        batch_id = get_latest_batch_id()

    if batch_id is None:
        return {
            "batchId": None,
            "totalClients": 0,
            "totalPpiAverage": 0.0,
            "totalPagtalubo": 0,
            "totalRegular": 0
        }

    rows = fetch_raw_rows(batch_id=batch_id)
    clients = build_client_profiles(rows)

    total_clients = len(clients)
    all_ppi_values = []
    total_pagtalubo = 0
    total_regular = 0

    for client in clients.values():
        if client["ppi_values"]:
            all_ppi_values.extend(client["ppi_values"])

        if client["category"] == "Pagtalubo":
            total_pagtalubo += 1
        else:
            total_regular += 1

    total_ppi_average = round(mean(all_ppi_values), 2) if all_ppi_values else 0.0

    return {
        "batchId": batch_id,
        "totalClients": total_clients,
        "totalPpiAverage": total_ppi_average,
        "totalPagtalubo": total_pagtalubo,
        "totalRegular": total_regular
    }


def get_branch_poverty_analysis(branch_level="unit_office", batch_id=None):
    if batch_id is None:
        batch_id = get_latest_batch_id()

    rows = fetch_raw_rows(batch_id=batch_id)
    clients = build_client_profiles(rows)

    valid_levels = {"area_office", "unit_office", "center_office", "region_code"}
    if branch_level not in valid_levels:
        branch_level = "unit_office"

    grouped = defaultdict(lambda: {
        "branch": None,
        "totalClients": 0,
        "totalPagtalubo": 0,
        "totalRegular": 0,
        "averagePpi": 0.0,
        "_ppi_values": []
    })

    for client in clients.values():
        branch_name = clean_text(client.get(branch_level)) or "Unassigned"
        grouped[branch_name]["branch"] = branch_name
        grouped[branch_name]["totalClients"] += 1
        grouped[branch_name]["_ppi_values"].append(client["avg_ppi"])

        if client["category"] == "Pagtalubo":
            grouped[branch_name]["totalPagtalubo"] += 1
        else:
            grouped[branch_name]["totalRegular"] += 1

    result = []
    for _, item in grouped.items():
        total_clients = item["totalClients"]
        total_pagtalubo = item["totalPagtalubo"]
        total_regular = item["totalRegular"]

        item["averagePpi"] = round(mean(item["_ppi_values"]), 2) if item["_ppi_values"] else 0.0
        item["pagtaluboPercentage"] = round((total_pagtalubo / total_clients) * 100, 2) if total_clients > 0 else 0.0
        item["regularPercentage"] = round((total_regular / total_clients) * 100, 2) if total_clients > 0 else 0.0

        del item["_ppi_values"]
        result.append(item)

    result.sort(key=lambda x: x["branch"])
    return result


def get_ppi_question_analysis(batch_id=None):
    if batch_id is None:
        batch_id = get_latest_batch_id()

    rows = fetch_raw_rows(batch_id=batch_id)
    clients = build_client_profiles(rows)

    results = []

    for q in QUESTION_COLUMNS:
        answer_counter = Counter()
        pagtalubo_counter = Counter()
        regular_counter = Counter()

        for client in clients.values():
            answers = client["question_answers"].get(q, [])
            if not answers:
                continue

            dominant_answer = Counter(answers).most_common(1)[0][0]
            answer_counter[dominant_answer] += 1

            if client["category"] == "Pagtalubo":
                pagtalubo_counter[dominant_answer] += 1
            else:
                regular_counter[dominant_answer] += 1

        results.append({
            "question": q,
            "totalAnswers": sum(answer_counter.values()),
            "answerBreakdown": dict(answer_counter),
            "pagtaluboBreakdown": dict(pagtalubo_counter),
            "regularBreakdown": dict(regular_counter)
        })

    return results


def get_client_poverty_prediction(batch_id=None):
    if batch_id is None:
        batch_id = get_latest_batch_id()

    rows = fetch_raw_rows(batch_id=batch_id)
    clients = build_client_profiles(rows)

    result = []
    for client in clients.values():
        result.append({
            "batchId": batch_id,
            "clientKey": client["clientKey"],
            "cid": client["cid"],
            "memname": client["memname"],
            "avgPpi": client["avg_ppi"],
            "category": client["category"],
            "povertyLikelihood": round(client["poverty_probability"] * 100, 2)
        })

    result.sort(key=lambda x: (-x["povertyLikelihood"], x["clientKey"]))
    return result


def get_ppi_trend_monitoring(current_batch_id=None, previous_batch_id=None):
    if current_batch_id is None:
        current_batch_id = get_latest_batch_id()

    if current_batch_id is None:
        return []

    if previous_batch_id is None:
        previous_batch_id = get_previous_batch_id(current_batch_id)

    if previous_batch_id is None:
        return []

    current_clients = build_client_profiles(fetch_raw_rows(batch_id=current_batch_id))
    previous_clients = build_client_profiles(fetch_raw_rows(batch_id=previous_batch_id))

    trends = []
    common_keys = set(current_clients.keys()) & set(previous_clients.keys())

    for client_key in sorted(common_keys):
        prev_ppi = previous_clients[client_key]["avg_ppi"]
        curr_ppi = current_clients[client_key]["avg_ppi"]
        change = round(curr_ppi - prev_ppi, 2)

        if change > 0:
            trend_status = "Improved"
        elif change < 0:
            trend_status = "Declined"
        else:
            trend_status = "No Change"

        trends.append({
            "clientKey": client_key,
            "cid": current_clients[client_key]["cid"],
            "memname": current_clients[client_key]["memname"],
            "previousBatchId": previous_batch_id,
            "currentBatchId": current_batch_id,
            "previousPpi": prev_ppi,
            "currentPpi": curr_ppi,
            "change": change,
            "trendStatus": trend_status,
            "previousCategory": previous_clients[client_key]["category"],
            "currentCategory": current_clients[client_key]["category"]
        })

    return trends



def get_top_poverty_risk_factors(batch_id=None, top_n=10):
    if batch_id is None:
        batch_id = get_latest_batch_id()

    if batch_id is None:
        return []

    rows = fetch_raw_rows(batch_id=batch_id)
    question_stats = []

    for q in QUESTION_COLUMNS:
        question_values = []
        pagtalubo_count = 0
        total_answered = 0

        for row in rows:
            answer_value = clean_number(row.get(q))

            # only include rows with an actual numeric answer for this question
            if answer_value is None:
                continue

            total_answered += 1
            question_values.append(answer_value)

            ppi_value = clean_number(row.get("ppiscore"), 0, 100)
            category = classify_poverty(ppi_value if ppi_value is not None else 0)

            if category == "Pagtalubo":
                pagtalubo_count += 1

        if total_answered == 0:
            continue

        average_score = round(mean(question_values), 2)
        percentage = round((pagtalubo_count / total_answered) * 100, 2)

        question_stats.append({
            "questionNo": q.upper(),
            "percentage": percentage,
            "averageScore": average_score
        })

    question_stats.sort(key=lambda x: (-x["percentage"], -x["averageScore"], x["questionNo"]))
    return question_stats[:top_n]


def get_poverty_movement_dashboard(current_batch_id=None, previous_batch_id=None):
    if current_batch_id is None:
        current_batch_id = get_latest_batch_id()

    if current_batch_id is None:
        return {
            "summary": {
                "currentBatchId": None,
                "previousBatchId": None,
                "mode": "empty",
                "improved": 0,
                "declined": 0,
                "noChange": 0,
                "graduatedFromPagtalubo": 0,
                "averagePpiImprovement": 0.0,
                "povertyReductionRate": 0.0
            },
            "topRiskFactors": []
        }

    if previous_batch_id is None:
        previous_batch_id = get_previous_batch_id(current_batch_id)

    if previous_batch_id is None:
        return {
            "summary": {
                "currentBatchId": current_batch_id,
                "previousBatchId": None,
                "mode": "snapshot",
                "improved": 0,
                "declined": 0,
                "noChange": 0,
                "graduatedFromPagtalubo": 0,
                "averagePpiImprovement": 0.0,
                "povertyReductionRate": 0.0
            },
            "topRiskFactors": get_top_poverty_risk_factors(batch_id=current_batch_id)
        }

    current_clients = build_client_profiles(fetch_raw_rows(batch_id=current_batch_id))
    previous_clients = build_client_profiles(fetch_raw_rows(batch_id=previous_batch_id))

    common_keys = sorted(set(current_clients.keys()) & set(previous_clients.keys()))

    improved = 0
    declined = 0
    no_change = 0
    graduated = 0
    positive_changes = []

    for client_key in common_keys:
        prev_client = previous_clients[client_key]
        curr_client = current_clients[client_key]

        prev_ppi = prev_client["avg_ppi"]
        curr_ppi = curr_client["avg_ppi"]
        change = round(curr_ppi - prev_ppi, 2)

        if change > 0:
            improved += 1
            positive_changes.append(change)
        elif change < 0:
            declined += 1
        else:
            no_change += 1

        if prev_client["category"] == "Pagtalubo" and curr_client["category"] == "Regular":
            graduated += 1

    average_improvement = round(mean(positive_changes), 2) if positive_changes else 0.0

    previous_pagtalubo_total = sum(
        1 for client in previous_clients.values() if client["category"] == "Pagtalubo"
    )

    poverty_reduction_rate = round(
        (graduated / previous_pagtalubo_total) * 100, 2
    ) if previous_pagtalubo_total > 0 else 0.0

    return {
        "summary": {
            "currentBatchId": current_batch_id,
            "previousBatchId": previous_batch_id,
            "mode": "comparison",
            "improved": improved,
            "declined": declined,
            "noChange": no_change,
            "graduatedFromPagtalubo": graduated,
            "averagePpiImprovement": average_improvement,
            "povertyReductionRate": poverty_reduction_rate
        },
        "topRiskFactors": get_top_poverty_risk_factors(batch_id=current_batch_id)
    }
    


def get_client_poverty_profiles(limit=1000, search=None, branch_level=None, branch_value=None):
    rows = fetch_raw_rows(batch_id=None)
    clients = build_client_profiles(rows)

    results = []

    for client_key, client in clients.items():
        avg_ppi = client["avg_ppi"]
        poverty_likelihood = round(client["poverty_probability"] * 100, 2)
        predicted_label = "Pagtalubo" if poverty_likelihood >= 50 else "Regular"

        row = {
            "clientKey": client_key,
            "cid": client["cid"],
            "name": client["memname"],
            "area": client["area_office"],
            "unit": client["unit_office"],
            "center": client["center_office"],
            "ppiScore": avg_ppi,
            "classification": client["category"],
            "povertyLikelihood": poverty_likelihood,
            "predictedPovertyLikelihood": predicted_label
        }

        results.append(row)

    # optional search filter
    if search:
        search_value = str(search).strip().lower()
        results = [
            row for row in results
            if (row["cid"] and search_value in str(row["cid"]).lower())
            or (row["name"] and search_value in str(row["name"]).lower())
        ]

    # optional branch filter
    branch_field_map = {
        "area": "area",
        "unit": "unit",
        "center": "center"
    }

    if branch_level and branch_value and branch_level in branch_field_map:
        field = branch_field_map[branch_level]
        branch_value_lower = str(branch_value).strip().lower()

        results = [
            row for row in results
            if row[field] and str(row[field]).strip().lower() == branch_value_lower
        ]

    results.sort(key=lambda x: (
        0 if x["classification"] == "Pagtalubo" else 1,
        x["ppiScore"] if x["ppiScore"] is not None else 9999
    ))

    return results[:limit]    


def get_current_poverty_overview():
    rows = fetch_raw_rows(batch_id=None)
    clients = build_client_profiles(rows)

    total_clients = len(clients)
    total_pagtalubo = 0
    total_regular = 0
    all_ppi = []

    for client in clients.values():
        all_ppi.append(client["avg_ppi"])

        if client["category"] == "Pagtalubo":
            total_pagtalubo += 1
        else:
            total_regular += 1

    average_ppi = round(mean(all_ppi), 2) if all_ppi else 0.0
    pagtalubo_percentage = round((total_pagtalubo / total_clients) * 100, 2) if total_clients > 0 else 0.0
    regular_percentage = round((total_regular / total_clients) * 100, 2) if total_clients > 0 else 0.0

    return {
        "totalClients": total_clients,
        "totalPagtalubo": total_pagtalubo,
        "totalRegular": total_regular,
        "averagePpi": average_ppi,
        "pagtaluboPercentage": pagtalubo_percentage,
        "regularPercentage": regular_percentage
    }


