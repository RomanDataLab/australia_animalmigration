"""
Run CircuitScape connectivity analysis for species migration.

This script runs CircuitScape to calculate connectivity between
current and future habitat locations.
"""

import os
import subprocess
import json
from pathlib import Path
import configparser
import sys
sys.path.insert(0, str(Path(__file__).parent))
from species_classification import get_species_group, get_all_species_by_group

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "output"
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)

def create_circuitscape_config(species_name, current_habitat, future_habitat, 
                                resistance_surface, output_dir):
    """
    Create a CircuitScape configuration file.
    
    Parameters:
    -----------
    species_name : str
        Name of the species
    current_habitat : Path
        Path to current habitat raster
    future_habitat : Path
        Path to future habitat raster
    resistance_surface : Path
        Path to resistance surface raster
    output_dir : Path
        Directory for output files
    """
    config = configparser.ConfigParser()
    
    config['Options for advanced mode'] = {
        'habitat_file_is_resistances': 'False',
        'habitat_file': str(resistance_surface),
        'point_file': str(current_habitat),
        'output_file': str(output_dir / f"{species_name}_current_flow.asc"),
        'set_null_currents_to_nodata': '1',
        'set_null_voltages_to_nodata': '1',
        'write_cur_maps': '1',
        'write_volt_maps': '1',
        'write_cum_cur_map_only': '1',
        'log_transform_maps': '0',
        'output_file': str(output_dir / f"{species_name}_connectivity.asc"),
        'scenario': 'pairwise',
        'low_memory_mode': 'False'
    }
    
    config_file = CONFIG_DIR / f"{species_name.replace(' ', '_')}_circuitscape.ini"
    with open(config_file, 'w') as f:
        config.write(f)
    
    return config_file

def run_circuitscape(config_file):
    """
    Run CircuitScape with the given configuration file.
    
    Parameters:
    -----------
    config_file : Path
        Path to CircuitScape configuration file
    """
    print(f"Running CircuitScape with config: {config_file}")
    
    try:
        # Run CircuitScape
        # Note: Adjust command based on your CircuitScape installation
        result = subprocess.run(
            ['python', '-m', 'circuitscape', str(config_file)],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("CircuitScape completed successfully")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"CircuitScape error: {e}")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("CircuitScape not found. Install with:")
        print("  conda install -c conda-forge circuitscape")
        print("  OR")
        print("  pip install circuitscape")
        return False

def process_species_connectivity(species_name):
    """
    Process connectivity for a single species.
    
    Parameters:
    -----------
    species_name : str
        Species name
    """
    species_safe = species_name.replace(' ', '_')
    
    # File paths
    current_habitat = OUTPUT_DIR / f"{species_safe}_current.tif"
    future_habitat = OUTPUT_DIR / f"{species_safe}_future.tif"
    resistance_surface = OUTPUT_DIR / "australia_resistance.tif"
    
    # Check if files exist
    if not current_habitat.exists():
        print(f"Current habitat file not found: {current_habitat}")
        return False
    
    if not future_habitat.exists():
        print(f"Future habitat file not found: {future_habitat}")
        print("NOTE: Create future habitat maps using climate projections first")
        return False
    
    if not resistance_surface.exists():
        print(f"Resistance surface not found: {resistance_surface}")
        print("NOTE: Create resistance surface first")
        return False
    
    # Create config file
    config_file = create_circuitscape_config(
        species_safe,
        current_habitat,
        future_habitat,
        resistance_surface,
        OUTPUT_DIR
    )
    
    # Run CircuitScape
    return run_circuitscape(config_file)

def process_all_species():
    """Process connectivity for all species."""
    # Find all current habitat files
    current_habitat_files = list(OUTPUT_DIR.glob("*_current.tif"))
    
    if not current_habitat_files:
        print("No habitat files found. Run process_species.py first.")
        return
    
    print(f"Found {len(current_habitat_files)} species to process")
    
    # Organize by group
    groups = get_all_species_by_group()
    print(f"\nSpecies by group:")
    for group, species_list in groups.items():
        count = len([f for f in current_habitat_files 
                    if get_species_group(f.stem.replace('_current', '').replace('_', ' ')) == group])
        print(f"  {group.capitalize()}: {count} species")
    
    processed_count = 0
    for habitat_file in current_habitat_files:
        species_name = habitat_file.stem.replace('_current', '').replace('_', ' ')
        group = get_species_group(species_name)
        
        print(f"\n{'='*60}")
        if group:
            print(f"[{group.upper()}] Processing: {species_name}")
        else:
            print(f"[UNKNOWN] Processing: {species_name}")
        print(f"{'='*60}")
        
        try:
            if process_species_connectivity(species_name):
                processed_count += 1
        except Exception as e:
            print(f"  ✗ Error processing {species_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✓ Successfully processed {processed_count}/{len(current_habitat_files)} species")

if __name__ == "__main__":
    print("=" * 60)
    print("CircuitScape Connectivity Analysis")
    print("=" * 60)
    
    # Check if CircuitScape is available
    try:
        import circuitscape
        print(f"CircuitScape version: {circuitscape.__version__}")
    except ImportError:
        print("WARNING: CircuitScape not installed")
        print("Install with: conda install -c conda-forge circuitscape")
        print("\nContinuing with template code...")
    
    process_all_species()
    
    print("\n" + "=" * 60)
    print("Connectivity analysis complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review connectivity results")
    print("2. Run generate_flow.py to create flow vectors")
    print("3. Visualize in web interface")


