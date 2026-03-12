"""
Download Australia's GeoJSON boundary from Overpass API (OpenStreetMap).
This provides much more accurate coastline data than the simplified version.

Alternative: Uses Overpass Turbo's GeoJSON export endpoint for easier access.
"""

import json
import urllib.request
import urllib.parse
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
GEOJSON_DIR = DATA_DIR / "geojson"
WEB_GEOJSON_DIR = DATA_DIR.parent / "web" / "data" / "geojson"
GEOJSON_DIR.mkdir(exist_ok=True, parents=True)
WEB_GEOJSON_DIR.mkdir(exist_ok=True, parents=True)

# Overpass API endpoint
OVERPASS_API = "https://overpass-api.de/api/interpreter"

def query_overpass_api(query):
    """
    Query the Overpass API and return the result.
    
    Parameters:
    -----------
    query : str
        Overpass QL query string
    
    Returns:
    --------
    dict : JSON response from Overpass API
    """
    print("Querying Overpass API...")
    print(f"Query: {query[:100]}...")
    
    # Encode query
    data = urllib.parse.urlencode({'data': query}).encode('utf-8')
    
    try:
        # Make request
        req = urllib.request.Request(OVERPASS_API, data=data)
        req.add_header('User-Agent', 'Australia-Migrations-Map/1.0')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        if e.code == 429:
            print("Rate limited. Please wait a moment and try again.")
        raise
    except Exception as e:
        print(f"Error querying Overpass API: {e}")
        raise

def convert_overpass_to_geojson(overpass_data):
    """
    Convert Overpass API response to GeoJSON format.
    Handles relations with geometry data.
    
    Parameters:
    -----------
    overpass_data : dict
        JSON response from Overpass API
    
    Returns:
    --------
    dict : GeoJSON FeatureCollection
    """
    features = []
    
    # Process relations (administrative boundaries)
    if 'elements' in overpass_data:
        for element in overpass_data['elements']:
            if element.get('type') == 'relation':
                # Check if relation has geometry (from 'out geom')
                if 'geometry' in element and element['geometry']:
                    # Extract coordinates from geometry
                    coords = []
                    for geom_point in element['geometry']:
                        if isinstance(geom_point, dict) and 'lat' in geom_point and 'lon' in geom_point:
                            coords.append([geom_point['lon'], geom_point['lat']])
                    
                    if len(coords) >= 3:
                        # Close the polygon if not already closed
                        if coords[0] != coords[-1]:
                            coords.append(coords[0])
                        
                        feature = {
                            "type": "Feature",
                            "properties": {
                                "name": element.get('tags', {}).get('name', 'Australia'),
                                "admin_level": element.get('tags', {}).get('admin_level', '2'),
                                "osm_id": element.get('id')
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [coords]
                            }
                        }
                        features.append(feature)
                        print(f"  Created feature with {len(coords)} points")
    
    # Create GeoJSON FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:EPSG::4326"
            }
        },
        "features": features
    }
    
    return geojson

def download_from_overpass_turbo():
    """
    Download Australia GeoJSON using Overpass Turbo's GeoJSON export.
    This is more reliable as Overpass Turbo handles the conversion.
    """
    # Overpass Turbo GeoJSON export URL
    # Using a direct query that Overpass Turbo can export
    query = """[out:json][timeout:60];
relation["admin_level"="2"]["name"="Australia"];
out geom;"""
    
    # Overpass Turbo API endpoint for GeoJSON export
    # Note: We'll use the regular Overpass API and convert manually
    # Or use a public GeoJSON source
    
    # Alternative: Use a reliable public GeoJSON source
    print("Trying alternative: Downloading from public GeoJSON source...")
    return download_from_public_source()

def download_from_public_source():
    """
    Download Australia GeoJSON from a reliable public source.
    """
    # Try multiple sources
    sources = [
        {
            'name': 'geojson-maps.kyd.au',
            'url': 'https://raw.githubusercontent.com/kydau/geojson-maps/master/countries/australia.geojson'
        },
        {
            'name': 'Natural Earth (via GitHub)',
            'url': 'https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson'
        }
    ]
    
    for source in sources:
        try:
            print(f"Trying {source['name']}...")
            req = urllib.request.Request(source['url'])
            req.add_header('User-Agent', 'Australia-Migrations-Map/1.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                geojson = json.loads(response.read().decode('utf-8'))
                
                # If it's a world map, extract Australia
                if geojson.get('type') == 'FeatureCollection':
                    # Check if it's a world map or just Australia
                    features = geojson.get('features', [])
                    if len(features) > 1:
                        # World map - find Australia
                        australia_features = [
                            f for f in features 
                            if f.get('properties', {}).get('name', '').lower() in ['australia', 'australia (mainland)']
                        ]
                        if australia_features:
                            geojson['features'] = australia_features
                            print(f"  Found Australia in world map")
                    
                    if geojson['features']:
                        # Ensure CRS is set
                        if 'crs' not in geojson:
                            geojson['crs'] = {
                                "type": "name",
                                "properties": {
                                    "name": "urn:ogc:def:crs:EPSG::4326"
                                }
                            }
                        print(f"  ✓ Successfully downloaded from {source['name']}")
                        return geojson
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue
    
    return None

def download_australia_from_overpass():
    """
    Download Australia's boundary from Overpass API.
    Uses a query to get the administrative boundary relation.
    """
    # First try public source (more reliable)
    geojson = download_from_public_source()
    if geojson:
        return geojson
    
    # Fallback to Overpass API
    # Overpass QL query for Australia
    # Query for Australia relation at admin_level 2 (country level)
    query = """[out:json][timeout:60];
(
  relation["admin_level"="2"]["name"="Australia"];
  relation["admin_level"="2"]["ISO3166-1"="AU"];
);
out geom;"""
    
    try:
        # Query Overpass API
        overpass_data = query_overpass_api(query)
        
        if not overpass_data or 'elements' not in overpass_data:
            print("No data returned from Overpass API")
            return None
        
        print(f"Received {len(overpass_data['elements'])} elements from Overpass API")
        
        # Convert to GeoJSON
        geojson = convert_overpass_to_geojson(overpass_data)
        
        if not geojson['features']:
            print("Warning: No features in GeoJSON.")
            return None
        
        return geojson
        
    except Exception as e:
        print(f"Error downloading from Overpass API: {e}")
        return None

def download_australia_bbox():
    """
    Alternative: Query Australia using bounding box.
    This is more reliable but may return more data.
    """
    # Australia bounding box
    # Query for all administrative boundaries in Australia's bounding box
    query = """[out:json][timeout:120];
(
  relation["admin_level"="2"](113.0,-44.0,154.0,-10.0);
);
out geom;"""
    
    try:
        overpass_data = query_overpass_api(query)
        
        if not overpass_data or 'elements' not in overpass_data:
            print("No data returned from bounding box query")
            return None
        
        print(f"Received {len(overpass_data['elements'])} elements from bounding box query")
        
        # Find Australia relation
        australia_relation = None
        for element in overpass_data['elements']:
            if element.get('type') == 'relation':
                tags = element.get('tags', {})
                name = tags.get('name', '').lower()
                if 'australia' in name or tags.get('ISO3166-1') == 'AU':
                    australia_relation = element
                    break
        
        if not australia_relation:
            print("Could not find Australia relation in results")
            return None
        
        # Convert to GeoJSON
        geojson = convert_overpass_to_geojson({'elements': [australia_relation]})
        return geojson
        
    except Exception as e:
        print(f"Error with bounding box query: {e}")
        return None

def save_geojson(geojson, output_file):
    """Save GeoJSON to file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    # Count total points
    total_points = 0
    for feature in geojson['features']:
        if feature['geometry']['type'] == 'Polygon':
            for ring in feature['geometry']['coordinates']:
                total_points += len(ring)
        elif feature['geometry']['type'] == 'MultiPolygon':
            for polygon in feature['geometry']['coordinates']:
                for ring in polygon:
                    total_points += len(ring)
    
    print(f"✓ Saved GeoJSON: {output_file}")
    print(f"  Features: {len(geojson['features'])}")
    print(f"  Total points: {total_points}")

def main():
    """Main function to download Australia GeoJSON from Overpass API."""
    print("=" * 60)
    print("Downloading Australia GeoJSON from Overpass API")
    print("=" * 60)
    print()
    
    # Download from Overpass API
    geojson = download_australia_from_overpass()
    
    if not geojson or not geojson['features']:
        print("Failed to download from Overpass API")
        print("You can manually download from:")
        print("  1. Go to https://overpass-turbo.eu/")
        print("  2. Run query: relation[\"admin_level\"=\"2\"][\"name\"=\"Australia\"]; out geom;")
        print("  3. Export as GeoJSON")
        return None
    
    # Save to both locations
    output_file = GEOJSON_DIR / "australia.geojson"
    web_output_file = WEB_GEOJSON_DIR / "australia.geojson"
    
    save_geojson(geojson, output_file)
    save_geojson(geojson, web_output_file)
    
    print()
    print("=" * 60)
    print("Download complete!")
    print("=" * 60)
    print()
    print("The GeoJSON will be automatically displayed on the map.")
    print("Refresh your browser to see the updated boundary.")
    
    return output_file

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
