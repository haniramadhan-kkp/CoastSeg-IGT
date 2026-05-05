# CoastSeg Data Portal Development Guide (Global Category Architecture)

This document is intended for an AI Agent to help build the Laravel backend and frontend for the CoastSeg Data Portal.

## Project Context
The goal is to visualize coastal change data processed by CoastSeg. The architecture has shifted from individual "Analysis Sessions" to **Global Categories** to allow side-by-side comparison of Raw vs. Tidally Corrected data across all processed regions.

### Core Data Categories
1.  **raw_data**: Aggregated data from all sessions using `raw_transect_time_series_merged.csv`.
2.  **tidally_corrected**: Aggregated data from all sessions using `tidally_corrected_transect_time_series_merged.csv`.

### Data Distribution Structure (`global_portal_output/`)
- `raw_data/` & `tidally_corrected/`
    - `session_info.json`: Metadata for the category (name, total ROIs, export date).
    - `rois.geojson`: Polygon geometry of all ROIs from all sessions.
        - **New Attribute**: `session_origin` (original session folder name).
    - `transects.geojson`: Line geometries for all transects.
        - **New Attribute**: `transect_id` format is `{session_origin}_{original_id}` (e.g., `bali_beach_wkq69`).
        - **New Attribute**: `session_origin`.
    - `timeseries.json`: Array of objects with history per `transect_id`.

## Database Architecture
Use the provided migration in `laravel/migrations/`.
- **Sessions Table**: Now stores "Virtual Sessions" (e.g., "Raw Data", "Tidally Corrected").
- **ROIs Table**: Geographic areas. Each ROI belongs to a Category (Virtual Session).
- **Transects Table**: Primary unit. `external_id` matches the unique `{session_origin}_{id}` string.
- **Shoreline Data Table**: Historical measurements. `is_corrected` flag is set to `true` if the parent session is `tidally_corrected`.

## Implementation Roadmap

### 1. Ingestion Logic (`ImportCoastSeg.php`)
The importer now handles global categories:
- **Atomicity**: Uses `DB::transaction` per category.
- **Uniqueness**: Uses `session_origin` + `id` to map ROIs to Transects correctly.
- **Cleanup**: Supports `--overwrite` to refresh an entire category.

### 2. API Development
- `GET /api/sessions`: List categories (Raw Data, Tidally Corrected).
- `GET /api/sessions/{id}/map-data`: Returns GeoJSON of all ROIs and Transects for that category.
- **Optimization**: Since categories contain data from all sessions, use BBox filtering (`ST_Intersects`) for the map API to maintain performance.

### 3. Frontend Visualization
- **Session Switcher**: Allow users to toggle between "Raw" and "Corrected" views.
- **ROI Identification**: Display the `session_origin` in the ROI/Transect popup to tell users which original session the data came from.
- **Chart Logic**: When viewing a transect, the history is fetched from the `shoreline_data` table linked to the unique `transect_id`.

## Dynamic Filtering & Trend Calculation

The portal must allow users to filter shoreline data by satellite type (e.g., Landsat 8, Sentinel-2) and see the trend rate (m/year) update dynamically.

### 1. Database Support
The `shoreline_data` table now includes a `satname` column. Ensure this column is returned in the `/api/transects/{id}/history` endpoint.

### 2. Frontend Strategy (Client-Side Filtering)
For the best user experience, perform filtering and recalculation in the browser:
- **UI Component**: Add a checkbox group (e.g., using Alpine.js) listing all unique satellites found in the transect history.
- **Filtering**: When checkboxes change, filter the `history` array to include only the selected `satname` values.
- **Trend Recalculation**: Use a JavaScript library (e.g., `simple-statistics` or a custom linear regression function) to calculate the slope of the filtered data.
    - **Formula**: `Slope (m/day) * 365.25 = Trend (m/year)`.
    - **X-Axis**: Convert `dates` to days elapsed since the first point.
    - **Y-Axis**: Use the `distance` value.
- **Visualization**: Update the Chart.js/Plotly chart and the "Trend Rate" label on the dashboard based on the new calculation.

### 3. Backend Strategy (Alternative)
If performance becomes an issue with large datasets:
- The API `/api/transects/{id}/history` should accept a `satellites` query parameter (e.g., `?satellites[]=L8&satellites[]=S2`).
- The backend will filter the database query and return the pre-calculated `new_trend_rate` in the JSON response.

## Technical Notes for AI Agent

### Unique ID Strategy
To prevent collisions between different sessions that might use the same internal IDs (e.g., both "Beach A" and "Beach B" having a transect with ID `1`), the Python export script prefixes all IDs:
`transect_id = f"{session_name}_{original_id}"`

### Spatial Query Example (PostGIS)
To fetch only ROIs belonging to the "Tidally Corrected" category within the visible map area:
```sql
SELECT id, external_id, ST_AsGeoJSON(geometry) 
FROM rois 
WHERE session_id = (SELECT id FROM sessions WHERE name = 'tidally_corrected')
AND ST_Intersects(geometry, ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326));
```

### Data Sync Workflow
1.  **CoastSeg**: Run `Automation_Tidal_Correction.ipynb` (Cell 6) to generate `global_portal_output/`.
2.  **Sync**: Run `python sync_portal_to_laravel.py` to move data to Laravel storage.
3.  **Laravel**: Run `php artisan coastseg:import storage/app/coastseg_data --overwrite`.
