from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2, psycopg2.extras
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, send_file
import psycopg2, io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import date
from flask import Flask, send_file, abort
import psycopg2
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2.extras

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


# ================= NILAI  ================= #

@app.route("/nilai/<int:id>", methods=["GET", "POST"])
def nilai_murid(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Ambil data murid
    cur.execute("SELECT * FROM murid WHERE id=%s", (id,))
    murid = cur.fetchone()
    if not murid:
        cur.close()
        conn.close()
        return "Data murid tidak ditemukan", 404

    # Ambil daftar mata pelajaran
    cur.execute("SELECT * FROM mapel ORDER BY id ASC")
    mapel_list = cur.fetchall()

    if request.method == "POST":
        action = request.form.get("action")
        semester = request.form.get("semester")

        # Tahun ajaran otomatis
        now = datetime.now()
        if now.month >= 7:
            tahun_ajaran = f"{now.year}/{now.year + 1}"
        else:
            tahun_ajaran = f"{now.year - 1}/{now.year}"

        
    # UPLOAD >> Cek dulu apakah nilai untuk semester & tahun ajaran sudah ada    
        if action == "upload":
            cur.execute("""
            SELECT COUNT(*) FROM nilai 
            WHERE murid_id=%s AND semester=%s AND tahun_ajaran=%s
        """, (id, semester, tahun_ajaran))
        exists = cur.fetchone()[0]

        if exists > 0:
            flash(f"⚠️ Nilai untuk semester '{semester}' tahun ajaran {tahun_ajaran} sudah diinput sebelumnya!", "danger")
            cur.close()
            conn.close()
            return redirect(request.url)

    # Kalau belum ada, baru insert
        for m in mapel_list:
            nilai = request.form.get(f"mapel_{m['id']}")
            deskripsi = request.form.get(f"deskripsi_{m['id']}")

            if not nilai or not deskripsi:
                flash(f"⚠️ Nilai atau deskripsi untuk {m['nama']} belum lengkap!", "danger")
                cur.close()
                conn.close()
                return redirect(request.url)

            cur.execute("""
                INSERT INTO nilai (murid_id, mapel_id, semester, tahun_ajaran, nilai, deskripsi)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id, m["id"], semester, tahun_ajaran, nilai, deskripsi))

        conn.commit()
        flash("✅ Semua nilai & deskripsi berhasil disimpan!", "success")
        cur.close()
        conn.close()
        return redirect(request.url)


    # Ambil nilai existing untuk tampilkan di form (edit/update)
    nilai_existing = {}
    cur.execute("""
        SELECT mapel_id, nilai, deskripsi, semester, tahun_ajaran
        FROM nilai WHERE murid_id=%s
    """, (id,))
    for row in cur.fetchall():
        key = (row["mapel_id"], row["semester"], row["tahun_ajaran"])
        nilai_existing[key] = {"nilai": row["nilai"], "deskripsi": row["deskripsi"]}

    cur.close()
    conn.close()

    return render_template(
        "nilai_murid.html",
        murid=murid,
        mapel_list=mapel_list,
        nilai_existing=nilai_existing,
        show_rapot_btn=True
    )



# ================= RIWAYAT NILAI MURID ================= #
@app.route("/murid/riwayat/<int:id>")
def riwayat_murid(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Data murid
    cur.execute("SELECT * FROM murid WHERE id=%s", (id,))
    murid = cur.fetchone()
    if not murid:
        cur.close()
        conn.close()
        return "Data murid tidak ditemukan", 404

    # Riwayat nilai (pakai kolom deskripsi)
    cur.execute("""
        SELECT n.tahun_ajaran, n.semester, mp.nama AS mapel_nama, 
               n.nilai, n.deskripsi, n.created_at
        FROM nilai n
        JOIN mapel mp ON n.mapel_id = mp.id
        WHERE n.murid_id = %s
        ORDER BY n.tahun_ajaran DESC, n.semester ASC, mp.nama ASC
    """, (id,))
    riwayat = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("riwayat_murid.html", murid=murid, riwayat=riwayat)





# ================= MAPEL ================= #
@app.route("/mapel")
def data_mapel():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM mapel ORDER BY id ASC")
    mapel_list = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("mapel.html", mapel=mapel_list)

# Tambah Mapel
@app.route("/mapel/tambah", methods=["POST"])
def tambah_mapel():
    nama = request.form.get("nama")
    deskripsi = request.form.get("deskripsi")

    if not nama or not deskripsi:
        flash("⚠️ Nama & Deskripsi mapel wajib diisi!", "danger")
        return redirect(request.referrer)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO mapel (nama, deskripsi) VALUES (%s, %s)", (nama, deskripsi))
    conn.commit()
    cur.close()
    conn.close()

    flash(f"✅ Mapel '{nama}' berhasil ditambahkan!", "success")
    return redirect(request.referrer)


# Ubah Mapel
@app.route("/mapel/edit/<int:id>", methods=["POST"])
def edit_mapel(id):
    nama = request.form.get("nama")
    deskripsi = request.form.get("deskripsi")

    if not nama or not deskripsi:
        flash("⚠️ Nama & Deskripsi wajib diisi!", "danger")
        return redirect(request.referrer)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE mapel SET nama=%s, deskripsi=%s WHERE id=%s", (nama, deskripsi, id))
    conn.commit()
    cur.close()
    conn.close()

    flash(f"✏️ Mapel '{nama}' berhasil diperbarui!", "success")
    return redirect(request.referrer)


# Hapus Mapel
@app.route("/mapel/hapus/<int:id>", methods=["POST"])
def hapus_mapel(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM mapel WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("🗑️ Mapel berhasil dihapus!", "success")
    return redirect(request.referrer)




# === Rapot ===
@app.route("/rapot/<int:murid_id>/<semester>")
def rapot(murid_id, semester):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Ambil data murid
        cur.execute("SELECT * FROM murid WHERE id = %s", (murid_id,))
        murid = cur.fetchone()
        if not murid:
            return "Murid tidak ditemukan", 404

        # Tahun ajaran otomatis
        now = datetime.now()
        if now.month >= 7:
            tahun_ajaran = f"{now.year}/{now.year + 1}"
        else:
            tahun_ajaran = f"{now.year - 1}/{now.year}"

        # Ambil nilai sesuai semester + kategori mapel
        # Asumsikan table 'mapel' ada kolom 'kategori' (BTQ, Diniyah, Praktek)
        cur.execute("""
            SELECT n.nilai, n.deskripsi, m.nama AS mapel, m.kategori
            FROM mapel m
            LEFT JOIN nilai n
                ON n.mapel_id = m.id AND n.murid_id = %s AND n.semester = %s AND n.tahun_ajaran = %s
            ORDER BY m.kategori ASC, m.nama ASC
        """, (murid_id, semester, tahun_ajaran))
        nilai_list = []
        for row in cur.fetchall():
            nilai_list.append({
                "mapel": row["mapel"],
                "nilai": row["nilai"] if row["nilai"] is not None else 0,
                "deskripsi": row["deskripsi"] if row["deskripsi"] else "Belum ada deskripsi",
                "kategori": row["kategori"] if row["kategori"] else "Lain-lain"
            })

        return render_template(
            "rapot.html",
            murid=murid,
            nilai_list=nilai_list,
            semester=semester,
            tahun_ajaran=tahun_ajaran,
            now=now
        )
    finally:
        conn.close()


# ================= RUN ================= #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
