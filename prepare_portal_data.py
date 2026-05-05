import os
import sys
import json
import pandas as pd
import geopandas as gpd
import numpy as np
from scipy.stats import linregress
from datetime import datetime

def calculate_trend(dates, distances):
    """Calculates shoreline change rate in meters per year."""
    if len(dates) < 2:
        return 0.0
    
    # Convert dates to days from start
    start_date = min(dates)
    days = [(d - start_date).days for d in dates]
    
    slope, intercept, r_value, p_value, std_err = linregress(days, distances)
    
    # Slope is m/day, convert to m/year
    return slope * 365.25

def prepare_portal_data(session_path):
    print(f"Preparing portal data for session: {session_path}")
    
    # Define paths
    config_gdf_path = os.path.join(session_path, "config_gdf.geojson")
    
    # Prioritize tidally corrected timeseries if it exists
    corrected_ts_path = os.path.join(session_path, "tidally_corrected_transect_time_series_merged.csv")
    raw_ts_path = os.path.join(session_path, "raw_transect_time_series_merged.csv")
    
    timeseries_csv_path = corrected_ts_path if os.path.exists(corrected_ts_path) else raw_ts_path
    print(f"Using timeseries file: {timeseries_csv_path}")
    
    slopes_csv_path = os.path.join(session_path, "estimated_beach_slopes.csv")
    
    # 1. Load ROIs and Transects from config_gdf
    config_gdf = gpd.read_file(config_gdf_path)
    rois_gdf = config_gdf[config_gdf['type'] == 'roi'].copy()
    transects_gdf = config_gdf[config_gdf['type'] == 'transect'].copy()
    
    # 2. Load Timeseries & Slopes
    ts_df = pd.read_csv(timeseries_csv_path)
    ts_df['dates'] = pd.to_datetime(ts_df['dates'])
    ts_df['transect_id'] = ts_df['transect_id'].astype(str)
    
    slopes_df = pd.DataFrame(columns=['transect_id', 'slope'])
    if os.path.exists(slopes_csv_path):
        slopes_df = pd.read_csv(slopes_csv_path)
        slopes_df['transect_id'] = slopes_df['transect_id'].astype(str)
        
    # 3. Clean Transect Geometries
    transects_gdf['transect_id'] = transects_gdf['id'].astype(str)
    
    # Output structure
    output_dir = os.path.join(session_path, "portal_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Process all transects in the session
    print(f"Processing {len(transects_gdf)} transects...")
    
    roi_transects_data = []
    
    # Add columns to GeoDataFrame
    transects_gdf['slope'] = 0.0
    transects_gdf['trend_rate'] = 0.0

    for idx, tr in transects_gdf.iterrows():
        tr_id = tr['transect_id']
        tr_data = ts_df[ts_df['transect_id'] == tr_id]
        
        if tr_data.empty:
            continue
            
        # Determine which distance column to use for trend and history
        dist_col = 'cross_distance_tidally_corrected' if 'cross_distance_tidally_corrected' in tr_data.columns else 'cross_distance'

        # Robust satname detection
        sat_col = None
        for col in ['satname', 'satname_x', 'satname_y']:
            if col in tr_data.columns:
                sat_col = col
                break

        # Trend calculation using the correct distance column
        trend = calculate_trend(tr_data['dates'], tr_data[dist_col])
        
        # Slope info
        slope_val = slopes_df.loc[slopes_df['transect_id'] == tr_id, 'slope'].values
        slope_val = slope_val[0] if len(slope_val) > 0 else 0.0
        
        # Update GeoDataFrame attributes
        transects_gdf.at[idx, 'slope'] = slope_val
        transects_gdf.at[idx, 'trend_rate'] = trend
        
        # Prepare detailed timeseries for JSON chart
        # We use cross_distance_tidally_corrected if available, else cross_distance
        dist_col = 'cross_distance_tidally_corrected' if 'cross_distance_tidally_corrected' in tr_data.columns else 'cross_distance'
        
        cols_to_copy = ['dates', dist_col]
        if sat_col:
            cols_to_copy.append(sat_col)
            
        tr_history = tr_data[cols_to_copy].copy()
        tr_history.rename(columns={dist_col: 'distance'}, inplace=True)
        if sat_col:
            tr_history.rename(columns={sat_col: 'satname'}, inplace=True)
            
        tr_history['dates'] = tr_history['dates'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Add tide info if available
        if 'tide' in tr_data.columns:
            tr_history['tide'] = tr_data['tide']
            
        roi_transects_data.append({
            "transect_id": tr_id,
            "history": tr_history.to_dict(orient='records')
        })

    # Save Session Info
    session_info = {
        "session_name": os.path.basename(session_path.rstrip('/')),
        "total_transects": len(roi_transects_data),
        "exported_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(os.path.join(output_dir, "session_info.json"), 'w') as f:
        json.dump(session_info, f)

    # Save ROIs GeoJSON
    rois_gdf.to_file(os.path.join(output_dir, "rois.geojson"), driver='GeoJSON')

    # Save Transects GeoJSON (with slope & trend)
    transects_gdf.to_file(os.path.join(output_dir, "transects.geojson"), driver='GeoJSON')
    
    # Save Timeseries JSON (for charts)
    with open(os.path.join(output_dir, "timeseries.json"), 'w') as f:
        json.dump(roi_transects_data, f)

    print(f"Portal data successfully exported to: {output_dir}")

def prepare_global_portal_data(sessions_root, output_base_dir):
    """
    Aggregates all sessions into two categories: raw_data and tidally_corrected.
    """
    categories = ['raw_data', 'tidally_corrected']
    
    for cat in categories:
        print(f"\n--- Aggregating for category: {cat} ---")
        all_rois = []
        all_transects = []
        all_timeseries = []
        
        cat_output_dir = os.path.join(output_base_dir, cat)
        os.makedirs(cat_output_dir, exist_ok=True)
        
        # Get all session folders
        session_folders = [f for f in os.listdir(sessions_root) if os.path.isdir(os.path.join(sessions_root, f))]
        
        for session_name in session_folders:
            session_path = os.path.join(sessions_root, session_name)
            config_gdf_path = os.path.join(session_path, "config_gdf.geojson")
            
            if not os.path.exists(config_gdf_path):
                continue
                
            # Determine which timeseries file to use
            if cat == 'tidally_corrected':
                ts_path = os.path.join(session_path, "tidally_corrected_transect_time_series_merged.csv")
            else:
                ts_path = os.path.join(session_path, "raw_transect_time_series_merged.csv")
                
            if not os.path.exists(ts_path):
                print(f"Skipping {session_name} for {cat}: file not found.")
                continue
            
            print(f"Processing session: {session_name}")
            
            # Load Data
            config_gdf = gpd.read_file(config_gdf_path)
            ts_df = pd.read_csv(ts_path)
            ts_df['dates'] = pd.to_datetime(ts_df['dates'])
            ts_df['transect_id'] = ts_df['transect_id'].astype(str)
            
            # Load Slopes if available
            slopes_csv_path = os.path.join(session_path, "estimated_beach_slopes.csv")
            slopes_df = pd.read_csv(slopes_csv_path) if os.path.exists(slopes_csv_path) else pd.DataFrame(columns=['transect_id', 'slope'])
            if not slopes_df.empty:
                slopes_df['transect_id'] = slopes_df['transect_id'].astype(str)

            # Process ROIs
            rois = config_gdf[config_gdf['type'] == 'roi'].copy()
            # Prefix ID with session name to ensure uniqueness
            rois['session_origin'] = session_name
            all_rois.append(rois)
            
            # Process Transects
            transects = config_gdf[config_gdf['type'] == 'transect'].copy()
            transects['transect_id'] = transects['id'].astype(str)
            transects['session_origin'] = session_name
            
            # Join with timeseries for trend calculation
            for idx, tr in transects.iterrows():
                tr_id = tr['transect_id']
                tr_data = ts_df[ts_df['transect_id'] == tr_id]
                
                if tr_data.empty:
                    continue
                
                dist_col = 'cross_distance_tidally_corrected' if 'cross_distance_tidally_corrected' in tr_data.columns else 'cross_distance'
                
                # Robust satname detection
                sat_col = None
                for col in ['satname', 'satname_x', 'satname_y']:
                    if col in tr_data.columns:
                        sat_col = col
                        break

                trend = calculate_trend(tr_data['dates'], tr_data[dist_col])
                
                slope_val = slopes_df.loc[slopes_df['transect_id'] == tr_id, 'slope'].values
                slope_val = slope_val[0] if len(slope_val) > 0 else 0.0
                
                transects.at[idx, 'slope'] = slope_val
                transects.at[idx, 'trend_rate'] = trend
                
                # Timeseries history
                cols_to_copy = ['dates', dist_col]
                if sat_col:
                    cols_to_copy.append(sat_col)
                    
                tr_history = tr_data[cols_to_copy].copy()
                tr_history.rename(columns={dist_col: 'distance'}, inplace=True)
                if sat_col:
                    tr_history.rename(columns={sat_col: 'satname'}, inplace=True)
                
                tr_history['dates'] = tr_history['dates'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                if 'tide' in tr_data.columns:
                    tr_history['tide'] = tr_data['tide']
                
                all_timeseries.append({
                    "transect_id": f"{session_name}_{tr_id}", # Unique ID
                    "session_origin": session_name,
                    "history": tr_history.to_dict(orient='records')
                })
            
            # Update transect_id in GeoJSON to be unique across sessions
            transects['transect_id'] = session_name + "_" + transects['transect_id']
            all_transects.append(transects)

        # Merge and Save
        if all_rois:
            merged_rois = pd.concat(all_rois)
            merged_rois.to_file(os.path.join(cat_output_dir, "rois.geojson"), driver='GeoJSON')
            
            merged_transects = pd.concat(all_transects)
            merged_transects.to_file(os.path.join(cat_output_dir, "transects.geojson"), driver='GeoJSON')
            
            with open(os.path.join(cat_output_dir, "timeseries.json"), 'w') as f:
                json.dump(all_timeseries, f)
            
            # Save Category Info
            cat_info = {
                "session_name": cat, # Laravel expects this as session name
                "total_rois": len(merged_rois),
                "total_transects": len(merged_transects),
                "exported_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(os.path.join(cat_output_dir, "session_info.json"), 'w') as f:
                json.dump(cat_info, f)

            print(f"✅ Category {cat} exported successfully with {len(all_rois)} sessions.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prepare_portal_data.py <path_to_session> OR --global <sessions_root> <output_dir>")
    elif sys.argv[1] == "--global":
        prepare_global_portal_data(sys.argv[2], sys.argv[3])
    else:
        prepare_portal_data(sys.argv[1])
