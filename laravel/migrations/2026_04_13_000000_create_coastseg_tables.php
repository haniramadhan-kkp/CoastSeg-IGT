<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up() {
        // Enable PostGIS extension
        DB::statement('CREATE EXTENSION IF NOT EXISTS postgis');

        Schema::create('sessions', function (Blueprint $table) {
            $table->id();
            $table->string('name')->unique();
            $table->string('session_path');
            $table->json('bounds')->nullable();
            $table->timestamps();
        });

        Schema::create('rois', function (Blueprint $table) {
            $table->id();
            $table->foreignId('session_id')->constrained()->onDelete('cascade');
            $table->string('external_id');
            $table->string('name');
            // Use PostGIS geometry type (Polygon, SRID 4326 for WGS84)
            $table->geometry('geometry', 'polygon', 4326); 
            $table->timestamps();
        });

        Schema::create('transects', function (Blueprint $table) {
            $table->id();
            $table->foreignId('roi_id')->constrained()->onDelete('cascade');
            $table->string('external_id');
            $table->double('slope')->nullable();
            $table->double('trend_rate')->nullable(); // meter/year
            // Use PostGIS geometry type (LineString, SRID 4326)
            $table->geometry('geometry', 'linestring', 4326);
            $table->timestamps();
        });

        Schema::create('shoreline_data', function (Blueprint $table) {
            $table->id();
            $table->foreignId('transect_id')->constrained()->onDelete('cascade');
            $table->dateTime('date');
            $table->double('distance');
            $table->string('satname')->nullable(); // Satellite source (e.g., L8, S2)
            $table->double('tide')->nullable();
            $table->boolean('is_corrected')->default(false);
            $table->timestamps();
        });
    }

    public function down() {
        Schema::dropIfExists('shoreline_data');
        Schema::dropIfExists('transects');
        Schema::dropIfExists('rois');
        Schema::dropIfExists('sessions');
    }
};
