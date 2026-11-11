import sqlite3
import hashlib
import base64
import json

DB_NAME = "sim_laporsma_encrypted.db"
SECRET_KEY = "SMA_RAPOR_BULANAN_SECRET_KEY_2026"

def derive_key(secret: str, salt: str = "SIM_LAPOR_SMA_SALT") -> bytes:
    return hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), salt.encode('utf-8'), 100000, 32)

def encrypt_data(data_str: str) -> str:
    if not data_str:
        return ""
    key = derive_key(SECRET_KEY)
    data_bytes = str(data_str).encode('utf-8')
    cipher = bytes([b ^ key[i % len(key)] for i, b in enumerate(data_bytes)])
    return base64.b64encode(cipher).decode('utf-8')

def decrypt_data(cipher_str: str) -> str:
    if not cipher_str:
        return ""
    try:
        key = derive_key(SECRET_KEY)
        cipher_bytes = base64.b64decode(cipher_str.encode('utf-8'))
        plain = bytes([b ^ key[i % len(key)] for i, b in enumerate(cipher_bytes)])
        return plain.decode('utf-8')
    except Exception:
        return cipher_str

def hash_password(password: str) -> str:
    return hashlib.sha256((password + "SIM_SMA_SALT").encode('utf-8')).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            nama_lengkap TEXT NOT NULL,
            nis_nip TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS siswa (
            nis TEXT PRIMARY KEY,
            nama_enc TEXT NOT NULL,
            kelas TEXT NOT NULL,
            jenis_kelamin TEXT,
            wali_kelas TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS laporan_bulanan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nis TEXT NOT NULL,
            bulan TEXT NOT NULL,
            tahun TEXT NOT NULL,
            hadir INTEGER DEFAULT 0,
            sakit INTEGER DEFAULT 0,
            izin INTEGER DEFAULT 0,
            alpa INTEGER DEFAULT 0,
            rerata_akademik REAL DEFAULT 0.0,
            detail_nilai_enc TEXT,
            penilaian_sikap_enc TEXT,
            catatan_prestasi_enc TEXT,
            catatan_pelanggaran_enc TEXT,
            catatan_wali_kelas_enc TEXT,
            status TEXT DEFAULT 'Draf',
            FOREIGN KEY(nis) REFERENCES siswa(nis),
            UNIQUE(nis, bulan, tahun)
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                       ("admin", hash_password("admin123"), "Admin", "Administrator Utama", "19800101"))
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                       ("guru1", hash_password("guru123"), "Guru", "Dra. Siti Rahmah (Wali 11-MIPA-1)", "19850312"))
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                       ("siswa1", hash_password("siswa123"), "Siswa", "Ahmad Fauzi", "10241"))
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                       ("siswa2", hash_password("siswa123"), "Siswa", "Beatrix Anindya", "10242"))

        cursor.execute("INSERT INTO siswa VALUES (?, ?, ?, ?, ?)", 
                       ("10241", encrypt_data("Ahmad Fauzi"), "11-MIPA-1", "L", "Dra. Siti Rahmah"))
        cursor.execute("INSERT INTO siswa VALUES (?, ?, ?, ?, ?)", 
                       ("10242", encrypt_data("Beatrix Anindya"), "11-MIPA-1", "P", "Dra. Siti Rahmah"))

        sikap_1 = json.dumps({"Kedisiplinan": "Sangat Baik", "Tanggung Jawab": "Baik"})
        cursor.execute("""
            INSERT INTO laporan_bulanan (nis, bulan, tahun, hadir, sakit, izin, alpa, rerata_akademik, detail_nilai_enc, penilaian_sikap_enc, catatan_prestasi_enc, catatan_pelanggaran_enc, catatan_wali_kelas_enc, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("10241", "Januari", "2026", 20, 1, 0, 0, 88.4, "", encrypt_data(sikap_1), 
              encrypt_data("Juara 1 Olimpiade Fisika"), encrypt_data("Nihil"), 
              encrypt_data("Sangat aktif dan berprestasi tinggi."), "Final"))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database SQLite berhasil diinisialisasi dan dienkripsi.")