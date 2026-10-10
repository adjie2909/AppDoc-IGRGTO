# AppDoc IGRGTO 📄

**AppDoc IGRGTO** adalah aplikasi berbasis web yang dibangun dengan framework **Django** untuk mengelola, mengarsipkan, serta memfasilitasi proses persetujuan (approval) dan penelusuran dokumen operasional internal (seperti Berita Acara pembatalan struk, perubahan sortasi, perbaikan biaya/acost, dan dokumen toko lainnya) secara terpusat dan terstruktur.

---

## 🚀 Fitur Utama

- **Autentikasi & Manajemen Akun (`accounts`)**:
  - Login, logout, dan manajemen sesi pengguna.
  - Pembatasan hak akses berbasis peran (role-based access) untuk staf operasional dan verifikator.
- **Pengelolaan Berita Acara & Dokumen (`documents`)**:
  - Unggah dan arsip dokumen digital (format PDF).
  - Pengelompokan dokumen berdasarkan tahun/bulan secara otomatis.
  - Pencarian dan monitoring status verifikasi/approval Berita Acara operasional toko.
- **Penyimpanan Terstruktur**:
  - Penataan berkas lampiran pendukung operasional yang rapi dan aman.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+ / 3.13, Django
- **Database**: SQLite (Default Development) / PostgreSQL (Production ready)
- **Frontend**: Django Templates, Bootstrap 5, HTML5/CSS3/JavaScript
- **File Storage**: Django FileField / Media Storage (PDF Handling)

---

## 📂 Struktur Direktori

```text
AppDoc-IGRGTO/
├── accounts/               # Modul manajemen akun dan autentikasi
│   ├── migrations/         # Skema migrasi database akun
│   ├── forms.py            # Form login, profil, dan validasi
│   ├── models.py           # Model pengguna kustom / relasi profil
│   ├── urls.py             # Routing URL untuk modul accounts
│   └── views.py            # Logika kontrol autentikasi
├── config/                 # Konfigurasi inti proyek Django
│   ├── settings.py         # Pengaturan lingkungan, database, & apps
│   ├── urls.py             # URL routing utama
│   ├── wsgi.py             # WSGI entry point
│   └── asgi.py             # ASGI entry point
├── documents/              # Berkas media / dokumen operasional yang diunggah
├── db.sqlite3              # Database lokal (SQLite)
├── manage.py               # Utilitas baris perintah Django
└── README.md               # Dokumentasi proyek

# Masuk ke direktori proyek
cd AppDoc-IGRGTO

# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment
# Di Windows (CMD/PowerShell):
venv\Scripts\activate
# Di Linux/macOS:
source venv/bin/activate

Bash
pip install -r requirements.txt

# Jalankan migrasi database
python manage.py makemigrations
python manage.py migrate

# Buat akun Superuser (Admin)
python manage.py createsuperuser

python manage.py runserver