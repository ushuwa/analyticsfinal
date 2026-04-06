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


def fetch_at_risk_rows(batch_id=None):
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
            acctdesc,
            principal,
            adjendbalprin,
            term,
            daysarrears,
            lpeightw,
            savingsbal,
            cycle,
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


def compute_at_risk_score(row):
    """
    Python analytical scoring model for client at-risk monitoring.
    Higher score = more severe risk.
    """
    days_arrears = clean_number(row.get("daysarrears"), 0)
    payment_recent = clean_number(row.get("lpeightw"), 0)
    principal = clean_number(row.get("principal"), 0)
    balance = clean_number(row.get("adjendbalprin"), 0)
    term = clean_number(row.get("term"), 0)
    savings = clean_number(row.get("savingsbal"), 0)
    cycle = clean_number(row.get("cycle"), 0)
    ppi = clean_number(row.get("ppiscore"), 0, 100)

    score = 0.0

    # 1. arrears pressure
    if days_arrears is not None:
        if days_arrears >= 120:
            score += 35
        elif days_arrears >= 90:
            score += 30
        elif days_arrears >= 60:
            score += 24
        elif days_arrears >= 30:
            score += 16
        elif days_arrears > 0:
            score += 8

    # 2. weak recent payment activity
    if payment_recent is not None:
        if payment_recent <= 0:
            score += 18
        elif payment_recent < 2:
            score += 14
        elif payment_recent < 4:
            score += 8

    # 3. large outstanding pressure
    if balance is not None:
        if balance >= 100000:
            score += 14
        elif balance >= 50000:
            score += 10
        elif balance >= 20000:
            score += 6
        elif balance > 0:
            score += 2
    elif principal is not None:
        if principal >= 100000:
            score += 10
        elif principal >= 50000:
            score += 7
        elif principal >= 20000:
            score += 4

    # 4. low savings buffer
    if savings is not None:
        if savings <= 0:
            score += 10
        elif savings < 500:
            score += 8
        elif savings < 2000:
            score += 4

    # 5. early loan cycle
    if cycle is not None:
        if cycle <= 1:
            score += 7
        elif cycle <= 2:
            score += 5
        elif cycle <= 3:
            score += 2

    # 6. poverty vulnerability factor
    if ppi is not None:
        if ppi <= 35:
            score += 10
        elif ppi <= 50:
            score += 5

    # 7. short-term pressure
    if term is not None:
        if term <= 6:
            score += 6
        elif term <= 12:
            score += 3

    return round(min(score, 100), 2)


def classify_risk_severity(score):
    if score >= 60:
        return "High Risk"
    if score >= 30:
        return "Moderate Risk"
    return "Low Risk"


def get_recommended_action(score):
    if score >= 60:
        return "Immediate follow-up and restructuring review"
    if score >= 30:
        return "Close monitoring and payment reminder"
    return "Routine monitoring"


def build_at_risk_profiles(rows):
    clients = {}

    for row in rows:
        client_key = get_client_key(row.get("cid"), row.get("memname"))
        if not client_key:
            continue

        score = compute_at_risk_score(row)

        if client_key not in clients:
            clients[client_key] = {
                "clientKey": client_key,
                "cid": clean_text(row.get("cid")),
                "name": clean_text(row.get("memname")),
                "area": clean_text(row.get("area_office")),
                "unit": clean_text(row.get("unit_office")),
                "center": clean_text(row.get("center_office")),
                "loanType": clean_text(row.get("acctdesc")),
                "loanPrincipals": [],
                "loanBalances": [],
                "loanTerms": [],
                "daysArrears": [],
                "scores": []
            }

        principal = clean_number(row.get("principal"), 0)
        balance = clean_number(row.get("adjendbalprin"), 0)
        term = clean_number(row.get("term"), 0)
        arrears = clean_number(row.get("daysarrears"), 0)

        if principal is not None:
            clients[client_key]["loanPrincipals"].append(principal)
        if balance is not None:
            clients[client_key]["loanBalances"].append(balance)
        if term is not None:
            clients[client_key]["loanTerms"].append(term)
        if arrears is not None:
            clients[client_key]["daysArrears"].append(arrears)

        clients[client_key]["scores"].append(score)

    for client in clients.values():
        avg_score = round(mean(client["scores"]), 2) if client["scores"] else 0.0
        client["riskScore"] = avg_score
        client["riskSeverity"] = classify_risk_severity(avg_score)
        client["recommendedAction"] = get_recommended_action(avg_score)
        client["loanPrincipal"] = round(sum(client["loanPrincipals"]), 2) if client["loanPrincipals"] else 0.0
        client["loanBalance"] = round(sum(client["loanBalances"]), 2) if client["loanBalances"] else 0.0
        client["loanTerm"] = round(mean(client["loanTerms"]), 2) if client["loanTerms"] else 0.0
        client["daysArrear"] = max(client["daysArrears"]) if client["daysArrears"] else 0.0

        del client["loanPrincipals"]
        del client["loanBalances"]
        del client["loanTerms"]
        del client["daysArrears"]
        del client["scores"]

    return list(clients.values())


def apply_filters(records, search=None, branch_level=None, branch_value=None, risk_severity=None):
    results = records

    if search:
        s = str(search).strip().lower()
        results = [
            r for r in results
            if (r.get("cid") and s in str(r["cid"]).lower())
            or (r.get("name") and s in str(r["name"]).lower())
        ]

    branch_map = {
        "area": "area",
        "unit": "unit",
        "center": "center"
    }

    if branch_level in branch_map and branch_value:
        field = branch_map[branch_level]
        target = str(branch_value).strip().lower()
        results = [
            r for r in results
            if r.get(field) and str(r[field]).strip().lower() == target
        ]

    if risk_severity:
        target_severity = str(risk_severity).strip().lower()
        results = [
            r for r in results
            if r.get("riskSeverity") and str(r["riskSeverity"]).strip().lower() == target_severity
        ]

    return results


def get_client_at_risk_dashboard(batch_id=None, search=None, branch_level=None, branch_value=None, risk_severity=None, limit=1000):
    rows = fetch_at_risk_rows(batch_id=batch_id)
    profiles = build_at_risk_profiles(rows)
    profiles = apply_filters(
        profiles,
        search=search,
        branch_level=branch_level,
        branch_value=branch_value,
        risk_severity=risk_severity
    )

    profiles.sort(
        key=lambda x: (
            0 if x["riskSeverity"] == "High Risk" else
            1 if x["riskSeverity"] == "Moderate Risk" else
            2,
            -x["riskScore"],
            x["name"] or ""
        )
    )

    low_count = sum(1 for p in profiles if p["riskSeverity"] == "Low Risk")
    moderate_count = sum(1 for p in profiles if p["riskSeverity"] == "Moderate Risk")
    high_count = sum(1 for p in profiles if p["riskSeverity"] == "High Risk")

    return {
        "summary": {
            "lowRisk": low_count,
            "moderateRisk": moderate_count,
            "highRisk": high_count
        },
        "clients": profiles[:limit]
    }