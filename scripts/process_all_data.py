"""
Master script to process all data for the map visualization.

This script runs all data processing steps in sequence:
1. Process species data
2. Generate sample flow data (if CircuitScape not available)
3. Aggregate flows by group
"""

import sys
from pathlib import Path
import subprocess

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

def run_script(script_name, description):
    """Run a Python script and handle errors."""
    print("\n" + "=" * 60)
    print(description)
    print("=" * 60)
    
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"✗ Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=False
        )
        
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True
        else:
            print(f"⚠ {description} completed with warnings (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"✗ Error running {script_name}: {e}")
        return False

def main():
    """Run all data processing steps."""
    print("=" * 60)
    print("Australia Migrations in Motion - Complete Data Processing")
    print("=" * 60)
    print("\nThis script will process all data for the map visualization.")
    print("Steps:")
    print("  1. Process species distribution data")
    print("  2. Create sample flow data (for testing)")
    print("  3. Generate flow vectors (if CircuitScape data available)")
    print()
    
    input("Press Enter to continue or Ctrl+C to cancel...")
    
    # Step 1: Process species data
    success1 = run_script(
        "process_species.py",
        "Processing Species Distribution Data"
    )
    
    if not success1:
        print("\n⚠ Warning: Species processing had issues. Continuing anyway...")
    
    # Step 2: Create sample flow data
    success2 = run_script(
        "create_sample_data.py",
        "Creating Sample Flow Data"
    )
    
    if not success2:
        print("\n⚠ Warning: Sample data creation had issues.")
    
    # Step 3: Try to generate flow vectors (may not have CircuitScape data)
    print("\n" + "=" * 60)
    print("Generating Flow Vectors (if CircuitScape data available)")
    print("=" * 60)
    print("\nNote: This step requires CircuitScape connectivity files.")
    print("      If you don't have them, the sample data from step 2 will be used.")
    
    success3 = run_script(
        "generate_flow.py",
        "Generating Flow Vectors"
    )
    
    if not success3:
        print("\n⚠ No CircuitScape data found. Using sample flow data instead.")
    
    # Summary
    print("\n" + "=" * 60)
    print("Data Processing Complete!")
    print("=" * 60)
    print("\nSummary:")
    print(f"  Species processing: {'✓' if success1 else '⚠'}")
    print(f"  Sample data creation: {'✓' if success2 else '⚠'}")
    print(f"  Flow vector generation: {'✓' if success3 else '⚠ (using sample data)'}")
    print("\nNext steps:")
    print("  1. Start the web server: cd web && python -m http.server 8000")
    print("  2. Open http://localhost:8000 in your browser")
    print("  3. You should see color-coded flows for mammals, birds, and amphibians")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcessing cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

