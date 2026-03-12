import json

with open('web/data/geojson/australia.geojson', 'r', encoding='utf-8') as f:
    geojson = json.load(f)

print(f"Type: {geojson.get('type')}")
print(f"Features: {len(geojson.get('features', []))}")

total_points = 0
for i, feature in enumerate(geojson.get('features', [])):
    geom = feature.get('geometry', {})
    geom_type = geom.get('type', 'unknown')
    coords = geom.get('coordinates', [])
    
    if geom_type == 'Polygon' and coords:
        points = len(coords[0]) if coords else 0
        total_points += points
        print(f"Feature {i+1}: {geom_type} with {points} points")
    elif geom_type == 'MultiPolygon' and coords:
        for j, polygon in enumerate(coords):
            if polygon and len(polygon) > 0:
                points = len(polygon[0]) if polygon[0] else 0
                total_points += points
                print(f"Feature {i+1}, Polygon {j+1}: {points} points")
        print(f"Feature {i+1}: {geom_type} with {len(coords)} polygons")

print(f"\nTotal points: {total_points:,}")
print(f"File size: ~2.7MB (much more detailed than the 21-point simplified version!)")

