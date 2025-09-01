from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2, psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "rahasia_tpq")  # penting untuk session

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url)

# ================= ROUTES ================= #

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return redirect(url_for("data_murid"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "admin":
            session["user"] = username
            return redirect(url_for("data_murid"))
        else:
            flash("Username atau password salah", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ================= MURID ================= #

@app.route("/murid")
def data_murid():
    if not session.get("user"):
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM murid ORDER BY id ASC")
    murid = cur.fetchall()

    # Ambil daftar kelas & jilid unik
    cur.execute("SELECT DISTINCT kelas FROM murid ORDER BY kelas ASC")
    kelas_list = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return render_template("data_murid.html", murid=murid, kelas_list=kelas_list, jilid_list=jilid_list)

@app.route("/add", methods=["GET", "POST"])
def add_murid():
    if request.method == "POST":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO murid (nama, jilid, kelas, alamat, wali_murid, wali_kelas)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            request.form["nama"], request.form["jilid"], request.form["kelas"], 
            request.form["alamat"], request.form["wali_murid"], request.form["wali_kelas"]
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("data_murid"))
    return render_template("add_murid.html")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_murid(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM murid WHERE id=%s", (id,))
    murid = cur.fetchone()

    if request.method == "POST":
        cur.execute("""
            UPDATE murid SET nama=%s, jilid=%s, kelas=%s, alamat=%s, wali_murid=%s, wali_kelas=%s
            WHERE id=%s
        """, (
            request.form["nama"], request.form["jilid"], request.form["kelas"],
            request.form["alamat"], request.form["wali_murid"], request.form["wali_kelas"], id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("data_murid"))

    cur.close()
    conn.close()
    return render_template("edit_murid.html", murid=murid)

@app.route("/delete/<int:id>")
def delete_murid(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM murid WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("data_murid"))

# ================= CETAK ================= #

@app.route("/cetak_data")
def cetak_data():
    if not session.get("user"):
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM murid ORDER BY id ASC")
    murid = cur.fetchall()

    cur.execute("SELECT DISTINCT kelas FROM murid ORDER BY kelas ASC")
    kelas_list = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return render_template("cetak.html", murid=murid, kelas_list=kelas_list, jilid_list=jilid_list)

@app.route("/cetak/kelas/<kelas>")
def cetak_per_kelas(kelas):
    if not session.get("user"):
        return redirect(url_for("login"))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM murid WHERE kelas=%s ORDER BY id ASC", (kelas,))
    murid = cur.fetchall()

    cur.execute("SELECT DISTINCT kelas FROM murid ORDER BY kelas ASC")
    kelas_list = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return render_template("cetak.html", murid=murid, kelas_list=kelas_list, jilid_list=jilid_list, kelas=kelas)

@app.route("/cetak/jilid/<jilid>")
def cetak_per_jilid(jilid):
    if not session.get("user"):
        return redirect(url_for("login"))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM murid WHERE jilid=%s ORDER BY id ASC", (jilid,))
    murid = cur.fetchall()

    cur.execute("SELECT DISTINCT kelas FROM murid ORDER BY kelas ASC")
    kelas_list = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return render_template("cetak.html", murid=murid, kelas_list=kelas_list, jilid_list=jilid_list, jilid=jilid)

# ================= RUN ================= #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
