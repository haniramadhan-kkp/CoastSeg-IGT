# Panduan Instalasi Cepat CoastSeg-IGT (Docker)

Proyek ini telah dikonfigurasi agar dapat dijalankan dengan mudah menggunakan Docker. Tidak perlu menginstal Python, GDAL, atau TensorFlow secara manual di komputer Anda.

## Prasyarat: Instalasi Docker

Sebelum memulai, pastikan Anda telah menginstal Docker di komputer Anda:

### 1. Windows
- Unduh dan instal **[Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)**.
- Saat instalasi, pastikan opsi **"Use WSL 2 instead of Hyper-V"** dicentang (direkomendasikan).
- Restart komputer setelah instalasi selesai.

### 2. macOS
- Unduh dan instal **[Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)**.
- Pilih versi yang sesuai dengan prosesor Anda (**Apple Silicon** untuk M1/M2/M3 atau **Intel Chip** untuk Mac lama).

### 3. Linux (Ubuntu/Debian)
Jalankan perintah berikut di terminal:
```bash
# Hapus versi lama jika ada
sudo apt-get remove docker docker-engine docker.io containerd runc

# Instal Docker Engine & Compose
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Tambahkan user ke grup docker (agar tidak perlu sudo setiap saat)
sudo usermod -aG docker $USER
```
*Catatan: Anda mungkin perlu logout dan login kembali agar perubahan grup berlaku.*

## Langkah-langkah Menjalankan CoastSeg

### Opsi A: Menggunakan Terminal (Paling Cepat)
1.  **Buka Terminal** (atau CMD/PowerShell) di folder proyek ini.
2.  **Jalankan Perintah:**
    ```bash
    docker compose up
    ```
3.  **Buka Browser** dan akses: `http://localhost:8889`

### Opsi B: Mengelola via Antarmuka Grafis (Docker Desktop GUI)
Meskipun pemicu awal harus melalui terminal, setelah itu Anda bisa mengelolanya tanpa mengetik lagi:

1.  **Inisialisasi (Hanya Sekali):** Jalankan perintah `docker compose up -d` di terminal pada folder proyek. Perintah `-d` (detached) akan menjalankan aplikasi di latar belakang.
2.  **Buka Docker Desktop:** Klik tab **"Containers"** di kolom sebelah kiri.
3.  **Muncul sebagai Group:** Anda akan melihat grup bernama `coastseg-igt` (atau sesuai nama folder proyek Anda).
4.  **Kontrol Mouse:**
    -   **Start/Stop:** Gunakan tombol **Play/Stop** di sebelah kanan nama proyek untuk menyalakan atau mematikan seluruh sistem.
    -   **Open in Browser:** Klik ikon **"Open with browser"** atau klik angka port `8889:8888` untuk langsung membuka Jupyter Lab.
    -   **Logs:** Klik nama grup proyek untuk melihat pesan sistem jika terjadi error.
    -   **Cleanup:** Jika ingin menghapus container untuk menghemat ruang (tanpa menghapus data), klik ikon **Tempat Sampah (Delete)**.

## Catatan Penting
- **Data Tetap Aman**: Semua data yang diunduh di folder `data/` dan `sessions/` akan tersimpan di komputer Anda, bukan di dalam container. Jika container dihapus, data Anda tidak akan hilang.
- **CoastSat Classifier**: Model `best.h5` sudah otomatis terpasang dan siap digunakan di dalam notebook `SDS_coastsat_classifier.ipynb`.
- **Berhenti**: Tekan `Ctrl+C` di terminal untuk menghentikan aplikasi.

---
*Dibuat untuk memudahkan kolaborasi dan pengajaran CoastSeg-IGT.*
