# AppDoc IGRGTO

Aplikasi Verifikasi dan Approval Dokumen Berjenjang (Staff -> Supervisor -> Junior Manajer -> Store Administration Manager -> Store Manager).

## Fitur Utama
- **Autentikasi Kustom**: UserID alfanumerik 3 karakter (uppercase) dengan upload spesimen tanda tangan digital (maks. 2MB).
- **Pratinjau PDF.js**: Viewer PDF interaktif di dalam browser tanpa perlu unduh file.
- **Approval Interaktif**:
  - Validasi kata sandi approver via modal.
  - Penempatan stempel tanda tangan dengan fitur drag & resize presisi berbasis persentase canvas (`interact.js`).
- **Reject Validasi Ketat**: Alasan penolakan minimal 15 karakter dengan proteksi regex dari input simbol/karakter acak.
- **Desain Khusus**: Tema Biru (#0D47A1), Merah (#D32F2F), dan Putih (#FFFFFF & #F5F7FB).

## Panduan Menjalankan Project

### 1. Setup Virtual Environment
```bash
python -m venv env
# Windows:
env\Scripts\activate
# Linux/MacOS:
source env/bin/activate