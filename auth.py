from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from db import get_db_connection

def authenticate_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
           userid,username,password,firstname,middlename,lastname,staffid,position
        FROM userslist
        WHERE username=%s
    """, (username,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    hashed_password = generate_password_hash(password)
    print("HASHED PASSWORD:")
    print(hashed_password)


    if not row:
        return None

    # Convert tuple into dict
    user = {
        "userid": row[0],
        "username": row[1],
        "password": row[2],   # stored_password
        "firstname": row[3],
        "middlename": row[4],
        "lastname": row[5],
        "staffid": row[6],
        "position": row[7]
    
    }

    # PASSWORD CHECK (plain text right now)
    
    if check_password_hash(user["password"], password):
        return user  

    return None