import os
import shutil
from pathlib import Path

def sync_portal_data():
    # 1. Konfigurasi Path
    current_dir = os.path.abspath(os.getcwd())
    sessions_dir = os.path.join(current_dir, "sessions")
    global_output_dir = os.path.join(current_dir, "global_portal_output")
    
    # Target direktori di Laravel (mengikuti struktur storage Laravel)
    laravel_target_root = os.path.join(current_dir, "laravel", "storage", "app", "coastseg_data")
    
    print(f"🔍 Mencari data portal...")
    print(f"📂 Target sinkronisasi: {laravel_target_root}")
    
    # Buat direktori target jika belum ada
    if not os.path.exists(laravel_target_root):
        os.makedirs(laravel_target_root, exist_ok=True)

    count = 0

    # 2. PRIORITAS: Sync dari global_portal_output (Raw vs Corrected)
    if os.path.exists(global_output_dir):
        print(f"🌍 Mendeteksi Global Portal Output di: {global_output_dir}")
        for category in ['raw_data', 'tidally_corrected']:
            cat_path = os.path.join(global_output_dir, category)
            if os.path.exists(cat_path):
                target_cat_dir = os.path.join(laravel_target_root, category)
                if os.path.exists(target_cat_dir):
                    shutil.rmtree(target_cat_dir)
                shutil.copytree(cat_path, target_cat_dir)
                print(f"✅ Berhasil menyalin Kategori: {category} -> {target_cat_dir}")
                count += 1

    # 3. FALLBACK: Iterasi setiap folder di sessions/ (Legacy)
    # Kita tetap simpan ini agar sesi lama tetap bisa disinkronkan jika diinginkan
    print(f"\n📂 Mencari sesi individual di: {sessions_dir}...")
    for session_name in os.listdir(sessions_dir):
        session_path = os.path.join(sessions_dir, session_name)
        
        if not os.path.isdir(session_path):
            continue
            
        # Cari folder portal_output
        # Mendukung struktur flat (sessions/name/portal_output) 
        # dan struktur nested (sessions/name/name/portal_output)
        portal_src = None
        
        # Cek level 1
        possible_path_1 = os.path.join(session_path, "portal_output")
        # Cek level 2 (nested)
        possible_path_2 = os.path.join(session_path, session_name, "portal_output")
        
        if os.path.exists(possible_path_1):
            portal_src = possible_path_1
        elif os.path.exists(possible_path_2):
            portal_src = possible_path_2
            
        if portal_src:
            target_session_dir = os.path.join(laravel_target_root, session_name)
            
            # Hapus jika sudah ada (overwrite)
            if os.path.exists(target_session_dir):
                shutil.rmtree(target_session_dir)
            
            # Copy data portal ke folder Laravel
            shutil.copytree(portal_src, target_session_dir)
            print(f"✅ Berhasil menyalin: {session_name} -> {target_session_dir}")
            count += 1
        else:
            print(f"⚠️  Melewati {session_name}: portal_output tidak ditemukan.")

    print(f"\n✨ Selesai! {count} sesi berhasil disinkronkan ke Laravel.")

if __name__ == "__main__":
    sync_portal_data()
