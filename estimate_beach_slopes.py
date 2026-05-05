import os
import pandas as pd
import numpy as np
from scipy.signal import lombscargle
import matplotlib.pyplot as plt
from tqdm import tqdm

def estimate_slope_lombscargle(dates, distances, tides, min_slope=0.01, max_slope=0.2, step=0.002):
    """
    Mengestimasi slope pantai menggunakan metode minimalisasi energi spektral (CoastSat.slope).
    """
    # Konversi tanggal ke detik (untuk Lomb-Scargle)
    t = (dates - dates.min()).dt.total_seconds().values
    
    # Definisikan rentang slope yang akan dicoba
    slopes = np.arange(min_slope, max_slope + step, step)
    energies = []

    # Identifikasi frekuensi dominan pasang surut (M2 tide ~ 12.42 jam)
    # Karena data satelit jarang, kita mencari energi pada rentang frekuensi pasut
    # Frekuensi dalam radian/detik
    f_tidal = 2 * np.pi / (12.42 * 3600) 
    
    for s in slopes:
        # Koreksi pasut pada jarak pantai: x_corr = x - (tide / slope)
        x_corr = distances - (tides / s)
        
        # Hilangkan tren (detrend) agar fokus pada fluktuasi
        x_detrend = x_corr - np.mean(x_corr)
        
        # Hitung Lomb-Scargle Periodogram pada frekuensi pasut
        # Kita mengevaluasi "kekuatan" sinyal pasut yang tersisa di garis pantai
        pgram = lombscargle(t, x_detrend, [f_tidal], precenter=True)
        energies.append(pgram[0])

    # Slope terbaik adalah yang meminimalkan energi pada frekuensi pasut
    best_slope = slopes[np.argmin(energies)]
    return best_slope, slopes, energies

def run_slope_estimation(session_path):
    """
    Menjalankan estimasi slope untuk seluruh transek dalam satu sesi CoastSeg.
    """
    print(f"Menganalisis data di: {session_path}")
    
    # 1. Load data garis pantai
    shoreline_file = os.path.join(session_path, "raw_transect_time_series_merged.csv")
    tide_file = os.path.join(session_path, "predicted_tides.csv")
    
    if not os.path.exists(shoreline_file) or not os.path.exists(tide_file):
        print("Error: File data tidak ditemukan. Pastikan Anda sudah menjalankan 'Extract Shorelines' dan 'Tide Correction' di CoastSeg.")
        return

    df_shore = pd.read_csv(shoreline_file)
    df_shore['dates'] = pd.to_datetime(df_shore['dates'])
    
    # 2. Load data pasut (format matrix) dan ubah ke format long
    df_tide_matrix = pd.read_csv(tide_file)
    df_tide_matrix['dates'] = pd.to_datetime(df_tide_matrix['dates'])
    df_tide = df_tide_matrix.melt(id_vars=['dates'], var_name='transect_id', value_name='tide')
    df_tide['transect_id'] = df_tide['transect_id'].astype(str)
    df_shore['transect_id'] = df_shore['transect_id'].astype(str)

    # 3. Gabungkan data
    df_merged = pd.merge(df_shore, df_tide, on=['dates', 'transect_id'], how='inner')
    
    results = []
    unique_transects = df_merged['transect_id'].unique()
    
    print(f"Menghitung slope untuk {len(unique_transects)} transek...")
    
    for tid in tqdm(unique_transects):
        subset = df_merged[df_merged['transect_id'] == tid].dropna(subset=['cross_distance', 'tide'])
        
        # Minimal butuh 30 titik data untuk analisis frekuensi yang layak
        if len(subset) < 30:
            continue
            
        best_s, slopes, energies = estimate_slope_lombscargle(
            subset['dates'], subset['cross_distance'], subset['tide']
        )
        
        results.append({
            'transect_id': tid,
            'estimated_slope': round(best_s, 4),
            'n_points': len(subset)
        })

    # 4. Simpan hasil
    output_df = pd.DataFrame(results)
    output_path = os.path.join(session_path, "estimated_beach_slopes.csv")
    output_df.to_csv(output_path, index=False)
    
    print(f"\nSelesai! Hasil disimpan di: {output_path}")
    print(output_df.head())

if __name__ == "__main__":
    # Ganti dengan path folder session Anda
    # Contoh: session_path = "sessions/my_session_name"
    import sys
    if len(sys.argv) > 1:
        run_slope_estimation(sys.argv[1])
    else:
        print("Gunakan: python estimate_beach_slopes.py <path_ke_folder_session>")
