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
            return render_template(
        "nilai_murid.html",
        murid=murid,
        mapel_list=mapel_list
    )

   

# ================= RIWAYAT NILAI MURID ================= #
@app.route("/murid/riwayat/<int:id>")
def riwayat_murid(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Data murid
    cur.execute("SELECT * FROM murid WHERE id=%s", (id,))
    murid = cur.fetchone()

    # Riwayat nilai lengkap (per mapel per jilid)
    cur.execute("""
        SELECT r.jilid, mp.nama AS mapel_nama, n.nilai, n.diskripsi, r.tanggal AS created_at
        FROM rapot r
        JOIN nilai n ON r.murid_id = n.murid_id AND r.jilid = n.jilid
        JOIN mapel mp ON n.mapel_id = mp.id
        WHERE r.murid_id = %s
        ORDER BY r.jilid ASC, mp.nama ASC
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

    # Hitung rata-rata
    rata_rata = sum([row["nilai"] for row in nilai_jilid]) / len(nilai_jilid) if nilai_jilid else 0

    # Simpan / ambil rapot_id
    cur.execute("SELECT id, tanggal FROM rapot WHERE murid_id=%s AND jilid=%s", (murid_id, jilid))
    ada = cur.fetchone()
    if not ada:
        cur.execute(
            "INSERT INTO rapot (murid_id, jilid, rata_rata, tanggal) VALUES (%s, %s, %s, %s) RETURNING id, tanggal",
            (murid_id, jilid, rata_rata, date.today())
        )
        rapot_row = cur.fetchone()
        rapot_id, tanggal_cetak = rapot_row["id"], rapot_row["tanggal"]
        conn.commit()
    else:
        rapot_id, tanggal_cetak = ada["id"], ada["tanggal"]

    cur.close()
    conn.close()

    # Struktur kategori mapel
    kategori_mapel = {
        "BTQ": ["Kehadiran", "Bacaan", "Hafalan"],
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
        nilai_dict=nilai_dict,
        rapot_id=rapot_id,
        rata_rata=rata_rata,
        tanggal_cetak=tanggal_cetak.strftime("%d-%m-%Y"),  # ✅ tampilkan format tanggal
        kepala_madrasah="Ust. Ahmad"  # ✅ bisa diganti sesuai kebutuhan
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

    nilai_dict = {row["nama"]: (row["nilai"], row["diskripsi"]) for row in nilai_jilid}

    kategori_mapel = {
        "BTQ": ["Kehadiran", "Bacaan", "Hafalan"],
        "Diniyah": ["Al-Qur’an Hadits", "Aqidah Akhlaq", "Tajwid",
                    "Bahasa Arab", "Pego", "Imla’/Khot", "Fiqih"],
        "Praktek": ["Wudhu", "Shalat", "Doa sehari-hari"]
    }

    # --- Generate PDF ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # === KOP SURAT (center) ===
    title_center = styles["Title"]; title_center.alignment = 1
    heading_center = styles["Heading2"]; heading_center.alignment = 1
    normal_center = styles["Normal"]; normal_center.alignment = 1

    elements.append(Paragraph("<b>TAMAN PENDIDIKAN AL QUR'AN</b>", title_center))
    elements.append(Paragraph("<b>“MAFATIHUL HUDA”</b>", heading_center))
    elements.append(Paragraph("BAKALANRAYUNG KECAMATAN KUDU – JOMBANG", normal_center))
    elements.append(Paragraph("Nomor Statistik : 411.235.17.2074  |  Telp. 0857-3634-0726", normal_center))
    elements.append(Spacer(1, 6))
    elements.append(Table([[""]], colWidths=[500], style=[
        ("LINEABOVE", (0,0), (-1,0), 2, colors.black)
    ]))
    elements.append(Spacer(1, 12))

    # === Judul Rapot (center) ===
    heading1 = styles["Heading1"]; heading1.alignment = 1
    heading2 = styles["Heading2"]; heading2.alignment = 1

    elements.append(Paragraph("<b>LAPORAN HASIL BELAJAR</b>", heading1))
    elements.append(Paragraph(f"Jilid {rapot['jilid']}", heading2))
    elements.append(Spacer(1, 12))

# === Identitas Murid (mirip HTML) ===
    identitas_data = [
        ["Nama", f": {rapot['nama']}", "Kelas", f": {rapot['kelas']}"],
        ["Wali Kelas", f": {rapot['wali_kelas']}", "Tanggal",
         f": {rapot['tanggal'].strftime('%d-%m-%Y') if rapot['tanggal'] else '-'}"]
    ]

    identitas_table = Table(identitas_data, colWidths=[90, 160, 90, 160])
    identitas_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),  # garis bawah baris 1
        ("LINEBELOW", (0, 1), (-1, 1), 1, colors.black),  # garis bawah baris 2
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))
    elements.append(identitas_table)
    elements.append(Spacer(1, 16))

    

    # === Tabel Nilai per Kategori ===
    for kategori, daftar in kategori_mapel.items():
        h3 = styles["Heading3"]; h3.alignment = 1
        elements.append(Paragraph(f"<b>{kategori}</b>", h3))

        data = [["Mata Pelajaran", "Nilai", "Deskripsi"]]
        for mp in daftar:
            if mp in nilai_dict:
                data.append([mp, str(nilai_dict[mp][0]), nilai_dict[mp][1]])
            else:
                data.append([mp, "-", "Belum ada deskripsi"])

        table = Table(data, colWidths=[150, 50, 250])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    # === Rata-rata (center) ===
    normal_center = styles["Normal"]; normal_center.alignment = 1
    elements.append(Paragraph(f"<b>Rata-rata:</b> {rapot['rata_rata']:.2f}", normal_center))
    elements.append(Spacer(1, 40))

    # === Tanda Tangan (3 kolom, center) ===
    kepala_madrasah = "Ustadz Ahmad"  # 👉 bisa diambil dari DB
    tanda_tangan = [
        ["Kepala Madrasah", "Wali Kelas", "Peserta Didik"],
        ["", "", ""],
        ["", "", ""],
        [f"( {kepala_madrasah} )", f"( {rapot['wali_kelas']} )", f"( {rapot['nama']} )"]
    ]
    tt_table = Table(tanda_tangan, colWidths=[160, 160, 160])
    tt_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(tt_table)

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
