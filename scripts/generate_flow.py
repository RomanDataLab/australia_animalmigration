"""
Generate flow vectors from CircuitScape connectivity results.

Converts connectivity maps into directional flow vectors for visualization.
"""

import numpy as np
import rasterio
from pathlib import Path
import json
from scipy import ndimage
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from species_classification import get_species_group, get_all_species_by_group

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "output"

def calculate_flow_vectors(connectivity_raster, current_habitat, future_habitat):
    """
    Calculate flow vectors from connectivity and habitat data.
    
    Parameters:
    -----------
    connectivity_raster : numpy array
        Connectivity current flow values
    current_habitat : numpy array
        Current habitat suitability
    future_habitat : numpy array
        Future habitat suitability
    
    Returns:
    --------
    u : numpy array
        East-west component of flow vectors
    v : numpy array
        North-south component of flow vectors
    magnitude : numpy array
        Magnitude of flow vectors
    """
    # Calculate gradient of connectivity to get flow direction
    grad_y, grad_x = np.gradient(connectivity_raster)
    
    # Normalize to get unit vectors
    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    magnitude[magnitude == 0] = 1  # Avoid division by zero
    
    u = grad_x / magnitude  # East-west component
    v = -grad_y / magnitude  # North-south component (negative because y increases downward)
    
    # Scale by connectivity magnitude
    magnitude = connectivity_raster
    
    return u, v, magnitude

def process_connectivity_file(connectivity_file, species_name):
    """
    Process a CircuitScape connectivity file and generate flow vectors.
    
    Parameters:
    -----------
    connectivity_file : Path
        Path to connectivity raster file
    species_name : str
        Species name
    """
    print(f"\nProcessing {species_name}...")
    
    # Load connectivity raster
    with rasterio.open(connectivity_file) as src:
        connectivity = src.read(1)
        transform = src.transform
        crs = src.crs
        bounds = src.bounds
    
    # Load current and future habitat (if available)
    species_safe = species_name.replace(' ', '_')
    current_habitat_file = OUTPUT_DIR / f"{species_safe}_current.tif"
    future_habitat_file = OUTPUT_DIR / f"{species_safe}_future.tif"
    
    current_habitat = None
    future_habitat = None
    
    if current_habitat_file.exists():
        with rasterio.open(current_habitat_file) as src:
            current_habitat = src.read(1)
    
    if future_habitat_file.exists():
        with rasterio.open(future_habitat_file) as src:
            future_habitat = src.read(1)
    
    # Calculate flow vectors
    if current_habitat is not None and future_habitat is not None:
        u, v, magnitude = calculate_flow_vectors(
            connectivity, current_habitat, future_habitat
        )
    else:
        # Use connectivity gradient alone
        grad_y, grad_x = np.gradient(connectivity)
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        magnitude[magnitude == 0] = 1
        u = grad_x / magnitude
        v = -grad_y / magnitude
        magnitude = connectivity
    
    # Save flow vectors as JSON for web visualization
    # Downsample for web performance (e.g., every 5th pixel)
    downsample = 5
    u_downsampled = u[::downsample, ::downsample]
    v_downsampled = v[::downsample, ::downsample]
    magnitude_downsampled = magnitude[::downsample, ::downsample]
    
    # Calculate separate resolutions for x (longitude) and y (latitude)
    # Transform[0] is pixel width (x resolution), transform[4] is pixel height (y resolution, usually negative)
    x_resolution = downsample * abs(transform[0])  # Longitude resolution
    y_resolution = downsample * abs(transform[4])  # Latitude resolution (use abs since it's usually negative)
    resolution = (x_resolution + y_resolution) / 2  # Average for backward compatibility
    
    # Create GeoJSON-like structure
    flow_data = {
        'species': species_name,
        'bounds': {
            'minx': bounds.left,
            'miny': bounds.bottom,
            'maxx': bounds.right,
            'maxy': bounds.top
        },
        'resolution': resolution,  # Average resolution for backward compatibility
        'x_resolution': x_resolution,  # Longitude resolution (degrees per cell)
        'y_resolution': y_resolution,  # Latitude resolution (degrees per cell)
        'u': u_downsampled.tolist(),
        'v': v_downsampled.tolist(),
        'magnitude': magnitude_downsampled.tolist()
    }
    
    output_file = OUTPUT_DIR / f"{species_safe}_flow.json"
    with open(output_file, 'w') as f:
        json.dump(flow_data, f)
    
    print(f"Saved flow vectors: {output_file}")
    print(f"  X resolution (lon): {x_resolution:.4f} degrees/cell")
    print(f"  Y resolution (lat): {y_resolution:.4f} degrees/cell")
    print(f"  Average resolution: {resolution:.4f} degrees")
    print(f"  Grid size: {len(u_downsampled[0])} x {len(u_downsampled)}")
    
    return output_file

def aggregate_flows(species_groups=None):
    """
    Aggregate flow vectors across multiple species by group.
    
    Parameters:
    -----------
    species_groups : dict, optional
        Dictionary mapping group names to lists of species names
        If None, will auto-detect from flow files
    """
    # Find all flow files
    flow_files = list(OUTPUT_DIR.glob("*_flow.json"))
    
    # Exclude already aggregated files
    flow_files = [f for f in flow_files if not f.name.endswith('_aggregated_flow.json')]
    
    if not flow_files:
        print("No flow files found. Run this script after run_circuitscape.py")
        return
    
    print(f"\nFound {len(flow_files)} flow files")
    print("Aggregating flows by group...")
    
    # Organize flow files by group
    if species_groups is None:
        species_groups = get_all_species_by_group()
    
    group_flow_files = {
        'mammals': [],
        'birds': [],
        'amphibians': []
    }
    
    # Classify each flow file
    for flow_file in flow_files:
        # Extract species name from filename
        species_name = flow_file.stem.replace('_flow', '').replace('_', ' ')
        group = get_species_group(species_name)
        
        if group and group in group_flow_files:
            group_flow_files[group].append(flow_file)
        else:
            print(f"  ⚠ Could not classify {species_name}, skipping...")
    
    # Aggregate flows for each group
    for group_name, files in group_flow_files.items():
        if not files:
            print(f"\n  No flow files found for {group_name}")
            continue
        
        print(f"\n  Aggregating {len(files)} species for {group_name}...")
        
        # Load all flow data for this group
        group_flows = []
        reference_bounds = None
        reference_resolution = None
        
        for flow_file in files:
            try:
                with open(flow_file, 'r') as f:
                    flow_data = json.load(f)
                
                if reference_bounds is None:
                    reference_bounds = flow_data['bounds']
                    reference_resolution = flow_data['resolution']
                
                group_flows.append(flow_data)
            except Exception as e:
                print(f"    ✗ Error loading {flow_file.name}: {e}")
        
        if not group_flows:
            print(f"    ⚠ No valid flow data for {group_name}")
            continue
        
        # Aggregate flow vectors (average them)
        # Note: This assumes all flows have the same grid structure
        # In practice, you'd need to resample to a common grid
        try:
            # Get dimensions from first flow
            first_flow = group_flows[0]
            height = len(first_flow['u'])
            width = len(first_flow['u'][0]) if height > 0 else 0
            
            # Initialize aggregated arrays
            u_agg = np.zeros((height, width))
            v_agg = np.zeros((height, width))
            magnitude_agg = np.zeros((height, width))
            count = 0
            
            for flow_data in group_flows:
                try:
                    u = np.array(flow_data['u'])
                    v = np.array(flow_data['v'])
                    magnitude = np.array(flow_data['magnitude'])
                    
                    # Check dimensions match
                    if u.shape == (height, width):
                        u_agg += u
                        v_agg += v
                        magnitude_agg += magnitude
                        count += 1
                except Exception as e:
                    print(f"    ⚠ Error processing flow data: {e}")
                    continue
            
            if count > 0:
                # Average the flows
                u_agg /= count
                v_agg /= count
                magnitude_agg /= count
                
                # Create aggregated flow data
                aggregated_data = {
                    'group': group_name,
                    'species_count': count,
                    'bounds': reference_bounds,
                    'resolution': reference_resolution,
                    'u': u_agg.tolist(),
                    'v': v_agg.tolist(),
                    'magnitude': magnitude_agg.tolist()
                }
                
                # Save aggregated flow
                aggregated_file = OUTPUT_DIR / f"{group_name}_aggregated_flow.json"
                with open(aggregated_file, 'w') as f:
                    json.dump(aggregated_data, f)
                
                print(f"    ✓ Saved aggregated flow: {aggregated_file}")
                print(f"      Grid size: {width} x {height}")
                print(f"      Species aggregated: {count}")
            else:
                print(f"    ⚠ No valid flows to aggregate for {group_name}")
                
        except Exception as e:
            print(f"    ✗ Error aggregating flows for {group_name}: {e}")
            import traceback
            traceback.print_exc()

def process_all_flows():
    """Process all connectivity files and generate flow vectors."""
    connectivity_files = list(OUTPUT_DIR.glob("*_connectivity.asc"))
    
    if not connectivity_files:
        print("No connectivity files found. Run run_circuitscape.py first.")
        print("Note: You can also use habitat rasters to generate sample flows.")
        return
    
    print(f"Found {len(connectivity_files)} connectivity files")
    
    # Organize by group
    groups = get_all_species_by_group()
    processed_count = 0
    
    for connectivity_file in connectivity_files:
        species_name = connectivity_file.stem.replace('_connectivity', '').replace('_', ' ')
        group = get_species_group(species_name)
        
        if group:
            print(f"\n[{group.upper()}] Processing {species_name}...")
        else:
            print(f"\n[UNKNOWN] Processing {species_name}...")
        
        try:
            process_connectivity_file(connectivity_file, species_name)
            processed_count += 1
        except Exception as e:
            print(f"  ✗ Error processing {species_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✓ Successfully processed {processed_count}/{len(connectivity_files)} connectivity files")
    
    # Aggregate flows by group
    print("\n" + "=" * 60)
    print("Aggregating flows by species group...")
    print("=" * 60)
    aggregate_flows()

if __name__ == "__main__":
    print("=" * 60)
    print("Generating Flow Vectors")
    print("=" * 60)
    
    process_all_flows()
    
    print("\n" + "=" * 60)
    print("Flow vector generation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review generated flow JSON files")
    print("2. Open web/index.html to visualize flows")


