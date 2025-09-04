from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2, psycopg2.extras
import os
from dotenv import load_dotenv

# Load environment dari file .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "rahasia_tpq")  # 🔑 penting untuk session

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

# Debug route → cek env
@app.route("/debug/env")
def debug_env():
    keys = ["DATABASE_URL", "PGURL", "RAILWAY_DATABASE_URL"]
    env_data = {k: os.getenv(k) for k in keys}
    return jsonify(env_data)

# ================= MURID ================= #

@app.route("/murid")
def data_murid():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    search = request.args.get("q", "")
    filter_kelas = request.args.get("kelas", "")
    filter_jilid = request.args.get("jilid", "")


    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Ambil semua murid
    cur.execute("SELECT * FROM murid ORDER BY id ASC")
    murid = cur.fetchall()

    # Ambil daftar kelas unik
    cur.execute("SELECT DISTINCT kelas FROM murid ORDER BY kelas ASC")
    kelas_list = [row['kelas'] for row in cur.fetchall()]

    # Ambil daftar jilid unik
    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row['jilid'] for row in cur.fetchall()]

    query = "SELECT * FROM murid WHERE 1=1"
    params = []

    if search:
        query += " AND nama ILIKE %s"
        params.append(f"%{search}%")
    if filter_kelas:
        query += " AND kelas=%s"
        params.append(filter_kelas)
    if filter_jilid:
        query += " AND jilid=%s"
        params.append(filter_jilid)

    query += " ORDER BY id ASC"
    cur.execute(query, tuple(params))
    murid = cur.fetchall()

    # Ambil daftar kelas & jilid unik untuk filter dropdown
    cur.execute("SELECT DISTINCT kelas FROM murid ORDER BY kelas ASC")
    kelas_list = cur.fetchall()
    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template(
        "data_murid.html", murid=murid, kelas_list=kelas_list, jilid_list=jilid_list,
        search=search, filter_kelas=filter_kelas, filter_jilid=filter_jilid
    )


# ================= CRUD ================= #

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
    kelas_list = [row['kelas'] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row['jilid'] for row in cur.fetchall()]

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
    kelas_list = [row['kelas'] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row['jilid'] for row in cur.fetchall()]

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
    kelas_list = [row['kelas'] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT jilid FROM murid ORDER BY jilid ASC")
    jilid_list = [row['jilid'] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return render_template("cetak.html", murid=murid, kelas_list=kelas_list, jilid_list=jilid_list, jilid=jilid)



# ================= BIODATA ================= #

@app.route("/biodata/<int:id>", methods=["GET", "POST"])
def biodata_murid(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM murid WHERE id=%s", (id,))
    murid = cur.fetchone()
    if not murid:
        cur.close()
        conn.close()
        return "Data murid tidak ditemukan", 404

    if request.method == "POST":
        cur.execute("""
            UPDATE murid SET 
                nama=%s, no_induk=%s, nik=%s, tempat_tanggal_lahir=%s, jenis_kelamin=%s,
                status_dalam_keluarga=%s, anak_ke=%s,
                nama_ayah=%s, no_tlp_ayah=%s, pekerjaan_ayah=%s,
                nama_ibu=%s, no_tlp_ibu=%s, pekerjaan_ibu=%s,
                dusun=%s, rt=%s, rw=%s, desa=%s, kecamatan=%s, kabupaten_kota=%s, provinsi=%s
            WHERE id=%s
        """, (
            request.form.get("nama"), request.form.get("no_induk"), request.form.get("nik"),
            request.form.get("tempat_tanggal_lahir"), request.form.get("jenis_kelamin"),
            request.form.get("status_dalam_keluarga"), request.form.get("anak_ke") or None,
            request.form.get("nama_ayah"), request.form.get("no_tlp_ayah"), request.form.get("pekerjaan_ayah"),
            request.form.get("nama_ibu"), request.form.get("no_tlp_ibu"), request.form.get("pekerjaan_ibu"),
            request.form.get("dusun"), request.form.get("rt"), request.form.get("rw"),
            request.form.get("desa"), request.form.get("kecamatan"), request.form.get("kabupaten_kota"),
            request.form.get("provinsi"), id
        ))
        conn.commit()
        cur.close()
        conn.close()
        flash("✅ Data murid berhasil diperbarui!", "success")
        return redirect(url_for("data_murid"))

    cur.close()
    conn.close()
    return render_template("biodata_murid.html", murid=murid)


# ================= NILAI ================= #

def generate_diskripsi(bacaan, menulis, hafalan, ahlak, kehadiran):
    return f"Bacaan: {bacaan}, Menulis: {menulis}, Hafalan: {hafalan}, Ahlak: {ahlak}, Kehadiran: {kehadiran}"

@app.route("/nilai/<int:id>", methods=["GET", "POST"])
def nilai_murid(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM murid WHERE id=%s", (id,))
    murid = cur.fetchone()
    if not murid:
        cur.close()
        conn.close()
        return "Data murid tidak ditemukan", 404

    if request.method == "POST":
        bacaan = request.form.get("bacaan")
        menulis = request.form.get("menulis")
        hafalan = request.form.get("hafalan")
        ahlak = request.form.get("ahlak")
        kehadiran = request.form.get("kehadiran")
        diskripsi = request.form.get("diskripsi")

        if not diskripsi:
            diskripsi = generate_diskripsi(bacaan, menulis, hafalan, ahlak, kehadiran)

        action = request.form.get("action")  # cek tombol mana yang ditekan

        if action == "simpan":
            # Simpan sementara ke tabel murid
            cur.execute("""
                UPDATE murid
                SET nilai_bacaan=%s, nilai_menulis=%s, nilai_hafalan=%s,
                    nilai_ahlak=%s, nilai_kehadiran=%s, diskripsi=%s
                WHERE id=%s
            """, (bacaan, menulis, hafalan, ahlak, kehadiran, diskripsi, id))
            flash("📝 Nilai berhasil disimpan sementara!", "info")

        elif action == "upload":
            # Pastikan nilai lengkap
            if not bacaan or not menulis or not hafalan or not ahlak or not kehadiran:
                flash("⚠️ Nilai ada yang kosong, tolong lengkapi sebelum upload.", "danger")
            else:
                jilid_aktif = int(murid["jilid"])
                cur.execute("""
                    INSERT INTO nilai (murid_id, jilid, nilai_bacaan, nilai_menulis,
                        nilai_hafalan, nilai_ahlak, nilai_kehadiran, diskripsi)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (id, jilid_aktif, bacaan, menulis, hafalan, ahlak, kehadiran, diskripsi))
                
                cur.execute("UPDATE murid SET jilid = jilid + 1 WHERE id=%s", (id,))
                flash("✅ Nilai berhasil di-upload & Jilid Naik!", "success")

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("nilai_murid", id=id))

    cur.execute("SELECT * FROM nilai WHERE murid_id=%s ORDER BY jilid ASC", (id,))
    riwayat = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("nilai_murid.html", murid=murid, riwayat=riwayat, jilid=murid["jilid"])



# ================= RUN ================= #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
