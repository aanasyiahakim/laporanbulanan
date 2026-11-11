from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, get_db, encrypt_data, decrypt_data, hash_password
import json

app = Flask(__name__)
app.secret_key = "FLASK_SUPER_SECRET_KEY_SIM_SMA"

init_db()

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username, role, nama_lengkap, nis_nip FROM users WHERE username = ? AND password = ?", 
                       (username, hash_password(password)))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["nama_lengkap"] = user["nama_lengkap"]
            session["nis_nip"] = user["nis_nip"]
            flash("Login berhasil!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Username atau Password salah!", "danger")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah keluar.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
        
    conn = get_db()
    cursor = conn.cursor()
    
    total_siswa = cursor.execute("SELECT COUNT(*) FROM siswa").fetchone()[0]
    total_final = cursor.execute("SELECT COUNT(*) FROM laporan_bulanan WHERE status = 'Final'").fetchone()[0]
    total_draf = cursor.execute("SELECT COUNT(*) FROM laporan_bulanan WHERE status = 'Draf'").fetchone()[0]
    avg_nilai = cursor.execute("SELECT AVG(rerata_akademik) FROM laporan_bulanan").fetchone()[0] or 0.0
    
    conn.close()
    
    return render_template("dashboard.html", 
                           total_siswa=total_siswa, 
                           total_final=total_final, 
                           total_draf=total_draf, 
                           avg_nilai=round(avg_nilai, 2))

@app.route("/siswa", methods=["GET", "POST"])
def siswa():
    if session.get("role") not in ["Admin", "Guru"]:
        flash("Akses ditolak!", "danger")
        return redirect(url_for("dashboard"))
        
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        nis = request.form["nis"].strip()
        nama = request.form["nama"].strip()
        kelas = request.form["kelas"].strip()
        
        cursor.execute("INSERT OR REPLACE INTO siswa VALUES (?, ?, ?, ?, ?)", 
                       (nis, encrypt_data(nama), kelas, "L", session["nama_lengkap"]))
        conn.commit()
        flash(f"Data siswa {nama} berhasil disimpan!", "success")
        return redirect(url_for("siswa"))
        
    siswa_rows = cursor.execute("SELECT nis, nama_enc, kelas, wali_kelas FROM siswa").fetchall()
    conn.close()
    
    siswa_list = [{
        "nis": row["nis"],
        "nama": decrypt_data(row["nama_enc"]),
        "kelas": row["kelas"],
        "wali_kelas": row["wali_kelas"]
    } for row in siswa_rows]
    
    return render_template("siswa.html", siswa_list=siswa_list)

@app.route("/kelola-laporan", methods=["GET", "POST"])
def kelola_laporan():
    if session.get("role") not in ["Admin", "Guru"]:
        flash("Akses ditolak!", "danger")
        return redirect(url_for("dashboard"))
        
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        nis = request.form["nis"]
        bulan = request.form["bulan"]
        tahun = "2026"
        hadir = int(request.form.get("hadir", 0))
        sakit = int(request.form.get("sakit", 0))
        izin = int(request.form.get("izin", 0))
        alpa = int(request.form.get("alpa", 0))
        rerata = float(request.form.get("rerata", 0.0))
        
        sikap = json.dumps({
            "Kedisiplinan": request.form.get("disiplin"),
            "Tanggung Jawab": request.form.get("tjawab")
        })
        
        cursor.execute("""
            INSERT OR REPLACE INTO laporan_bulanan 
            (nis, bulan, tahun, hadir, sakit, izin, alpa, rerata_akademik, penilaian_sikap_enc, catatan_prestasi_enc, catatan_pelanggaran_enc, catatan_wali_kelas_enc, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nis, bulan, tahun, hadir, sakit, izin, alpa, rerata,
              encrypt_data(sikap),
              encrypt_data(request.form.get("prestasi")),
              encrypt_data(request.form.get("pelanggaran")),
              encrypt_data(request.form.get("catatan")),
              request.form.get("status")))
        conn.commit()
        flash("Laporan bulanan berhasil disimpan ke database terenkripsi!", "success")
        return redirect(url_for("kelola_laporan"))
        
    siswa_rows = cursor.execute("SELECT nis, nama_enc FROM siswa").fetchall()
    conn.close()
    
    siswa_dict = [{
        "nis": row["nis"],
        "nama": decrypt_data(row["nama_enc"])
    } for row in siswa_rows]
    
    return render_template("kelola_laporan.html", siswa_list=siswa_dict)

@app.route("/cetak-laporan")
def cetak_laporan():
    if "username" not in session:
        return redirect(url_for("login"))
        
    conn = get_db()
    cursor = conn.cursor()
    
    if session["role"] == "Siswa":
        siswa_rows = cursor.execute("SELECT nis, nama_enc, kelas, wali_kelas FROM siswa WHERE nis = ?", (session["nis_nip"],)).fetchall()
    else:
        siswa_rows = cursor.execute("SELECT nis, nama_enc, kelas, wali_kelas FROM siswa").fetchall()
        
    selected_nis = request.args.get("nis")
    laporan_detail = None
    
    if selected_nis:
        siswa_info = cursor.execute("SELECT nis, nama_enc, kelas, wali_kelas FROM siswa WHERE nis = ?", (selected_nis,)).fetchone()
        lap_row = cursor.execute("""
            SELECT bulan, tahun, hadir, sakit, izin, alpa, rerata_akademik, penilaian_sikap_enc,
                   catatan_prestasi_enc, catatan_pelanggaran_enc, catatan_wali_kelas_enc, status
            FROM laporan_bulanan WHERE nis = ? ORDER BY id DESC LIMIT 1
        """, (selected_nis,)).fetchone()
        
        if siswa_info and lap_row:
            sikap = json.loads(decrypt_data(lap_row["penilaian_sikap_enc"])) if lap_row["penilaian_sikap_enc"] else {}
            laporan_detail = {
                "nis": siswa_info["nis"],
                "nama": decrypt_data(siswa_info["nama_enc"]),
                "kelas": siswa_info["kelas"],
                "wali_kelas": siswa_info["wali_kelas"],
                "bulan": lap_row["bulan"],
                "tahun": lap_row["tahun"],
                "hadir": lap_row["hadir"],
                "sakit": lap_row["sakit"],
                "izin": lap_row["izin"],
                "alpa": lap_row["alpa"],
                "rerata": lap_row["rerata_akademik"],
                "sikap": sikap,
                "prestasi": decrypt_data(lap_row["catatan_prestasi_enc"]),
                "pelanggaran": decrypt_data(lap_row["catatan_pelanggaran_enc"]),
                "catatan": decrypt_data(lap_row["catatan_wali_kelas_enc"]),
                "status": lap_row["status"]
            }
            
    conn.close()
    
    siswa_list = [{
        "nis": row["nis"],
        "nama": decrypt_data(row["nama_enc"])
    } for row in siswa_rows]
    
    return render_template("cetak_laporan.html", siswa_list=siswa_list, laporan=laporan_detail, selected_nis=selected_nis)

if __name__ == "__main__":
    app.run(debug=True, port=5000)