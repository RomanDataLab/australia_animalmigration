"""
Download Australia's GeoJSON boundary data for constraining particle flows.
"""

import json
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
GEOJSON_DIR = DATA_DIR / "geojson"
GEOJSON_DIR.mkdir(exist_ok=True, parents=True)

# URL for Australia GeoJSON (simplified version from Natural Earth)
# Using a public GeoJSON source
AUSTRALIA_GEOJSON_URL = "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson"

# Alternative: Use a simplified Australia polygon
# We'll create a simplified version based on Australia's approximate coastline
def create_simplified_australia_geojson():
    """
    Create a simplified GeoJSON polygon for Australia's mainland and Tasmania.
    This is a simplified version - for production, use a detailed GeoJSON from Natural Earth or similar.
    """
    # Simplified polygon coordinates for Australia (mainland + Tasmania)
    # These are approximate coordinates that define Australia's coastline
    # For better accuracy, download from: https://geojson-maps.kyd.au/
    
    australia_geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:EPSG::4326"
            }
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Australia"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        # Mainland Australia - simplified polygon (clockwise)
                        # More accurate coordinates based on Australia's coastline
                        [113.0, -13.5],   # Northwest (Shark Bay area)
                        [115.0, -20.0],   # West (Carnarvon)
                        [118.0, -24.0],   # West (Exmouth)
                        [121.0, -18.0],   # Northwest (Broome)
                        [125.0, -15.0],   # North (Darwin area)
                        [129.0, -12.0],   # North (Arnhem Land)
                        [135.0, -12.0],   # North (Gulf of Carpentaria)
                        [142.0, -10.7],   # Northeast (Cape York)
                        [145.0, -16.0],   # East (Cairns)
                        [150.0, -20.0],   # East (Townsville)
                        [152.0, -27.0],   # East (Brisbane)
                        [153.0, -28.0],   # Southeast (Gold Coast)
                        [151.0, -33.0],   # East (Sydney)
                        [150.0, -37.0],   # Southeast (Wollongong)
                        [147.0, -38.0],   # South (Lakes Entrance)
                        [141.0, -38.5],   # Southwest (Portland)
                        [138.0, -35.0],   # South (Adelaide)
                        [131.0, -32.0],   # West (Perth)
                        [115.0, -34.0],   # Southwest (Bunbury)
                        [113.0, -26.0],   # West (Geraldton)
                        [113.0, -13.5]    # Close polygon
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Tasmania"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        # Tasmania - simplified polygon (clockwise)
                        [144.0, -40.5],   # Northwest
                        [148.0, -40.5],   # Northeast
                        [148.0, -43.5],   # Southeast
                        [144.0, -43.5],   # Southwest
                        [144.0, -40.5]    # Close polygon
                    ]]
                }
            }
        ]
    }
    
    return australia_geojson

def download_australia_geojson():
    """
    Download Australia GeoJSON from a public source.
    Falls back to simplified version if download fails.
    """
    output_file = GEOJSON_DIR / "australia.geojson"
    
    # Try to download from a reliable source
    # For now, we'll use the simplified version
    # In production, you could download from:
    # - https://geojson-maps.kyd.au/ (select Australia)
    # - Natural Earth data
    # - OpenStreetMap boundaries
    
    print("Creating simplified Australia GeoJSON...")
    geojson = create_simplified_australia_geojson()
    
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"✓ Created Australia GeoJSON: {output_file}")
    print(f"  Features: {len(geojson['features'])}")
    print(f"  Note: This is a simplified version. For better accuracy,")
    print(f"        download detailed GeoJSON from https://geojson-maps.kyd.au/")
    
    return output_file

if __name__ == "__main__":
    download_australia_geojson()

