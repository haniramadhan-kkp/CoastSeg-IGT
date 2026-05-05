<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;

class ImportCoastSeg extends Command
{
    protected $signature = 'coastseg:import {path : Path to the portal_output directory} {--overwrite : Overwrite existing sessions in the database}';
    protected $description = 'Import CoastSeg analytical results into the database';

    public function handle()
    {
        $path = $this->argument('path');
        
        if (!File::isDirectory($path)) {
            $this->error("Directory not found: $path");
            return 1;
        }

        // Check if root or single session
        if (!File::exists("$path/session_info.json")) {
            $subFolders = File::directories($path);
            $this->info("Detected root directory. Found " . count($subFolders) . " sessions/categories to import.");
            
            foreach ($subFolders as $subFolder) {
                if (File::exists("$subFolder/session_info.json")) {
                    $this->importSession($subFolder);
                } else {
                    $this->warn("Skipping " . basename($subFolder) . ": session_info.json not found.");
                }
            }
        } else {
            $this->importSession($path);
        }

        $this->info("All imports completed successfully!");
        return 0;
    }

    protected function importSession($path)
    {
        $sessionFolderName = basename($path);
        $this->info("---------------------------------------");
        $this->info("Importing: $sessionFolderName");

        // 1. Load Session Info
        $sessionInfo = json_decode(File::get("$path/session_info.json"), true);
        $sessionName = $sessionInfo['session_name'];

        // Check for existing session
        $existingSession = DB::table('sessions')->where('name', $sessionName)->first();

        if ($existingSession) {
            if ($this->option('overwrite')) {
                $this->warn("Session '{$sessionName}' already exists. Overwriting...");
                // Cascading delete should handle related ROIs, Transects, ShorelineData
                DB::table('sessions')->where('id', $existingSession->id)->delete();
            } else {
                $this->info("Session '{$sessionName}' already exists. Skipping...");
                return;
            }
        }

        DB::transaction(function () use ($path, $sessionName) {
            $sessionId = DB::table('sessions')->insertGetId([
                'name' => $sessionName,
                'session_path' => $path,
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            // 2. Load ROIs
            $roisGeoJson = json_decode(File::get("$path/rois.geojson"), true);
            $roiMap = []; // Mapping of session_origin_ROIid to DB id
            
            foreach ($roisGeoJson['features'] as $feature) {
                $props = $feature['properties'];
                $extId = $props['id'];
                $origin = $props['session_origin'] ?? 'default';
                
                $dbId = DB::table('rois')->insertGetId([
                    'session_id' => $sessionId,
                    'external_id' => $extId,
                    'name' => "ROI $extId ($origin)",
                    'geometry' => DB::raw("ST_GeomFromGeoJSON('" . json_encode($feature['geometry']) . "')"),
                    'created_at' => now(),
                    'updated_at' => now(),
                ]);
                
                // Key format: sessionName_extId
                $roiMap["{$origin}_{$extId}"] = $dbId;
            }

            // 3. Load Transects
            $transectsGeoJson = json_decode(File::get("$path/transects.geojson"), true);
            $transectMap = [];
            
            foreach ($transectsGeoJson['features'] as $feature) {
                $props = $feature['properties'];
                $trExtId = $props['transect_id']; // This is already unique (sessionName_id) from python
                $roiExtId = $props['id']; // This is the original ROI id
                $origin = $props['session_origin'] ?? 'default';
                
                $roiDbId = $roiMap["{$origin}_{$roiExtId}"] ?? reset($roiMap);

                $dbId = DB::table('transects')->insertGetId([
                    'roi_id' => $roiDbId,
                    'external_id' => $trExtId,
                    'slope' => $props['slope'] ?? null,
                    'trend_rate' => $props['trend_rate'] ?? null,
                    'geometry' => DB::raw("ST_GeomFromGeoJSON('" . json_encode($feature['geometry']) . "')"),
                    'created_at' => now(),
                    'updated_at' => now(),
                ]);
                $transectMap[$trExtId] = $dbId;
            }

            // 4. Load Shoreline Time Series Data
            $timeseriesData = json_decode(File::get("$path/timeseries.json"), true);
            $shorelineBatch = [];
            
            foreach ($timeseriesData as $item) {
                $trExtId = $item['transect_id'];
                if (!isset($transectMap[$trExtId])) continue;

                foreach ($item['history'] as $record) {
                    $shorelineBatch[] = [
                        'transect_id' => $transectMap[$trExtId],
                        'date' => $record['dates'],
                        'distance' => $record['distance'],
                        'satname' => $record['satname'] ?? null,
                        'tide' => $record['tide'] ?? null,
                        'is_corrected' => ($sessionName === 'tidally_corrected'),
                        'created_at' => now(),
                        'updated_at' => now(),
                    ];

                    if (count($shorelineBatch) >= 1000) {
                        DB::table('shoreline_data')->insert($shorelineBatch);
                        $shorelineBatch = [];
                    }
                }
            }
            if (!empty($shorelineBatch)) {
                DB::table('shoreline_data')->insert($shorelineBatch);
            }
        });

        $this->info("Import successful for: $sessionName");
    }
}
