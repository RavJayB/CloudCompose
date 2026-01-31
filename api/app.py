from flask import Flask
import os
import psycopg2

app = Flask(__name__)

@app.get("/")
def home():
    return {"status": "ok", "message": "Flask API running behind Nginx ✅"}

@app.get("/db-check")
def db_check():
    host = os.getenv("DB_HOST", "db")
    dbname = os.getenv("POSTGRES_DB", "appdb")
    user = os.getenv("POSTGRES_USER", "appuser")
    password = os.getenv("POSTGRES_PASSWORD", "apppass")

    conn = psycopg2.connect(
        host=host,
        dbname=dbname,
        user=user,
        password=password
    )
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    now = cur.fetchone()[0]
    cur.close()
    conn.close()

    return {"db": "connected", "time": str(now)}
