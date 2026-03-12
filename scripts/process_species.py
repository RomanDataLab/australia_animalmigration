"""
Process species distribution data for CircuitScape analysis.

Converts species occurrence data into current and future habitat maps.
"""

import os
import json
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from species_classification import get_species_group, get_all_species_by_group

DATA_DIR = Path(__file__).parent.parent / "data"
SPECIES_DIR = DATA_DIR / "species"
OUTPUT_DIR = DATA_DIR / "output"

# Australia bounding box (approximate)
AUSTRALIA_BOUNDS = {
    'minx': 113.0,  # West
    'miny': -44.0,  # South
    'maxx': 154.0,  # East
    'maxy': -10.0   # North
}

# Resolution for habitat maps (degrees)
RESOLUTION = 0.05  # ~5km at equator

def create_habitat_raster(occurrences, bounds, resolution, output_file):
    """
    Create a habitat raster from species occurrence points.
    
    Parameters:
    -----------
    occurrences : GeoDataFrame
        Species occurrence points
    bounds : dict
        Bounding box {'minx', 'miny', 'maxx', 'maxy'}
    resolution : float
        Cell size in degrees
    output_file : Path
        Output raster file path
    """
    # Calculate raster dimensions
    width = int((bounds['maxx'] - bounds['minx']) / resolution)
    height = int((bounds['maxy'] - bounds['miny']) / resolution)
    
    # Create empty raster
    raster = np.zeros((height, width), dtype=np.float32)
    
    # Rasterize points
    for idx, point in occurrences.iterrows():
        if point.geometry.geom_type == 'Point':
            x = point.geometry.x
            y = point.geometry.y
            
            # Convert to raster coordinates
            col = int((x - bounds['minx']) / resolution)
            row = int((bounds['maxy'] - y) / resolution)
            
            if 0 <= row < height and 0 <= col < width:
                raster[row, col] = 1.0
    
    # Apply smoothing/kernel to create habitat suitability
    # This is a simple example - you'd use actual habitat modeling
    from scipy import ndimage
    kernel = np.ones((3, 3)) / 9
    raster = ndimage.convolve(raster, kernel, mode='constant')
    
    # Create transform
    transform = from_bounds(
        bounds['minx'], bounds['miny'],
        bounds['maxx'], bounds['maxy'],
        width, height
    )
    
    # Write raster
    with rasterio.open(
        output_file,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=raster.dtype,
        crs='EPSG:4326',
        transform=transform,
        compress='lzw'
    ) as dst:
        dst.write(raster, 1)
    
    print(f"Created habitat raster: {output_file}")

def process_species_file(species_file, species_name):
    """
    Process a single species file and create habitat maps.
    
    Parameters:
    -----------
    species_file : Path
        Path to species occurrence JSON file
    species_name : str
        Species name
    """
    print(f"\nProcessing {species_name}...")
    
    # Load occurrence data
    with open(species_file, 'r') as f:
        data = json.load(f)
    
    # Convert to GeoDataFrame
    # Note: ALA API format may vary - adjust as needed
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and 'records' in data:
        records = data['records']
    else:
        records = [data]
    
    # Extract coordinates
    points = []
    for record in records:
        if 'decimalLongitude' in record and 'decimalLatitude' in record:
            lon = record['decimalLongitude']
            lat = record['decimalLatitude']
            
            # Filter to Australia bounds
            if (AUSTRALIA_BOUNDS['minx'] <= lon <= AUSTRALIA_BOUNDS['maxx'] and
                AUSTRALIA_BOUNDS['miny'] <= lat <= AUSTRALIA_BOUNDS['maxy']):
                points.append({
                    'geometry': Point(lon, lat),
                    'species': species_name
                })
    
    if not points:
        print(f"No valid occurrence points found for {species_name}")
        return
    
    gdf = gpd.GeoDataFrame(points, crs='EPSG:4326')
    print(f"Found {len(gdf)} occurrence points")
    
    # Create current habitat map
    current_habitat = OUTPUT_DIR / f"{species_name.replace(' ', '_')}_current.tif"
    create_habitat_raster(gdf, AUSTRALIA_BOUNDS, RESOLUTION, current_habitat)
    
    # Future habitat map would be created using climate projections
    # This is a placeholder - you'd use species distribution modeling
    print(f"NOTE: Future habitat map requires climate projection data")
    print(f"      Use species distribution modeling (e.g., MaxEnt) to create future habitat")

def process_all_species():
    """Process all species files in the species directory."""
    species_files = list(SPECIES_DIR.glob("*.json"))
    
    if not species_files:
        print("No species files found. Run download_data.py first.")
        return
    
    print(f"Found {len(species_files)} species files")
    
    # Organize by group
    groups = get_all_species_by_group()
    print(f"\nSpecies by group:")
    for group, species_list in groups.items():
        print(f"  {group.capitalize()}: {len(species_list)} species")
    
    # Process each species
    processed_count = 0
    for species_file in species_files:
        species_name = species_file.stem.replace('_', ' ')
        group = get_species_group(species_name)
        if group:
            print(f"\n[{group.upper()}] Processing {species_name}...")
        else:
            print(f"\n[UNKNOWN] Processing {species_name}...")
        
        try:
            process_species_file(species_file, species_name)
            processed_count += 1
        except Exception as e:
            print(f"  ✗ Error processing {species_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✓ Successfully processed {processed_count}/{len(species_files)} species")

if __name__ == "__main__":
    print("=" * 60)
    print("Processing Species Distribution Data")
    print("=" * 60)
    
    process_all_species()
    
    print("\n" + "=" * 60)
    print("Species processing complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Create future habitat maps using climate projections")
    print("2. Create resistance surfaces for each species")
    print("3. Run run_circuitscape.py to calculate connectivity")


