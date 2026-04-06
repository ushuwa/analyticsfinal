from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection


# -------------------------------------------------------------
# GET ALL USERS
# -------------------------------------------------------------
def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            userid, username, firstname, middlename, lastname, staffid, position
        FROM userslist
        ORDER BY userid DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # Convert list of tuples → list of dicts
    users = []
    for r in rows:
        users.append({
            "userid": r[0],
            "username": r[1],
            "firstname": r[2],
            "middlename": r[3],
            "lastname": r[4],
            "staffid": r[5],
            "position": r[6],
        })
    return users


# -------------------------------------------------------------
# GET SINGLE USER BY ID
# -------------------------------------------------------------
def get_user(userid):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            userid, username, firstname, middlename, lastname, staffid, position, password
        FROM userslist
        WHERE userid=%s
    """, (userid,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "userid": row[0],
        "username": row[1],
        "firstname": row[2],
        "middlename": row[3],
        "lastname": row[4],
        "staffid": row[5],
        "position": row[6],
        "password": row[7],  # hashed
    }


# -------------------------------------------------------------
# CREATE NEW USER
# -------------------------------------------------------------
def create_user(username, password, firstname, middlename, lastname, staffid, position):
    conn = get_db_connection()
    cur = conn.cursor()

    hashed = generate_password_hash(password)

    cur.execute("""
        INSERT INTO userslist (username, password, firstname, middlename, lastname, staffid, position)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING userid
    """, (username, hashed, firstname, middlename, lastname, staffid, position))

    new_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return new_id


# -------------------------------------------------------------
# UPDATE USER (without changing password)
# -------------------------------------------------------------
def update_user(userid, username, firstname, middlename, lastname, staffid, position):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE userslist
        SET username=%s, firstname=%s, middlename=%s, lastname=%s,
            staffid=%s, position=%s
        WHERE userid=%s
        RETURNING userid
    """, (username, firstname, middlename, lastname, staffid, position, userid))

    updated = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return updated is not None


# -------------------------------------------------------------
# UPDATE PASSWORD ONLY
# -------------------------------------------------------------
def update_user_password(userid, new_password):
    conn = get_db_connection()
    cur = conn.cursor()

    hashed = generate_password_hash(new_password)

    cur.execute("""
        UPDATE userslist
        SET password=%s
        WHERE userid=%s
        RETURNING userid
    """, (hashed, userid))

    updated = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return updated is not None


# -------------------------------------------------------------
# DELETE USER
# -------------------------------------------------------------
def delete_user(userid):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM userslist WHERE userid=%s RETURNING userid", (userid,))
    deleted = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return deleted is not None
