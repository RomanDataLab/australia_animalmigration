"""
Download species distribution and climate projection data for Australia.

This script downloads data from:
- Atlas of Living Australia (ALA) using the Galah package
- Climate projection datasets
- Species distribution data

Galah documentation: https://galah.ala.org.au/Python/
"""

import os
import json
from pathlib import Path
from tqdm import tqdm

try:
    import galah
except ImportError:
    print("ERROR: galah-python package not installed. Install it with: pip install galah-python")
    print("See https://galah.ala.org.au/Python/getting_started/Installation.html for more information")
    print("Prerequisites: pip install numpy pandas requests urllib3 TIME-python zip-files configparser glob2 shutils setuptools shapely pytest unittest2py3k")
    exit(1)

# Create data directories
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SPECIES_DIR = DATA_DIR / "species"
CLIMATE_DIR = DATA_DIR / "climate"
OUTPUT_DIR = DATA_DIR / "output"

for dir_path in [SPECIES_DIR, CLIMATE_DIR, OUTPUT_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# Australia bounding box for filtering
AUSTRALIA_BOUNDS = {
    'minx': 113.0,  # West
    'miny': -44.0,  # South
    'maxx': 154.0,  # East
    'maxy': -10.0   # North
}

def configure_galah(email=None):
    """
    Configure Galah to use the Australian atlas.
    
    Parameters:
    -----------
    email : str, optional
        Email address for ALA account. If None, will prompt user.
    """
    if email is None:
        print("\n" + "="*60)
        print("Galah Configuration")
        print("="*60)
        print("Galah requires an email address for the ALA account.")
        print("You can register at: https://auth.ala.org.au/userdetails/registration")
        email = input("Enter your email address (or press Enter to skip): ").strip()
    
    if email:
        try:
            galah.galah_config(atlas="Australia", email=email)
            print(f"✓ Galah configured with email: {email}")
            return True
        except Exception as e:
            print(f"Warning: Could not configure Galah: {e}")
            print("You may still be able to download data, but some features may be limited.")
            return False
    else:
        print("Skipping Galah configuration. Some features may be limited.")
        return False

def download_ala_species_data(species_list=None, output_dir=SPECIES_DIR, 
                               email=None, quality_filters=True):
    """
    Download species distribution data from Atlas of Living Australia using Galah.
    
    Parameters:
    -----------
    species_list : list, optional
        List of species names to download. If None, downloads common Australian species.
    output_dir : Path
        Directory to save downloaded data
    email : str, optional
        Email address for ALA account
    quality_filters : bool
        Apply data quality filters (remove records with coordinate issues, etc.)
    """
    print("\n" + "="*60)
    print("Downloading species data from Atlas of Living Australia")
    print("Using Galah Python package: https://galah.ala.org.au/Python/")
    print("="*60)
    
    # Configure Galah
    configure_galah(email)
    
    # Example species list - replace with your target species
    # Organized by group for color-coded visualization (10 species per group)
    if species_list is None:
        species_list = [
            # Mammals (10 species)
            "Macropus giganteus",  # Eastern Grey Kangaroo
            "Phascolarctos cinereus",  # Koala
            "Tachyglossus aculeatus",  # Short-beaked Echidna
            "Macropus rufus",  # Red Kangaroo
            "Vombatus ursinus",  # Common Wombat
            "Trichosurus vulpecula",  # Common Brushtail Possum
            "Isoodon obesulus",  # Southern Brown Bandicoot
            "Perameles nasuta",  # Long-nosed Bandicoot
            "Wallabia bicolor",  # Swamp Wallaby
            "Pseudocheirus peregrinus",  # Common Ringtail Possum
            # Birds (10 species)
            "Dromaius novaehollandiae",  # Emu
            "Cacatua galerita",  # Sulphur-crested Cockatoo
            "Gymnorhina tibicen",  # Australian Magpie
            "Platycercus eximius",  # Eastern Rosella
            "Corvus coronoides",  # Australian Raven
            "Acanthiza pusilla",  # Brown Thornbill
            "Meliphaga lewinii",  # Lewin's Honeyeater
            "Pardalotus punctatus",  # Spotted Pardalote
            "Rhipidura leucophrys",  # Willie Wagtail
            "Eolophus roseicapilla",  # Galah
            # Amphibians (10 species)
            "Litoria caerulea",  # Green Tree Frog
            "Limnodynastes dumerilii",  # Pobblebonk Frog
            "Crinia signifera",  # Common Eastern Froglet
            "Litoria peronii",  # Peron's Tree Frog
            "Limnodynastes tasmaniensis",  # Spotted Grass Frog
            "Litoria ewingii",  # Brown Tree Frog
            "Uperoleia laevigata",  # Smooth Toadlet
            "Litoria raniformis",  # Growling Grass Frog
            "Pseudophryne bibronii",  # Bibron's Toadlet
            "Litoria verreauxii",  # Verreaux's Tree Frog
        ]
    
    print(f"\nDownloading data for {len(species_list)} species...")
    
    for species in tqdm(species_list, desc="Downloading species"):
        try:
            # Build filters for Australia bounds and data quality
            filters = [
                f"decimalLongitude>={AUSTRALIA_BOUNDS['minx']}",
                f"decimalLongitude<={AUSTRALIA_BOUNDS['maxx']}",
                f"decimalLatitude>={AUSTRALIA_BOUNDS['miny']}",
                f"decimalLatitude<={AUSTRALIA_BOUNDS['maxy']}"
            ]
            
            if quality_filters:
                # Add data quality filters
                filters.extend([
                    "basisOfRecord=HUMAN_OBSERVATION|OBSERVATION|MACHINE_OBSERVATION|SPECIMEN",
                    "coordinateUncertaintyInMeters<10000"  # Remove very uncertain coordinates
                ])
            
            # Fields to download (matching what process_species.py expects)
            fields = [
                "decimalLongitude",
                "decimalLatitude",
                "scientificName",
                "eventDate",
                "year",
                "month",
                "basisOfRecord",
                "coordinateUncertaintyInMeters",
                "dataResourceName"
            ]
            
            # First, search for the species to get correct taxon information
            print(f"\n  Searching for {species}...")
            try:
                taxa_info = galah.search_taxa(taxa=species)
                if taxa_info is None or len(taxa_info) == 0:
                    print(f"  ⚠ Species not found: {species}")
                    continue
                print(f"  ✓ Found taxon: {taxa_info.iloc[0]['scientificName'] if 'scientificName' in taxa_info.columns else species}")
            except Exception as e:
                print(f"  ⚠ Could not search for species: {e}")
                # Continue anyway with the provided name
            
            # Download occurrence records using Galah
            print(f"  Fetching occurrence records...")
            try:
                # Try with fewer filters first
                basic_filters = [
                    f"decimalLongitude>={AUSTRALIA_BOUNDS['minx']}",
                    f"decimalLongitude<={AUSTRALIA_BOUNDS['maxx']}",
                    f"decimalLatitude>={AUSTRALIA_BOUNDS['miny']}",
                    f"decimalLatitude<={AUSTRALIA_BOUNDS['maxy']}"
                ]
                
                occurrences = galah.atlas_occurrences(
                    taxa=species,
                    filters=basic_filters,
                    fields=fields
                )
                
                if occurrences is None or len(occurrences) == 0:
                    # Try without any filters except species
                    print(f"  Trying without location filters...")
                    occurrences = galah.atlas_occurrences(
                        taxa=species,
                        fields=fields
                    )
                    
                if occurrences is None or len(occurrences) == 0:
                    print(f"  ⚠ No occurrence records found for {species}")
                    continue
            except Exception as e:
                print(f"  ✗ Error fetching records: {e}")
                continue
            
            print(f"  ✓ Found {len(occurrences)} occurrence records")
            
            # Convert DataFrame to list of dictionaries (JSON-compatible format)
            # This matches the format expected by process_species.py
            records = occurrences.to_dict('records')
            
            # Save as JSON
            species_safe = species.replace(' ', '_')
            output_file = output_dir / f"{species_safe}.json"
            
            with open(output_file, 'w') as f:
                json.dump(records, f, indent=2, default=str)
            
            print(f"  ✓ Saved {len(records)} records to {output_file}")
                
        except Exception as e:
            print(f"  ✗ Error downloading {species}: {str(e)}")
            import traceback
            traceback.print_exc()

def download_climate_data(output_dir=CLIMATE_DIR):
    """
    Download climate projection data for Australia.
    
    Note: This is a template. You'll need to adapt this to your specific
    climate data source (e.g., WorldClim, CSIRO, BoM).
    """
    print("Downloading climate projection data...")
    print("NOTE: You'll need to manually download climate data from:")
    print("  - WorldClim: https://www.worldclim.org/")
    print("  - CSIRO: https://www.csiro.au/en/research/environmental-impacts/climate-change")
    print("  - Australian Bureau of Meteorology")
    print("\nPlace downloaded files in:", output_dir)

def create_australia_resistance_surface(output_file=None):
    """
    Create a basic resistance surface for Australia.
    
    This is a template that creates a simple resistance surface based on
    land use and elevation. You should customize this based on your specific
    species and landscape data.
    """
    if output_file is None:
        output_file = OUTPUT_DIR / "australia_resistance.tif"
    
    print("Creating resistance surface...")
    print("NOTE: This requires actual land use and elevation data.")
    print("You'll need to create this using GIS software or Python with:")
    print("  - Land use/land cover data")
    print("  - Elevation data")
    print("  - Road networks")
    print("  - Urban areas")
    print("\nOutput file:", output_file)

if __name__ == "__main__":
    print("=" * 60)
    print("Australia Migrations in Motion - Data Download")
    print("=" * 60)
    print("\nThis script uses Galah to download species data from ALA.")
    print("Galah documentation: https://galah.ala.org.au/Python/")
    print("\nNote: You may need to register an ALA account at:")
    print("      https://auth.ala.org.au/userdetails/registration")
    print("=" * 60)
    
    # Download species data
    # Using provided email address
    download_ala_species_data(email="hermandataset@gmail.com")
    
    # Download climate data (template)
    download_climate_data()
    
    # Create resistance surface (template)
    create_australia_resistance_surface()
    
    print("\n" + "=" * 60)
    print("Data download complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review downloaded species data in data/species/")
    print("2. Download climate projection data manually")
    print("3. Create resistance surfaces for your target species")
    print("4. Run process_species.py to prepare data for CircuitScape")
    print("\nFor more information on Galah:")
    print("  - Documentation: https://galah.ala.org.au/Python/")
    print("  - User Guide: https://galah.ala.org.au/Python/galah_user_guide/")


