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

    # Ambil daftar mata pelajaran diniyah
    cur.execute("SELECT * FROM mapel ORDER BY id ASC")
    mapel_list = cur.fetchall()

    if request.method == "POST":
        action = request.form.get("action")  # tombol yang ditekan
        jilid_aktif = int(murid["jilid"])

        if action == "simpan":
            # Simpan sementara ke tabel murid (nilai & diskripsi belum final)
            for m in mapel_list:
                nilai = request.form.get(f"mapel_{m['id']}")
                diskripsi = request.form.get(f"diskripsi_{m['id']}")
                if nilai:  # hanya update jika ada isinya
                    cur.execute(
                        f"UPDATE murid SET nilai_mapel_{m['id']} = %s, diskripsi_mapel_{m['id']} = %s WHERE id = %s",
                        (nilai, diskripsi, id),
                    )
            conn.commit()
            flash("💾 Nilai sementara berhasil disimpan!", "info")
            cur.close()
            conn.close()
            return redirect(request.url)

        elif action == "upload":
            # Validasi semua mapel wajib ada nilai & diskripsi
            for m in mapel_list:
                nilai = request.form.get(f"mapel_{m['id']}")
                diskripsi = request.form.get(f"diskripsi_{m['id']}")
                if not nilai or not diskripsi:
                    flash(f"⚠️ Nilai atau diskripsi untuk {m['nama']} belum lengkap!", "danger")
                    cur.close()
                    conn.close()
                    return redirect(request.url)

            # Jika valid → simpan ke tabel nilai
            for m in mapel_list:
                nilai = request.form.get(f"mapel_{m['id']}")
                diskripsi = request.form.get(f"diskripsi_{m['id']}")
                cur.execute(
                    """
                    INSERT INTO nilai (murid_id, mapel_id, jilid, nilai, diskripsi)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (id, m["id"], jilid_aktif, nilai, diskripsi),
                )

            # Naikkan jilid
            cur.execute("UPDATE murid SET jilid = jilid + 1 WHERE id=%s", (id,))
            conn.commit()
            flash("✅ Semua nilai & diskripsi berhasil diupload & Jilid naik!", "success")
            cur.close()
            conn.close()
            return redirect(url_for("data_murid"))

    # Ambil riwayat nilai murid
    cur.execute(
        """
        SELECT n.*, m.nama as mapel_nama
        FROM nilai n
        JOIN mapel m ON n.mapel_id = m.id
        WHERE murid_id=%s
        ORDER BY jilid ASC, mapel_id ASC
        """,
        (id,),
    )
    riwayat = cur.fetchall()

    cur.close()
    conn.close()
    return render_template(
        "nilai_murid.html", murid=murid, mapel_list=mapel_list, riwayat=riwayat
    )



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

# ================= RAPOT ================= #

@app.route("/rapot/<int:murid_id>/<int:jilid>")
def rapot(murid_id, jilid):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Data murid
    cur.execute("SELECT id, nama, kelas, wali_kelas FROM murid WHERE id=%s", (murid_id,))
    murid = cur.fetchone()

    # Ambil nilai mapel
    cur.execute("""
        SELECT m.nama, n.nilai, n.diskripsi
        FROM nilai n
        JOIN mapel m ON n.mapel_id = m.id
        WHERE n.murid_id=%s AND n.jilid=%s
    """, (murid_id, jilid))
    nilai_jilid = cur.fetchall()
    cur.close()
    conn.close()

    # Struktur kategori mapel
    kategori_mapel = {
        "BTQ": ["Kehadiran", "Membaca Jilid", "Hafalan materi"],
        "Diniyah": ["Al-Qur’an Hadits", "Aqidah Akhlaq", "Tajwid", "Bahasa Arab", "Pego", "Imla’/Khot", "Fiqih"],
        "Praktek": ["Wudhu", "Shalat", "Doa sehari-hari"]
    }

    # Ubah hasil query ke dict
    nilai_dict = {row["nama"]: (row["nilai"], row["diskripsi"]) for row in nilai_jilid}

    return render_template(
        "rapot.html",
        murid=murid,
        jilid=jilid,
        kategori_mapel=kategori_mapel,
        nilai_dict=nilai_dict
    )


# ================= CETAK RAPOT ================= #

@app.route("/rapot/cetak/<int:rapot_id>")
def cetak_rapot(rapot_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Ambil rapot + murid
    cur.execute("""
        SELECT r.jilid, r.tanggal, r.rata_rata,
               m.nama, m.kelas, m.wali_kelas, m.id
        FROM rapot r
        JOIN murid m ON r.murid_id = m.id
        WHERE r.id=%s
    """, (rapot_id,))
    rapot = cur.fetchone()

    if not rapot:
        cur.close()
        conn.close()
        return "Rapot tidak ditemukan", 404

    # Ambil nilai & deskripsi
    cur.execute("""
        SELECT mp.nama, n.nilai, n.diskripsi
        FROM nilai n
        JOIN mapel mp ON n.mapel_id=mp.id
        WHERE n.murid_id=%s AND n.jilid=%s
    """, (rapot["id"], rapot["jilid"]))
    nilai_jilid = cur.fetchall()
    cur.close()
    conn.close()

    # Format dict
    nilai_dict = {row["nama"]: (row["nilai"], row["diskripsi"]) for row in nilai_jilid}

    # Definisi kategori mapel
    kategori_mapel = {
        "BTQ": ["Kehadiran", "Membaca Jilid", "Hafalan materi"],
        "Diniyah": ["Al-Qur’an Hadits", "Aqidah Akhlaq", "Tajwid", "Bahasa Arab", "Pego", "Imla’/Khot", "Fiqih"],
        "Praktek": ["Wudhu", "Shalat", "Doa sehari-hari"]
    }

    # --- Generate PDF ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Judul
    elements.append(Paragraph(f"<b>LAPORAN HASIL BELAJAR</b>", styles["Title"]))
    elements.append(Paragraph(f"Jilid {rapot['jilid']}", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    # Identitas murid
    elements.append(Paragraph(f"<b>Nama:</b> {rapot['nama']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Kelas:</b> {rapot['kelas']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Wali Kelas:</b> {rapot['wali_kelas']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Tanggal:</b> {rapot['tanggal'].strftime('%d-%m-%Y')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Tabel per kategori
    for kategori, daftar in kategori_mapel.items():
        elements.append(Paragraph(f"<b>{kategori}</b>", styles["Heading3"]))

        data = [["Mata Pelajaran", "Nilai", "Deskripsi"]]
        for mp in daftar:
            if mp in nilai_dict:
                data.append([mp, str(nilai_dict[mp][0]), nilai_dict[mp][1]])
            else:
                data.append([mp, "-", "Belum ada deskripsi"])

        table = Table(data, colWidths=[120, 50, 280])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    # Rata-rata
    elements.append(Paragraph(f"<b>Rata-rata:</b> {rapot['rata_rata']:.2f}", styles["Normal"]))
    elements.append(Spacer(1, 40))

    # Tanda tangan
    elements.append(Paragraph(f"Mengetahui,", styles["Normal"]))
    elements.append(Paragraph(f"Wali Kelas", styles["Normal"]))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(f"( {rapot['wali_kelas']} )", styles["Normal"]))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(f"Peserta Didik,", styles["Normal"]))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(f"( {rapot['nama']} )", styles["Normal"]))

    doc.build(elements)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"rapot_jilid_{rapot['jilid']}.pdf",
        mimetype="application/pdf"
    )


# ================= RUN ================= #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
