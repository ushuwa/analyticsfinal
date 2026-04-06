from db import get_db_connection


def get_dashboard_summary():
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
    WITH cleaned_data AS (
        SELECT
            COALESCE(
                NULLIF(BTRIM(cid), ''),
                NULLIF(BTRIM(memname), '')
            ) AS client_key,
            CASE
                WHEN NULLIF(BTRIM(ppiscore), '') IS NOT NULL
                     AND REPLACE(BTRIM(ppiscore), '%', '') ~ '^[0-9]+(\\.[0-9]+)?$'
                THEN CAST(REPLACE(BTRIM(ppiscore), '%', '') AS NUMERIC)
                ELSE NULL
            END AS ppi_value
        FROM client_ppi_raw
    ),
    valid_clients AS (
        SELECT *
        FROM cleaned_data
        WHERE client_key IS NOT NULL
    ),
    overall_ppi AS (
        SELECT ROUND(AVG(ppi_value), 2) AS total_ppi_average
        FROM valid_clients
        WHERE ppi_value IS NOT NULL
    ),
    client_avg AS (
        SELECT
            client_key,
            COALESCE(AVG(ppi_value), 0) AS avg_ppi
        FROM valid_clients
        GROUP BY client_key
    )
    SELECT
        (SELECT COUNT(*) FROM client_avg) AS total_clients,
        COALESCE((SELECT total_ppi_average FROM overall_ppi), 0) AS total_ppi_average,
        COUNT(*) FILTER (WHERE avg_ppi <= 35) AS total_pagtalubo,
        COUNT(*) FILTER (WHERE avg_ppi > 35) AS total_regular
    FROM client_avg;
    """

    cur.execute(query)
    row = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "totalClients": int(row[0] or 0),
        "totalPpiAverage": float(row[1] or 0),
        "totalPagtalubo": int(row[2] or 0),
        "totalRegular": int(row[3] or 0)
    }