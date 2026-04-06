from collections import defaultdict
from statistics import mean
from db import get_db_connection

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np


FACTOR_LABELS = {
    "client_age": "Client Age",
    "late_payments_8w": "Late Payments last 8 weeks",
    "length_of_membership": "Length of membership",
    "poverty_index_progress": "Progress out of Poverty Index",
    "days_past_due": "Days Past Due",
    "savings_trend": "Savings Trend",
    "transaction_trend": "Transaction Trend",
    "loan_cycle": "Loan Cycle",
    "compliance_ratio": "Compliance Ratio",
    "repayment_progress_ratio": "Repayment Progress Ratio",
    "number_of_children": "No. of Children",
    "declared_income": "Declared household monthly income",
    "declared_expense": "Declared household monthly expense"
}


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


def get_recent_batches(limit=5):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT batch_id, reporting_date, uploaded_at
        FROM client_ppi_upload_batch
        ORDER BY batch_id DESC
        LIMIT %s
        """,
        (limit,)
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    rows = list(reversed(rows))

    result = []
    for batch_id, reporting_date, uploaded_at in rows:
        if reporting_date:
            label = str(reporting_date)
        elif uploaded_at:
            label = uploaded_at.strftime("%Y-%m-%d")
        else:
            label = f"Batch {batch_id}"

        result.append({
            "batchId": batch_id,
            "label": label
        })

    return result


def fetch_rows(batch_id=None):
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
            acctdesc,
            currage,
            lpeightw,
            los,
            ppiscore,
            daysarrears,
            savingsbal,
            fourweeksbefore,
            avgsavtrnfour,
            avgsavtrneight,
            cycle,
            term,
            termpaid,
            numberofchildren,
            householdmonthlyincome,
            householdmonthlyexpense
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


def safe_ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def to_risk_0_100(value, low, high, inverse=False):
    if value is None:
        return None

    if high == low:
        return 0.0

    clipped = max(low, min(value, high))
    ratio = (clipped - low) / (high - low)
    score = ratio * 100.0
    if inverse:
        score = 100.0 - score
    return round(score, 2)


def extract_factor_scores(row):
    currage = clean_number(row.get("currage"), 0, 120)
    lpeightw = clean_number(row.get("lpeightw"), 0)
    los = clean_number(row.get("los"), 0)
    ppiscore = clean_number(row.get("ppiscore"), 0, 100)
    daysarrears = clean_number(row.get("daysarrears"), 0)
    savingsbal = clean_number(row.get("savingsbal"))
    fourweeksbefore = clean_number(row.get("fourweeksbefore"))
    avgsavtrnfour = clean_number(row.get("avgsavtrnfour"))
    avgsavtrneight = clean_number(row.get("avgsavtrneight"))
    cycle = clean_number(row.get("cycle"), 0)
    term = clean_number(row.get("term"), 0)
    termpaid = clean_number(row.get("termpaid"), 0)
    numberofchildren = clean_number(row.get("numberofchildren"), 0)
    income = clean_number(row.get("householdmonthlyincome"), 0)
    expense = clean_number(row.get("householdmonthlyexpense"), 0)

    compliance_ratio = safe_ratio(lpeightw, 8)
    repayment_progress = safe_ratio(termpaid, term)

    savings_trend_raw = None
    if fourweeksbefore is not None and savingsbal is not None:
        base = abs(fourweeksbefore) if abs(fourweeksbefore) > 0 else 1
        savings_trend_raw = (savingsbal - fourweeksbefore) / base

    transaction_trend_raw = None
    if avgsavtrneight is not None and avgsavtrnfour is not None:
        base = abs(avgsavtrneight) if abs(avgsavtrneight) > 0 else 1
        transaction_trend_raw = (avgsavtrnfour - avgsavtrneight) / base

    return {
        "client_age": to_risk_0_100(currage, 18, 75, inverse=False),
        "late_payments_8w": to_risk_0_100(lpeightw, 0, 8, inverse=True),
        "length_of_membership": to_risk_0_100(los, 0, 120, inverse=True),
        "poverty_index_progress": to_risk_0_100(ppiscore, 0, 100, inverse=True),
        "days_past_due": to_risk_0_100(daysarrears, 0, 120, inverse=False),
        "savings_trend": to_risk_0_100(savings_trend_raw, -1, 1, inverse=True),
        "transaction_trend": to_risk_0_100(transaction_trend_raw, -1, 1, inverse=True),
        "loan_cycle": to_risk_0_100(cycle, 1, 10, inverse=True),
        "compliance_ratio": to_risk_0_100(compliance_ratio, 0, 1, inverse=True),
        "repayment_progress_ratio": to_risk_0_100(repayment_progress, 0, 1, inverse=True),
        "number_of_children": to_risk_0_100(numberofchildren, 0, 8, inverse=False),
        "declared_income": to_risk_0_100(income, 0, 50000, inverse=True),
        "declared_expense": to_risk_0_100(expense, 0, 50000, inverse=False),
    }


def overall_client_risk(factor_scores):
    values = [v for v in factor_scores.values() if v is not None]
    if not values:
        return 0.0
    return round(mean(values), 2)


def classify_client_risk(score):
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def build_factor_summary(batch_id):
    rows = fetch_rows(batch_id=batch_id)
    factor_values = defaultdict(list)
    loan_type_scores = defaultdict(list)
    client_risk_scores = []

    for row in rows:
        factor_scores = extract_factor_scores(row)
        overall_risk = overall_client_risk(factor_scores)
        client_risk_scores.append(overall_risk)

        loan_type = clean_text(row.get("acctdesc")) or "Unknown"
        loan_type_scores[loan_type].append(overall_risk)

        for factor, score in factor_scores.items():
            if score is not None:
                factor_values[factor].append(score)

    factor_means = {
        factor: round(mean(values), 2) if values else 0.0
        for factor, values in factor_values.items()
    }

    client_risk_distribution = {
        "low": sum(1 for s in client_risk_scores if classify_client_risk(s) == "Low"),
        "medium": sum(1 for s in client_risk_scores if classify_client_risk(s) == "Medium"),
        "high": sum(1 for s in client_risk_scores if classify_client_risk(s) == "High"),
    }

    loan_type_means = [
        {
            "loanType": loan_type,
            "averageRiskScore": round(mean(scores), 2) if scores else 0.0
        }
        for loan_type, scores in loan_type_scores.items()
    ]
    loan_type_means.sort(key=lambda x: (-x["averageRiskScore"], x["loanType"]))

    return {
        "factorMeans": factor_means,
        "riskDistribution": client_risk_distribution,
        "loanTypeRiskComparison": loan_type_means
    }


def classify_factor_severity_with_kmeans(current_factor_means, previous_factor_means=None):
    factors = list(current_factor_means.keys())
    rows = []

    for factor in factors:
        current_val = current_factor_means.get(factor, 0.0)
        previous_val = 0.0 if not previous_factor_means else previous_factor_means.get(factor, 0.0)
        delta = current_val - previous_val if previous_factor_means is not None else 0.0
        pct_change = ((delta / previous_val) * 100.0) if previous_factor_means and previous_val not in (0, None) else delta

        rows.append([current_val, abs(pct_change)])

    X = np.array(rows, dtype=float)

    if len(X) < 3:
        labels = []
        for current_val, change_abs in X:
            score = current_val
            if score >= 60:
                labels.append("High")
            elif score >= 30:
                labels.append("Medium")
            else:
                labels.append("Low")
        return labels

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(X_scaled)

    centers = []
    for idx, center in enumerate(kmeans.cluster_centers_):
        severity_score = center[0] * 0.8 + center[1] * 0.2
        centers.append((idx, severity_score))

    centers.sort(key=lambda x: x[1])
    cluster_to_label = {
        centers[0][0]: "Low",
        centers[1][0]: "Medium",
        centers[2][0]: "High"
    }

    return [cluster_to_label[c] for c in cluster_ids]


def get_recommended_actions(factor_rows):
    high_factors = [f["riskFactor"] for f in factor_rows if f["riskSeverity"] == "High"]
    medium_factors = [f["riskFactor"] for f in factor_rows if f["riskSeverity"] == "Medium"]

    actions = []

    if any("Late Payments" in f or "Days Past Due" in f for f in high_factors):
        actions.append("Immediate monitoring or field visit to the client.")
    if any("Compliance Ratio" in f or "Repayment Progress Ratio" in f for f in high_factors + medium_factors):
        actions.append("Monitor closely. Review repayment behavior and renewal conditions.")
    if any("Savings Trend" in f or "Transaction Trend" in f for f in high_factors + medium_factors):
        actions.append("Encourage savings discipline and monitor transaction activity.")
    if any("Declared household monthly income" in f or "Declared household monthly expense" in f for f in high_factors):
        actions.append("Assess household cash flow and repayment capacity.")
    if not actions:
        actions.append("Normal monitoring.")

    deduped = []
    seen = set()
    for action in actions:
        if action not in seen:
            deduped.append(action)
            seen.add(action)

    return deduped[:3]


def get_risk_factors_overview(current_batch_id=None, previous_batch_id=None):
    if current_batch_id is None:
        current_batch_id = get_latest_batch_id()

    if current_batch_id is None:
        return {
            "monthlyRiskTrend": [],
            "riskFactors": [],
            "loanTypeRiskComparison": [],
            "recommendedActions": []
        }

    if previous_batch_id is None:
        previous_batch_id = get_previous_batch_id(current_batch_id)

    current_summary = build_factor_summary(current_batch_id)
    previous_summary = build_factor_summary(previous_batch_id) if previous_batch_id else None

    current_means = current_summary["factorMeans"]
    previous_means = previous_summary["factorMeans"] if previous_summary else None

    severities = classify_factor_severity_with_kmeans(current_means, previous_means)

    factor_rows = []
    for idx, factor in enumerate(current_means.keys()):
        current_val = current_means.get(factor, 0.0)
        previous_val = previous_means.get(factor, 0.0) if previous_means else 0.0

        if previous_means and previous_val not in (0, None):
            pct_change = ((current_val - previous_val) / previous_val) * 100.0
        else:
            pct_change = current_val

        trend = "Up" if pct_change > 0 else "Down" if pct_change < 0 else "Flat"

        factor_rows.append({
            "riskFactor": FACTOR_LABELS.get(factor, factor),
            "riskSeverity": severities[idx],
            "increaseDecreasePercentage": round(abs(pct_change), 2),
            "trend": trend,
            "currentScore": round(current_val, 2)
        })

    factor_rows.sort(
        key=lambda x: (
            0 if x["riskSeverity"] == "High" else 1 if x["riskSeverity"] == "Medium" else 2,
            -x["increaseDecreasePercentage"],
            x["riskFactor"]
        )
    )

    recent_batches = get_recent_batches(limit=5)
    monthly_risk_trend = []

    for batch in recent_batches:
        summary = build_factor_summary(batch["batchId"])
        monthly_risk_trend.append({
            "label": batch["label"],
            "low": summary["riskDistribution"]["low"],
            "medium": summary["riskDistribution"]["medium"],
            "high": summary["riskDistribution"]["high"]
        })

    return {
        "monthlyRiskTrend": monthly_risk_trend,
        "riskFactors": factor_rows,
        "loanTypeRiskComparison": current_summary["loanTypeRiskComparison"][:10],
        "recommendedActions": get_recommended_actions(factor_rows)
    }