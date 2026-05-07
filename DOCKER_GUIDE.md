# Panduan Instalasi Universal CoastSeg-IGT (Docker)

Proyek ini telah dikonfigurasi agar dapat dijalankan dengan mudah menggunakan Docker di **Windows (WSL2)**, **macOS (Intel & M1/M2/M3)**, dan **Linux**. 

## Keuntungan Menggunakan Docker
- **Tanpa Konflik Library**: Tidak perlu menginstal Python, GDAL, atau TensorFlow secara manual.
- **Konsistensi**: Apa yang berjalan di laptop pengembang akan berjalan sama persis di laptop Anda.
- **Isolasi**: Lingkungan proyek tidak akan mengganggu perangkat lunak lain di komputer Anda.

---

## 1. Persiapan: Instalasi Docker

Pastikan Docker Desktop sudah terpasang di komputer Anda:

- **Windows**: Instal [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/) (Gunakan backend WSL2).
- **macOS**: Instal [Docker Desktop](https://docs.docker.com/desktop/install/mac-install/) (Pilih versi Apple Silicon untuk chip M1/M2/M3).
- **Linux**: Instal [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) dan [Docker Compose](https://docs.docker.com/compose/install/).

---

## 2. Cara Menjalankan Proyek

1. **Buka Terminal** (CMD, PowerShell, atau Terminal Mac/Linux) di folder proyek ini.
2. **Jalankan Perintah Build & Up**:
   ```bash
   docker compose up -d --build
   ```
   *Catatan: Proses pertama kali mungkin memakan waktu 5-10 menit untuk mengunduh semua library.*
3. **Akses Aplikasi**:
   Buka browser Anda dan masukkan alamat:
   [http://localhost:8889](http://localhost:8889)

---

## 3. Catatan Khusus Pengguna Mac (M1/M2/M3)

Proyek ini telah diotomatisasi untuk menggunakan **Rosetta 2**. 
- Anda tidak perlu melakukan pengaturan tambahan. 
- Baris `platform: linux/amd64` di file konfigurasi kami akan memberitahu Docker untuk menjalankan lingkungan Intel yang stabil di atas chip Apple Silicon Anda secara otomatis.
- Jika Docker menanyakan izin untuk menggunakan Rosetta, pilih **"Allow"** atau **"Install"**.

---

## 4. Tips Penggunaan

### Menghentikan Aplikasi
Untuk mematikan sistem tanpa menghapus data:
```bash
docker compose stop
```

### Menjalankan Kembali
Setelah instalasi pertama, Anda cukup menjalankan:
```bash
docker compose start
```

### Reset Lingkungan (Jika Error)
Jika terjadi masalah pada library, Anda bisa membangun ulang dari nol:
```bash
docker compose down
docker compose up -d --build
```

### Lokasi Data
Data Anda **TIDAK AKAN HILANG** meskipun container dihapus. Folder berikut disinkronkan langsung dengan laptop Anda:
- `/data`: Hasil download citra satelit.
- `/sessions`: Hasil ekstraksi garis pantai.
- `/logs`: Catatan aktivitas sistem.

---

## 5. Troubleshooting (Masalah Umum)

- **Port 8889 sudah digunakan**: Jika muncul error port, buka `docker-compose.yml` dan ubah angka `8889` menjadi angka lain (misal `9000`).
- **Memory/RAM Low**: CoastSeg membutuhkan minimal 4GB RAM yang dialokasikan ke Docker (cek di Docker Desktop Settings -> Resources).
- **Gagal Login GEE**: Pastikan Anda sudah memiliki akun Google Earth Engine dan ikuti instruksi autentikasi di dalam notebook.

---
*Panduan ini dibuat untuk memastikan CoastSeg-IGT dapat diakses oleh semua peneliti dengan hambatan teknis seminimal mungkin.*
