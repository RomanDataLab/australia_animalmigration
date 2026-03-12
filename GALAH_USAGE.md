# Using Galah to Download Species Data

This project now uses [Galah](https://galah.ala.org.au/Python/), the official Python package for accessing biodiversity data from the Atlas of Living Australia (ALA).

## Installation

Install Galah along with other dependencies:

```bash
pip install -r requirements.txt
```

Or install Galah separately:

```bash
pip install galah
```

## Quick Start

### 1. Register an ALA Account (Optional but Recommended)

While not strictly required, having an ALA account allows you to:
- Access more data
- Avoid rate limiting
- Use advanced features

Register at: https://auth.ala.org.au/userdetails/registration

### 2. Download Species Data

Run the download script:

```bash
python scripts/download_data.py
```

The script will:
- Prompt you for your email address (or you can pass it as a parameter)
- Download occurrence records for common Australian species
- Save data in JSON format to `data/species/`

### 3. Customize Species List

Edit `scripts/download_data.py` to download data for your target species:

```python
species_list = [
    "Macropus giganteus",  # Eastern Grey Kangaroo
    "Phascolarctos cinereus",  # Koala
    "Your species name here",
]
```

## Galah Features

### Search for Species

```python
import galah

# Search for a species
species_info = galah.search_taxa(taxa="Macropus giganteus")
print(species_info)
```

### Download Occurrence Records

```python
import galah

# Configure Galah
galah.galah_config(atlas="Australia", email="your-email@example.com")

# Download occurrences with filters
occurrences = galah.atlas_occurrences(
    taxa="Macropus giganteus",
    filters=[
        "decimalLongitude>=113.0",
        "decimalLongitude<=154.0",
        "decimalLatitude>=-44.0",
        "decimalLatitude<=-10.0",
        "year>=2010"
    ],
    fields=["decimalLongitude", "decimalLatitude", "scientificName", "eventDate"]
)

print(occurrences)
```

### Data Quality Filters

The download script automatically applies quality filters:
- Removes records with very uncertain coordinates
- Filters by basis of record (observations, specimens, etc.)
- Restricts to Australia bounding box

You can customize filters in `scripts/download_data.py`.

## Advanced Usage

### Filter by Location

```python
occurrences = galah.atlas_occurrences(
    taxa="Phascolarctos cinereus",
    filters=["stateProvince=Queensland", "year>=2020"]
)
```

### Filter by Data Quality

```python
occurrences = galah.atlas_occurrences(
    taxa="Dromaius novaehollandiae",
    filters=[
        "coordinateUncertaintyInMeters<1000",  # High precision only
        "basisOfRecord=HUMAN_OBSERVATION"      # Only human observations
    ]
)
```

### Select Specific Fields

```python
occurrences = galah.atlas_occurrences(
    taxa="Tachyglossus aculeatus",
    fields=[
        "decimalLongitude",
        "decimalLatitude",
        "scientificName",
        "eventDate",
        "year",
        "month",
        "dataResourceName"
    ]
)
```

## Resources

- **Galah Documentation**: https://galah.ala.org.au/Python/
- **Galah User Guide**: https://galah.ala.org.au/Python/galah_user_guide/
- **Galah API Docs**: https://galah.ala.org.au/Python/api_docs/
- **ALA Website**: https://www.ala.org.au/
- **ALA Registration**: https://auth.ala.org.au/userdetails/registration

## Troubleshooting

### "galah package not installed"
```bash
pip install galah
```

### "No occurrence records found"
- Check that the species name is correct (use scientific name)
- Try searching for the species first: `galah.search_taxa(taxa="species name")`
- Verify the species occurs in Australia
- Check that filters aren't too restrictive

### Rate Limiting
- Register an ALA account and configure Galah with your email
- Add delays between requests if downloading many species
- Consider using `atlas_occurrences()` with smaller date ranges

### Data Format Issues
The download script converts Galah DataFrames to JSON format compatible with `process_species.py`. If you need to modify the format, edit the conversion in `download_ala_species_data()`.





