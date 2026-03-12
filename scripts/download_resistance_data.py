"""
Build resistance surfaces for Australia using known geography.

Creates per-group resistance at 80x68 and 160x136 grids using:
- Distance from coast (interior = arid)
- Latitude zones (tropical north, temperate south)
- Known terrain features (Great Dividing Range, deserts)
- Group-specific weights (mammals vs birds vs amphibians)

No external data download required - uses the existing GeoJSON land mask.
"""

import json
import numpy as np
from pathlib import Path
from scipy import ndimage

DATA_DIR = Path(__file__).parent.parent / "data"
RESISTANCE_DIR = DATA_DIR / "resistance"
GEOJSON_PATH = Path(__file__).parent.parent / "web" / "data" / "geojson" / "australia.geojson"
RESISTANCE_DIR.mkdir(parents=True, exist_ok=True)

BOUNDS = {'minx': 113.0, 'miny': -44.0, 'maxx': 154.0, 'maxy': -10.0}

GRIDS = {
    'species': (80, 68),
    'aggregated': (160, 136)
}


def point_in_polygon(lon, lat, polygon):
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def create_land_mask(width, height, bounds):
    mask = np.zeros((height, width), dtype=bool)
    if not GEOJSON_PATH.exists():
        mask[:] = True
        return mask

    with open(GEOJSON_PATH) as f:
        geojson = json.load(f)

    polygons = []
    for feat in geojson['features']:
        geom = feat['geometry']
        if geom['type'] == 'Polygon':
            polygons.append(geom['coordinates'][0])
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['coordinates']:
                polygons.append(poly[0])

    x_res = (bounds['maxx'] - bounds['minx']) / width
    y_res = (bounds['maxy'] - bounds['miny']) / height

    for row in range(height):
        lat = bounds['maxy'] - (row + 0.5) * y_res
        for col in range(width):
            lon = bounds['minx'] + (col + 0.5) * x_res
            for poly in polygons:
                if point_in_polygon(lon, lat, poly):
                    mask[row, col] = True
                    break

    return mask


def build_synthetic_terrain(width, height, bounds, land_mask):
    """
    Build synthetic elevation + terrain type arrays based on known Australian geography.

    Returns:
        elevation: (height, width) float32 - synthetic elevation in meters
        aridity: (height, width) float32 - 0=wet, 1=arid
        ruggedness: (height, width) float32 - 0=flat, 1=mountainous
    """
    x_res = (bounds['maxx'] - bounds['minx']) / width
    y_res = (bounds['maxy'] - bounds['miny']) / height

    # Create coordinate grids
    lons = np.array([bounds['minx'] + (c + 0.5) * x_res for c in range(width)])
    lats = np.array([bounds['maxy'] - (r + 0.5) * y_res for r in range(height)])
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # --- Synthetic elevation ---
    elevation = np.zeros((height, width), dtype=np.float32)

    # Great Dividing Range: runs along east coast from ~-38 to ~-15
    # Ridge line roughly at 149-150°E in south, 146-148°E in north
    ridge_lon = 149.0 - (lat_grid + 38) * 0.1  # shifts west as we go north
    dist_from_ridge = np.abs(lon_grid - ridge_lon)
    gdr_mask = (lat_grid > -38) & (lat_grid < -15) & (lon_grid > 140) & (dist_from_ridge < 4)
    gdr_elev = np.exp(-0.5 * (dist_from_ridge / 1.5) ** 2) * 1200
    gdr_elev[~gdr_mask] = 0
    elevation += gdr_elev

    # Australian Alps: higher peaks around -36 to -37, 148-149°E
    alps_dist = np.sqrt((lon_grid - 148.5) ** 2 + (lat_grid + 36.5) ** 2)
    alps_elev = np.exp(-0.5 * (alps_dist / 1.0) ** 2) * 800
    elevation += alps_elev

    # Central highlands / MacDonnell Ranges: ~-24, 134°E
    mac_dist = np.sqrt(((lon_grid - 134) / 2) ** 2 + (lat_grid + 24) ** 2)
    mac_elev = np.exp(-0.5 * (mac_dist / 0.8) ** 2) * 600
    elevation += mac_elev

    # Flinders Ranges: ~-31.5, 138.5°E
    fli_dist = np.sqrt((lon_grid - 138.5) ** 2 + ((lat_grid + 31.5) / 1.5) ** 2)
    fli_elev = np.exp(-0.5 * (fli_dist / 0.7) ** 2) * 500
    elevation += fli_elev

    # General western plateau: broad low elevation
    west_mask = (lon_grid < 135) & land_mask
    elevation[west_mask] += 300

    # Coastal lowlands
    coast_dist = ndimage.distance_transform_edt(land_mask)
    coast_dist_norm = coast_dist / max(coast_dist.max(), 1)
    coastal_mask = (coast_dist_norm < 0.05) & land_mask
    elevation[coastal_mask] *= 0.3

    # Smooth
    elevation = ndimage.gaussian_filter(elevation, sigma=1.5)
    elevation[~land_mask] = 0

    # --- Aridity ---
    # Interior Australia is very arid, coast is wetter, tropical north is wet
    aridity = np.zeros((height, width), dtype=np.float32)

    # Base: distance from coast = more arid
    aridity = np.clip(coast_dist_norm * 2.5, 0, 1)

    # Tropical north (above -20°) is wetter
    tropical = lat_grid > -20
    aridity[tropical] *= 0.4

    # Southeast is wetter (temperate rainfall)
    southeast = (lat_grid < -30) & (lon_grid > 145)
    aridity[southeast] *= 0.3

    # Tasmania is wet
    tasmania = (lat_grid < -40) & (lon_grid > 144) & (lon_grid < 149)
    aridity[tasmania] *= 0.2

    # East coast strip is wetter (orographic rainfall)
    east_coast = (lon_grid > 148) & (lat_grid > -38) & (lat_grid < -15)
    aridity[east_coast] *= 0.5

    # Southwest WA has some rainfall
    sw_wa = (lat_grid < -30) & (lon_grid < 120)
    aridity[sw_wa] *= 0.6

    aridity = np.clip(aridity, 0, 1)
    aridity = ndimage.gaussian_filter(aridity, sigma=2.0)
    aridity = np.clip(aridity, 0, 1)
    aridity[~land_mask] = 0

    # --- Ruggedness (from elevation gradient) ---
    if elevation.max() > 0:
        dy, dx = np.gradient(elevation)
        ruggedness = np.sqrt(dx ** 2 + dy ** 2)
        ruggedness = np.clip(ruggedness / max(ruggedness.max(), 1), 0, 1)
    else:
        ruggedness = np.zeros_like(elevation)
    ruggedness[~land_mask] = 0

    return elevation, aridity, ruggedness


def build_resistance_surfaces(elevation, aridity, ruggedness, land_mask):
    """Build per-group resistance surfaces."""
    results = {}

    # Group-specific resistance formulas
    configs = {
        'mammals': {
            'aridity_weight': 0.4,      # Arid = harder
            'ruggedness_weight': 0.35,   # Mountains = harder
            'elevation_weight': 0.15,    # High = slightly harder
            'base': 0.1,
        },
        'birds': {
            'aridity_weight': 0.15,      # Less affected by aridity
            'ruggedness_weight': 0.05,   # Not affected by terrain
            'elevation_weight': 0.0,
            'base': 0.05,
        },
        'amphibians': {
            'aridity_weight': 0.55,      # Very affected by dry conditions
            'ruggedness_weight': 0.25,   # Affected by terrain
            'elevation_weight': 0.1,
            'base': 0.1,
        },
    }

    elev_norm = elevation / max(elevation.max(), 1)

    for group, cfg in configs.items():
        resist = np.full_like(elevation, cfg['base'])

        resist += cfg['aridity_weight'] * aridity
        resist += cfg['ruggedness_weight'] * ruggedness
        resist += cfg['elevation_weight'] * elev_norm

        # Ocean = max resistance
        resist[~land_mask] = 1.0

        # Normalize land cells to 0-1
        if land_mask.any():
            land_vals = resist[land_mask]
            r_min, r_max = land_vals.min(), land_vals.max()
            if r_max > r_min:
                resist[land_mask] = (resist[land_mask] - r_min) / (r_max - r_min)
            resist[land_mask] = np.clip(resist[land_mask], 0.01, 0.99)

        # Smooth for visual coherence
        resist = ndimage.gaussian_filter(resist, sigma=1.5)
        resist = np.clip(resist, 0, 1)
        resist[~land_mask] = 1.0

        results[group] = resist
        print(f"  {group}: resistance range [{resist[land_mask].min():.3f}, "
              f"{resist[land_mask].max():.3f}], mean={resist[land_mask].mean():.3f}")

    return results


def main():
    print("=" * 60)
    print("Building Resistance Surfaces for Australia")
    print("=" * 60)

    for label, (w, h) in GRIDS.items():
        print(f"\n--- Grid: {label} ({w}x{h}) ---")

        print("  Building land mask...")
        land_mask = create_land_mask(w, h, BOUNDS)
        land_pct = 100 * land_mask.sum() / land_mask.size
        print(f"  Land: {land_mask.sum()}/{land_mask.size} cells ({land_pct:.1f}%)")

        print("  Building synthetic terrain...")
        elevation, aridity, ruggedness = build_synthetic_terrain(w, h, BOUNDS, land_mask)
        print(f"  Elevation: [{elevation[land_mask].min():.0f}, {elevation[land_mask].max():.0f}]m")
        print(f"  Aridity: [{aridity[land_mask].min():.2f}, {aridity[land_mask].max():.2f}]")
        print(f"  Ruggedness: [{ruggedness[land_mask].min():.3f}, {ruggedness[land_mask].max():.3f}]")

        print("  Building resistance surfaces...")
        resistance = build_resistance_surfaces(elevation, aridity, ruggedness, land_mask)

        for group, resist in resistance.items():
            filename = f"{group}_resistance_{w}x{h}.npy"
            np.save(RESISTANCE_DIR / filename, resist.astype(np.float32))
            print(f"  Saved {filename}")

    print(f"\n{'='*60}")
    print("Resistance surfaces built successfully!")
    print("=" * 60)
    print(f"\nFiles in {RESISTANCE_DIR}:")
    for f in sorted(RESISTANCE_DIR.glob("*.npy")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
