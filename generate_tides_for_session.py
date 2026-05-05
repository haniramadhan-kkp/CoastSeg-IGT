import os
import sys
import pandas as pd
import geopandas as gpd
import numpy as np
from scipy.signal import lombscargle
from tqdm import tqdm
import coastseg
from coastseg import tide_correction
from coastseg import common

def estimate_slope_lombscargle(dates, distances, tides, min_slope=0.01, max_slope=0.2, step=0.002):
    """
    Estimates beach slope using spectral energy minimization (CoastSat.slope).
    """
    t = (dates - dates.min()).dt.total_seconds().values
    slopes = np.arange(min_slope, max_slope + step, step)
    energies = []
    f_tidal = 2 * np.pi / (12.42 * 3600) 
    
    for s in slopes:
        x_corr = distances - (tides / s)
        x_detrend = x_corr - np.mean(x_corr)
        pgram = lombscargle(t, x_detrend, [f_tidal], precenter=True)
        energies.append(pgram)

    best_slope = slopes[np.argmin(energies)]
    return best_slope

def prepare_tides_and_slopes(session_path, limit_one=False):

    print(f"Processing session: {session_path}")
    
    config_path = os.path.join(session_path, "config_gdf.geojson")
    raw_timeseries_path = os.path.join(session_path, "raw_transect_time_series_merged.csv")

    if not os.path.exists(config_path) or not os.path.exists(raw_timeseries_path):
        print(f"Error: Missing required files in {session_path}")
        return

    # 1. Load Data
    print("Loading data...")
    raw_timeseries_df = pd.read_csv(raw_timeseries_path)
    raw_timeseries_df['dates'] = pd.to_datetime(raw_timeseries_df['dates'], utc=True)
    # Ensure transect_id is string
    raw_timeseries_df['transect_id'] = raw_timeseries_df['transect_id'].astype(str)

    transects_gdf = tide_correction.read_and_filter_geojson(config_path)
    # The GeoJSON usually has 'id' column which becomes 'transect_id' in predict_tides
    if 'id' in transects_gdf.columns:
        transects_gdf['id'] = transects_gdf['id'].astype(str)
    if 'transect_id' in transects_gdf.columns:
        transects_gdf['transect_id'] = transects_gdf['transect_id'].astype(str)

    # 2. Filter to common transects
    available_ids = raw_timeseries_df['transect_id'].unique()
    print(f"Transect IDs available in timeseries: {available_ids[:10]}... (Total: {len(available_ids)})")
    
    # Filter transects_gdf to only include those in available_ids
    # We need to find which column in transects_gdf corresponds to the ID
    id_col = 'id' if 'id' in transects_gdf.columns else 'transect_id'
    transects_gdf = transects_gdf[transects_gdf[id_col].isin(available_ids)]
    
    if transects_gdf.empty:
        print("Error: No matching transects found between GeoJSON and timeseries.")
        return

    # 3. Predict Tides
    print(f"Predicting tides for {len(transects_gdf)} transects...")
    base_dir = os.path.dirname(coastseg.__file__)
    model_regions_geojson_path = os.path.join(base_dir, "tide_model", "tide_regions_map.geojson")
    tide_model_path = os.path.abspath("tide_model")
    if not os.path.exists(tide_model_path):
        tide_model_path = os.path.join(os.path.dirname(base_dir), "tide_model")

    tide_model_config = tide_correction.setup_tide_model_config(tide_model_path, model="FES2022")

    predicted_tides_df = tide_correction.predict_tides(
        transects_gdf,
        raw_timeseries_df,
        model_regions_geojson_path,
        tide_model_config,
    )

    if predicted_tides_df.empty:
        print("No tides predicted.")
        return

    # Save tides in Long Format (Format 2) for better compatibility
    output_tide_file = os.path.join(session_path, "predicted_tides.csv")
    predicted_tides_df.to_csv(output_tide_file, index=False)
    print(f"Saved predicted tides to {output_tide_file} (Long Format)")

    # 4. Estimate Slopes
    print("Estimating beach slopes...")
    # predicted_tides_df already has [dates, transect_id, tide]
    df_merged = pd.merge(raw_timeseries_df, predicted_tides_df, on=['dates', 'transect_id'], how='inner')
    
    slope_results = []
    unique_transects = df_merged['transect_id'].unique()
    
    for tid in tqdm(unique_transects, desc="Estimating Slopes"):
        subset = df_merged[df_merged['transect_id'] == tid].dropna(subset=['cross_distance', 'tide'])
        if len(subset) < 5: # Lowered for debugging, though lombscargle needs more for quality
            print(f"Warning: Only {len(subset)} points for transect {tid}")
        
        if len(subset) < 3:
            continue
            
        best_s = estimate_slope_lombscargle(
            subset['dates'], subset['cross_distance'], subset['tide']
        )
        
        slope_results.append({
            'transect_id': tid,
            'slope': round(best_s, 4)
        })

    if slope_results:
        slope_df = pd.DataFrame(slope_results)
        output_slope_file = os.path.join(session_path, "estimated_beach_slopes.csv")
        slope_df.to_csv(output_slope_file, index=False)
        print(f"Saved estimated slopes to {output_slope_file}")
        print(slope_df)
    else:
        print("No slopes could be estimated.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generate_tides_for_session.py <path_to_session>")
    else:
        prepare_tides_and_slopes(sys.argv[1])
