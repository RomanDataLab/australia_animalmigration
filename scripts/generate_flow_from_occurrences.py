"""
Generate flow vectors directly from species occurrence data.

Produces per-species flow data (30 files) plus aggregated group files.
Uses GeoJSON land mask to ensure flows stay within Australia's coastline.
"""

import json
import numpy as np
from pathlib import Path
from scipy import ndimage
import sys

sys.path.insert(0, str(Path(__file__).parent))
from species_classification import get_species_group, get_all_species_by_group

DATA_DIR = Path(__file__).parent.parent / "data"
SPECIES_DIR = DATA_DIR / "species"
OUTPUT_DIR = DATA_DIR / "output"
WEB_OUTPUT_DIR = Path(__file__).parent.parent / "web" / "data" / "output"
GEOJSON_PATH = Path(__file__).parent.parent / "web" / "data" / "geojson" / "australia.geojson"
RESISTANCE_DIR = DATA_DIR / "resistance"

BOUNDS = {
    'minx': 113.0, 'miny': -44.0,
    'maxx': 154.0, 'maxy': -10.0
}

# Per-species: 80x68 for small files; aggregated: 160x136 for detail
SPECIES_WIDTH = 80
SPECIES_HEIGHT = 68
AGG_WIDTH = 160
AGG_HEIGHT = 136

# Climate shift per group (poleward = south in southern hemisphere)
CLIMATE_SHIFT = {
    'mammals':    {'u':  0.03, 'v': -0.12},
    'birds':      {'u': -0.04, 'v': -0.08},
    'amphibians': {'u':  0.01, 'v': -0.15},
}

# Common names and Wikipedia slugs for each species
SPECIES_INFO = {
    # Mammals
    'Macropus giganteus':       {'common': 'Eastern Grey Kangaroo',     'wiki': 'Eastern_grey_kangaroo'},
    'Phascolarctos cinereus':   {'common': 'Koala',                     'wiki': 'Koala'},
    'Tachyglossus aculeatus':   {'common': 'Short-beaked Echidna',      'wiki': 'Short-beaked_echidna'},
    'Macropus rufus':           {'common': 'Red Kangaroo',              'wiki': 'Red_kangaroo'},
    'Vombatus ursinus':         {'common': 'Common Wombat',             'wiki': 'Common_wombat'},
    'Trichosurus vulpecula':    {'common': 'Common Brushtail Possum',   'wiki': 'Common_brushtail_possum'},
    'Isoodon obesulus':         {'common': 'Southern Brown Bandicoot',  'wiki': 'Southern_brown_bandicoot'},
    'Perameles nasuta':         {'common': 'Long-nosed Bandicoot',      'wiki': 'Long-nosed_bandicoot'},
    'Wallabia bicolor':         {'common': 'Swamp Wallaby',             'wiki': 'Swamp_wallaby'},
    'Pseudocheirus peregrinus': {'common': 'Common Ringtail Possum',    'wiki': 'Common_ringtail_possum'},
    # Birds
    'Dromaius novaehollandiae': {'common': 'Emu',                       'wiki': 'Emu'},
    'Cacatua galerita':         {'common': 'Sulphur-crested Cockatoo',  'wiki': 'Sulphur-crested_cockatoo'},
    'Gymnorhina tibicen':       {'common': 'Australian Magpie',         'wiki': 'Australian_magpie'},
    'Platycercus eximius':      {'common': 'Eastern Rosella',           'wiki': 'Eastern_rosella'},
    'Corvus coronoides':        {'common': 'Australian Raven',          'wiki': 'Australian_raven'},
    'Acanthiza pusilla':        {'common': 'Brown Thornbill',           'wiki': 'Brown_thornbill'},
    'Meliphaga lewinii':        {'common': "Lewin's Honeyeater",       'wiki': "Lewin%27s_honeyeater"},
    'Pardalotus punctatus':     {'common': 'Spotted Pardalote',         'wiki': 'Spotted_pardalote'},
    'Rhipidura leucophrys':     {'common': 'Willie Wagtail',            'wiki': 'Willie_wagtail'},
    'Eolophus roseicapilla':    {'common': 'Galah',                     'wiki': 'Galah'},
    # Amphibians
    'Litoria caerulea':             {'common': 'Green Tree Frog',           'wiki': 'Australian_green_tree_frog'},
    'Limnodynastes dumerilii':      {'common': 'Eastern Banjo Frog',       'wiki': 'Eastern_banjo_frog'},
    'Crinia signifera':             {'common': 'Common Eastern Froglet',    'wiki': 'Common_eastern_froglet'},
    'Litoria peronii':              {'common': "Peron's Tree Frog",         'wiki': "Peron%27s_tree_frog"},
    'Limnodynastes tasmaniensis':   {'common': 'Spotted Grass Frog',       'wiki': 'Spotted_grass_frog'},
    'Litoria ewingii':              {'common': 'Brown Tree Frog',           'wiki': 'Brown_tree_frog'},
    'Uperoleia laevigata':          {'common': 'Smooth Toadlet',            'wiki': 'Smooth_toadlet'},
    'Litoria raniformis':           {'common': 'Growling Grass Frog',       'wiki': 'Growling_grass_frog'},
    'Pseudophryne bibronii':        {'common': "Bibron's Toadlet",          'wiki': "Bibron%27s_toadlet"},
    'Litoria verreauxii':           {'common': "Verreaux's Tree Frog",      'wiki': 'Whistling_tree_frog'},
}


def load_species_json(filepath):
    text = filepath.read_text(encoding='utf-8')
    text = text.replace(': NaN', ': null').replace(':NaN', ':null')
    data = json.loads(text)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'records' in data:
        return data['records']
    return [data]


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


def occurrences_to_density(records, width, height, bounds, sigma=4.0):
    grid = np.zeros((height, width), dtype=np.float64)
    x_res = (bounds['maxx'] - bounds['minx']) / width
    y_res = (bounds['maxy'] - bounds['miny']) / height

    count = 0
    for rec in records:
        lon = rec.get('decimalLongitude')
        lat = rec.get('decimalLatitude')
        if lon is None or lat is None:
            continue
        if not (bounds['minx'] <= lon <= bounds['maxx'] and
                bounds['miny'] <= lat <= bounds['maxy']):
            continue
        col = int((lon - bounds['minx']) / x_res)
        row = int((bounds['maxy'] - lat) / y_res)
        col = max(0, min(col, width - 1))
        row = max(0, min(row, height - 1))
        grid[row, col] += 1.0
        count += 1

    if count == 0:
        return grid
    grid = ndimage.gaussian_filter(grid, sigma=sigma)
    mx = grid.max()
    if mx > 0:
        grid /= mx
    return grid


def load_resistance(group_name, width, height):
    """Load resistance surface for a group at the given grid size."""
    filename = f"{group_name}_resistance_{width}x{height}.npy"
    path = RESISTANCE_DIR / filename
    if path.exists():
        return np.load(path)
    return None


def density_to_flow(density, group_name, land_mask, resistance=None):
    grad_y, grad_x = np.gradient(density)
    u_disp = grad_x * 0.2
    v_disp = -grad_y * 0.2

    shift = CLIMATE_SHIFT.get(group_name, {'u': 0, 'v': -0.12})
    hw = np.clip(density * 5.0, 0, 1)
    hw_broad = ndimage.gaussian_filter(hw, sigma=6.0)
    hw_broad = np.clip(hw_broad * 3.0, 0, 1)

    np.random.seed(abs(hash(group_name)) % (2**31))
    u = u_disp + shift['u'] * hw_broad + np.random.normal(0, 0.02, density.shape) * hw_broad
    v = v_disp + shift['v'] * hw_broad + np.random.normal(0, 0.02, density.shape) * hw_broad

    # Apply resistance-aware steering
    if resistance is not None:
        # Conductance = inverse of resistance (low resistance = easy to traverse)
        conductance = 1.0 / np.clip(resistance, 0.05, 1.0)
        # Gradient of conductance: flows are pulled toward higher conductance (lower resistance)
        cond_grad_y, cond_grad_x = np.gradient(conductance)
        # Resistance steering weight (stronger for mammals/amphibians, weaker for birds)
        resist_weight = {'mammals': 0.35, 'birds': 0.08, 'amphibians': 0.45}.get(group_name, 0.2)
        u += resist_weight * cond_grad_x * hw_broad
        v += -resist_weight * cond_grad_y * hw_broad
        # Scale magnitude by conductance (flows weaken in high-resistance areas)
        cond_norm = np.clip(conductance / max(conductance.max(), 1), 0.15, 1.0)
    else:
        cond_norm = None

    u = ndimage.gaussian_filter(u, sigma=2.0)
    v = ndimage.gaussian_filter(v, sigma=2.0)

    magnitude = np.sqrt(u**2 + v**2)
    nonzero = magnitude > 1e-6
    u[nonzero] /= magnitude[nonzero]
    v[nonzero] /= magnitude[nonzero]

    magnitude = hw_broad * 0.7 + 0.3 * np.clip(density * 2, 0, 1)

    # Apply conductance scaling to magnitude
    if cond_norm is not None:
        magnitude *= cond_norm

    u[~land_mask] = 0
    v[~land_mask] = 0
    magnitude[~land_mask] = 0
    weak = magnitude < 0.02
    u[weak] = 0
    v[weak] = 0
    magnitude[weak] = 0

    return u, v, magnitude


def make_flow_json(u, v, magnitude, width, height, bounds, extra_fields=None):
    x_res = (bounds['maxx'] - bounds['minx']) / width
    y_res = (bounds['maxy'] - bounds['miny']) / height
    data = {
        'bounds': bounds,
        'resolution': (x_res + y_res) / 2,
        'x_resolution': x_res,
        'y_resolution': y_res,
        'u': u.tolist(),
        'v': v.tolist(),
        'magnitude': magnitude.tolist()
    }
    if extra_fields:
        data.update(extra_fields)
    return data


def save_flow(flow_data, filename):
    for out_dir in [OUTPUT_DIR, WEB_OUTPUT_DIR]:
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / filename, 'w') as f:
            json.dump(flow_data, f)


def main():
    print("=" * 60)
    print("Generating Per-Species + Aggregated Flow Vectors")
    print("=" * 60)

    # Create land masks at both resolutions
    print("\nCreating land masks...")
    land_sp = create_land_mask(SPECIES_WIDTH, SPECIES_HEIGHT, BOUNDS)
    print(f"  Species grid ({SPECIES_WIDTH}x{SPECIES_HEIGHT}): "
          f"{land_sp.sum()}/{land_sp.size} land cells")
    land_agg = create_land_mask(AGG_WIDTH, AGG_HEIGHT, BOUNDS)
    print(f"  Aggregated grid ({AGG_WIDTH}x{AGG_HEIGHT}): "
          f"{land_agg.sum()}/{land_agg.size} land cells")

    # Load resistance surfaces
    print("\nLoading resistance surfaces...")
    resistance_sp = {}
    resistance_agg = {}
    for g in ['mammals', 'birds', 'amphibians']:
        r_sp = load_resistance(g, SPECIES_WIDTH, SPECIES_HEIGHT)
        r_agg = load_resistance(g, AGG_WIDTH, AGG_HEIGHT)
        if r_sp is not None:
            resistance_sp[g] = r_sp
            print(f"  {g} species: loaded ({r_sp.shape})")
        if r_agg is not None:
            resistance_agg[g] = r_agg
            print(f"  {g} aggregated: loaded ({r_agg.shape})")
    if not resistance_sp:
        print("  No resistance surfaces found - using basic flow generation")

    groups = get_all_species_by_group()

    # Build species manifest for the web app
    manifest = {'groups': {}}

    for group_name, species_list in groups.items():
        print(f"\n{'='*50}")
        print(f"{group_name.upper()} ({len(species_list)} species)")
        print(f"{'='*50}")

        agg_density = np.zeros((AGG_HEIGHT, AGG_WIDTH), dtype=np.float64)
        group_species = []
        sp_count = 0

        for species_name in species_list:
            safe = species_name.replace(' ', '_')
            sp_file = SPECIES_DIR / f"{safe}.json"
            if not sp_file.exists():
                print(f"  ! Missing: {sp_file.name}")
                continue

            records = load_species_json(sp_file)
            n_pts = sum(1 for r in records
                        if r.get('decimalLongitude') is not None
                        and r.get('decimalLatitude') is not None)

            # Per-species flow at lower resolution
            density_sp = occurrences_to_density(
                records, SPECIES_WIDTH, SPECIES_HEIGHT, BOUNDS, sigma=4.0)
            u, v, mag = density_to_flow(density_sp, group_name, land_sp,
                                        resistance_sp.get(group_name))
            nz = int(np.sum(mag > 0.02))

            flow = make_flow_json(u, v, mag, SPECIES_WIDTH, SPECIES_HEIGHT, BOUNDS,
                                  {'species': species_name, 'group': group_name})
            save_flow(flow, f"{safe}_flow.json")

            # Info for manifest
            info = SPECIES_INFO.get(species_name, {})
            group_species.append({
                'scientific': species_name,
                'common': info.get('common', species_name),
                'wiki': info.get('wiki', safe),
                'file': f"{safe}_flow.json",
                'points': n_pts
            })

            print(f"  + {species_name} ({info.get('common','')}): "
                  f"{n_pts} pts, {nz} flow cells")

            # Accumulate for aggregated
            density_agg = occurrences_to_density(
                records, AGG_WIDTH, AGG_HEIGHT, BOUNDS, sigma=5.0)
            agg_density += density_agg
            sp_count += 1

        # Aggregated group flow
        if sp_count > 0:
            agg_density /= sp_count
            mx = agg_density.max()
            if mx > 0:
                agg_density /= mx
            u, v, mag = density_to_flow(agg_density, group_name, land_agg,
                                        resistance_agg.get(group_name))
            flow = make_flow_json(u, v, mag, AGG_WIDTH, AGG_HEIGHT, BOUNDS,
                                  {'group': group_name, 'species_count': sp_count})
            save_flow(flow, f"{group_name}_aggregated_flow.json")
            nz = int(np.sum(mag > 0.02))
            print(f"\n  -> Aggregated: {nz}/{mag.size} flow cells ({100*nz/mag.size:.1f}%)")

        manifest['groups'][group_name] = group_species

    # Save manifest
    for out_dir in [OUTPUT_DIR, WEB_OUTPUT_DIR]:
        with open(out_dir / 'species_manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
    print(f"\nSaved species_manifest.json")

    # Sample flow
    if (WEB_OUTPUT_DIR / 'mammals_aggregated_flow.json').exists():
        import shutil
        shutil.copy(WEB_OUTPUT_DIR / 'mammals_aggregated_flow.json',
                     WEB_OUTPUT_DIR / 'sample_flow.json')
        shutil.copy(OUTPUT_DIR / 'mammals_aggregated_flow.json',
                     OUTPUT_DIR / 'sample_flow.json')

    total_sp = sum(len(v) for v in manifest['groups'].values())
    print(f"\n{'='*60}")
    print(f"Done! {total_sp} species flow files + 3 aggregated + manifest")
    print("=" * 60)


if __name__ == "__main__":
    main()
