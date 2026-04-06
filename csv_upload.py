import csv
import os
from db import get_db_connection

TABLE_NAME = "client_ppi_raw"
BATCH_TABLE = "client_ppi_upload_batch"

COLUMNS = [
    "region_code",
    "area_office",
    "unit_office",
    "center_office",
    "cid",
    "memname",
    "los",
    "currage",
    "civilstatus",
    "gender",
    "businesstype",
    "employment",
    "brgy",
    "city",
    "prov",
    "householdmonthlyincome",
    "householdmonthlyexpense",
    "ppiscore",
    "numberofchildren",
    "acc",
    "acctdesc",
    "principal",
    "adjendbalprin",
    "amort",
    "term",
    "termpaid",
    "cycle",
    "savingsbal",
    "fourweeksbefore",
    "avgsavtrnfour",
    "avgsavtrneight",
    "daysarrears",
    "lpeightw",
    "q1",
    "q2",
    "q3",
    "q4",
    "q5",
    "q6",
    "q7",
    "q8",
    "q9",
    "q10",
    "name",
    "education",
    "benage",
    "bnstatus"
]


def count_csv_rows(file_path: str) -> int:
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        return max(sum(1 for _ in f) - 1, 0)


def validate_csv_headers(file_path: str):
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader)

    normalized_headers = [str(h).strip() for h in headers]
    expected_headers = COLUMNS

    if normalized_headers != expected_headers:
        raise ValueError(
            f"CSV headers do not match expected structure.\n"
            f"Expected: {expected_headers}\n"
            f"Actual: {normalized_headers}"
        )


def create_upload_batch(file_name: str, reporting_date=None, uploaded_by=None) -> int:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        INSERT INTO {BATCH_TABLE} (file_name, reporting_date, uploaded_by)
        VALUES (%s, %s, %s)
        RETURNING batch_id
        """,
        (file_name, reporting_date, uploaded_by)
    )

    batch_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return batch_id


def update_batch_total_rows(batch_id: int, total_rows: int):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        UPDATE {BATCH_TABLE}
        SET total_rows = %s
        WHERE batch_id = %s
        """,
        (total_rows, batch_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def build_temp_csv_with_batch_id(file_path: str, batch_id: int) -> str:
    temp_file = f"{file_path}.batch.csv"

    with open(file_path, "r", encoding="utf-8-sig", newline="") as src, \
         open(temp_file, "w", encoding="utf-8", newline="") as dst:

        reader = csv.reader(src)
        writer = csv.writer(dst)

        original_header = next(reader)
        writer.writerow(["batch_id"] + original_header)

        for row in reader:
            if len(row) < len(COLUMNS):
                row = row + [""] * (len(COLUMNS) - len(row))
            elif len(row) > len(COLUMNS):
                row = row[:len(COLUMNS)]

            writer.writerow([batch_id] + row)

    return temp_file


def copy_csv_to_table(temp_file_path: str):
    conn = get_db_connection()
    cur = conn.cursor()

    column_list = ", ".join([f'"{col}"' for col in (["batch_id"] + COLUMNS)])

    with open(temp_file_path, "r", encoding="utf-8") as f:
        copy_sql = f"""
            COPY {TABLE_NAME} ({column_list})
            FROM STDIN
            WITH CSV HEADER
            DELIMITER ','
        """
        cur.copy_expert(copy_sql, f)

    conn.commit()
    cur.close()
    conn.close()


def process_csv_upload(file_path: str, file_name: str, reporting_date=None, uploaded_by=None) -> dict:
    validate_csv_headers(file_path)
    row_count = count_csv_rows(file_path)

    batch_id = create_upload_batch(
        file_name=file_name,
        reporting_date=reporting_date,
        uploaded_by=uploaded_by
    )

    temp_file_path = build_temp_csv_with_batch_id(file_path, batch_id)

    try:
        copy_csv_to_table(temp_file_path)
        update_batch_total_rows(batch_id, row_count)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return {
        "batchId": batch_id,
        "table": TABLE_NAME,
        "rowsRead": row_count,
        "rowsInserted": row_count,
        "fileName": file_name,
        "reportingDate": reporting_date
    }


def get_upload_batches():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT batch_id, file_name, reporting_date, uploaded_by, uploaded_at, total_rows
        FROM {BATCH_TABLE}
        ORDER BY batch_id DESC
        """
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "batchId": row[0],
            "fileName": row[1],
            "reportingDate": str(row[2]) if row[2] else None,
            "uploadedBy": row[3],
            "uploadedAt": row[4].isoformat() if row[4] else None,
            "totalRows": row[5]
        })

    return result


def delete_batch(batch_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"DELETE FROM {BATCH_TABLE} WHERE batch_id = %s", (batch_id,))
    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    return deleted > 0