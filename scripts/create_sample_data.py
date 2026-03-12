"""
Create sample flow data for testing the visualization.
This generates demo flow vectors so you can see the visualization working.
Creates sample data for all species groups (mammals, birds, amphibians).
"""

import json
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from species_classification import get_all_species_by_group

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def create_sample_flow_data_for_group(group_name, pattern='circular'):
    """
    Create sample flow data for a specific group.
    
    Parameters:
    -----------
    group_name : str
        Group name ('mammals', 'birds', 'amphibians')
    pattern : str
        Flow pattern type ('circular', 'northward', 'southward', 'eastward', 'westward')
    """
    # Australia bounding box
    bounds = {
        'minx': 113.0,
        'miny': -44.0,
        'maxx': 154.0,
        'maxy': -10.0
    }
    
    # Create flow grid (downsampled for web performance)
    width = 80
    height = 68
    # Calculate separate resolutions for x (longitude) and y (latitude)
    # This ensures the grid aligns properly with geographic boundaries
    x_resolution = (bounds['maxx'] - bounds['minx']) / width
    y_resolution = abs(bounds['maxy'] - bounds['miny']) / height
    # For backward compatibility, also store a single resolution (average)
    resolution = (x_resolution + y_resolution) / 2
    
    # Create flow vectors with different patterns per group
    u = []
    v = []
    magnitude = []
    
    center_x = width / 2
    center_y = height / 2
    
    # Different patterns for different groups
    pattern_offsets = {
        'mammals': 0,      # Circular
        'birds': np.pi / 4,  # Rotated circular
        'amphibians': np.pi / 2  # Different rotation
    }
    offset = pattern_offsets.get(group_name, 0)
    
    for y in range(height):
        u_row = []
        v_row = []
        mag_row = []
        
        for x in range(width):
            dx = x - center_x
            dy = y - center_y
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance > 0:
                # Create flow pattern based on group
                if pattern == 'circular':
                    angle = np.arctan2(dy, dx) + np.pi / 2 + offset
                    u_val = np.cos(angle) * 0.3
                    v_val = np.sin(angle) * 0.3
                elif pattern == 'northward':
                    u_val = np.random.normal(0, 0.05)
                    v_val = -0.3  # Northward
                elif pattern == 'southward':
                    u_val = np.random.normal(0, 0.05)
                    v_val = 0.3  # Southward
                elif pattern == 'eastward':
                    u_val = 0.3  # Eastward
                    v_val = np.random.normal(0, 0.05)
                elif pattern == 'westward':
                    u_val = -0.3  # Westward
                    v_val = np.random.normal(0, 0.05)
                else:
                    angle = np.arctan2(dy, dx) + np.pi / 2 + offset
                    u_val = np.cos(angle) * 0.3
                    v_val = np.sin(angle) * 0.3
                
                # Add some variation
                u_val += np.random.normal(0, 0.1)
                v_val += np.random.normal(0, 0.1)
                
                # Magnitude based on distance from center
                mag_val = 0.3 + 0.7 * np.exp(-distance / 20)
            else:
                u_val = 0
                v_val = 0
                mag_val = 0
            
            u_row.append(float(u_val))
            v_row.append(float(v_val))
            mag_row.append(float(mag_val))
        
        u.append(u_row)
        v.append(v_row)
        magnitude.append(mag_row)
    
    # Create flow data structure
    flow_data = {
        'group': group_name,
        'species': 'sample',
        'bounds': bounds,
        'resolution': resolution,  # Average resolution for backward compatibility
        'x_resolution': x_resolution,  # Longitude resolution (degrees per cell)
        'y_resolution': y_resolution,  # Latitude resolution (degrees per cell)
        'u': u,
        'v': v,
        'magnitude': magnitude
    }
    
    # Save to JSON
    output_file = OUTPUT_DIR / f"{group_name}_aggregated_flow.json"
    with open(output_file, 'w') as f:
        json.dump(flow_data, f, indent=2)
    
    print(f"  ✓ Created {group_name} flow data: {output_file}")
    print(f"    Grid size: {width} x {height}")
    print(f"    X resolution (lon): {x_resolution:.4f} degrees/cell")
    print(f"    Y resolution (lat): {y_resolution:.4f} degrees/cell")
    print(f"    Average resolution: {resolution:.4f} degrees")
    
    return output_file

def create_sample_flow_data():
    """Create sample flow data for all groups."""
    print("Creating sample flow data for all species groups...")
    
    groups = get_all_species_by_group()
    output_files = []
    
    for group_name in groups.keys():
        print(f"\nCreating sample data for {group_name}...")
        output_file = create_sample_flow_data_for_group(group_name, pattern='circular')
        output_files.append(output_file)
    
    # Also create a generic sample file
    print(f"\nCreating generic sample flow data...")
    generic_data = create_sample_flow_data_for_group('mammals', pattern='circular')
    generic_file = OUTPUT_DIR / "sample_flow.json"
    
    # Copy mammals data to sample_flow.json
    with open(generic_data, 'r') as f:
        data = json.load(f)
    data['species'] = 'sample'
    if 'group' in data:
        del data['group']
    
    with open(generic_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"  ✓ Created generic sample flow data: {generic_file}")
    
    return output_files

if __name__ == "__main__":
    print("=" * 60)
    print("Creating Sample Flow Data for All Species Groups")
    print("=" * 60)
    print("\nThis will create sample flow data files for:")
    print("  - Mammals (mammals_aggregated_flow.json)")
    print("  - Birds (birds_aggregated_flow.json)")
    print("  - Amphibians (amphibians_aggregated_flow.json)")
    print("  - Generic sample (sample_flow.json)")
    print()
    
    create_sample_flow_data()
    
    print("\n" + "=" * 60)
    print("Sample data created!")
    print("=" * 60)
    print("\nYou can now test the web visualization with color-coded flows.")
    print("Open http://localhost:8000 to see the visualization.")


