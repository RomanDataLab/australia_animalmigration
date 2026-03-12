# Setup Guide: Australia Migrations in Motion Map

This guide will help you set up and run the migration flow visualization for Australia.

## Prerequisites

1. **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)
2. **CircuitScape** - Install via conda (recommended) or pip
3. **Mapbox Account** - Free account at [mapbox.com](https://account.mapbox.com/)

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install CircuitScape

**Option A: Using Conda (Recommended)**
```bash
conda install -c conda-forge circuitscape
```

**Option B: Using Pip**
```bash
pip install circuitscape
```

Verify installation:
```bash
python -c "import circuitscape; print(circuitscape.__version__)"
```

### 3. Create Data Directories

```bash
mkdir -p data/species data/climate data/output
```

### 4. Set Up Mapbox Access Token

1. Sign up for a free Mapbox account at https://account.mapbox.com/
2. Get your access token from the account dashboard
3. Edit `web/js/map.js` and replace `YOUR_MAPBOX_ACCESS_TOKEN` with your token

**OR** use an environment variable (recommended for production):

Create a `.env` file in the project root:
```
MAPBOX_TOKEN=your_token_here
```

Then modify `web/js/map.js` to read from environment (requires a build step or server-side rendering).

### 5. Download Data

#### Option A: Use Atlas of Living Australia API

```bash
python scripts/download_data.py
```

This will download species occurrence data from the ALA API.

#### Option B: Manual Data Download

1. **Species Data**: Visit https://www.ala.org.au/ and download species distribution data
2. **Climate Data**: Download from:
   - WorldClim: https://www.worldclim.org/data/cmip6/cmip6_clim.html
   - CSIRO Climate Change projections
   - Australian Bureau of Meteorology

Place downloaded files in `data/species/` and `data/climate/` directories.

### 6. Process Species Data

```bash
python scripts/process_species.py
```

This converts raw occurrence data into habitat rasters.

### 7. Create Resistance Surfaces

You'll need to create resistance surfaces that represent landscape permeability. This typically requires:

- Land use/land cover data
- Elevation data
- Road networks
- Urban areas
- Other barriers to movement

Use GIS software (QGIS, ArcGIS) or Python with rasterio/geopandas to create these.

Save resistance surfaces as GeoTIFF files in `data/output/`.

### 8. Run CircuitScape Analysis

```bash
python scripts/run_circuitscape.py
```

This calculates connectivity between current and future habitats.

**Note**: You'll need to create future habitat maps first using species distribution modeling (e.g., MaxEnt, BIOMOD2) with climate projection data.

### 9. Generate Flow Vectors

```bash
python scripts/generate_flow.py
```

This converts CircuitScape results into flow vectors for visualization.

### 10. View the Map

#### Option A: Simple HTTP Server

```bash
cd web
python -m http.server 8000
```

Then open http://localhost:8000 in your browser.

#### Option B: Using Node.js (if installed)

```bash
cd web
npx http-server -p 8000
```

## Data Workflow Summary

```
1. Download Data
   └─> scripts/download_data.py
       └─> data/species/*.json

2. Process Species
   └─> scripts/process_species.py
       └─> data/output/*_current.tif

3. Create Future Habitats (Manual/SDM)
   └─> data/output/*_future.tif

4. Create Resistance Surfaces (Manual/GIS)
   └─> data/output/*_resistance.tif

5. Run CircuitScape
   └─> scripts/run_circuitscape.py
       └─> data/output/*_connectivity.asc

6. Generate Flow Vectors
   └─> scripts/generate_flow.py
       └─> data/output/*_flow.json

7. Visualize
   └─> web/index.html
```

## Troubleshooting

### CircuitScape Not Found

If you get "CircuitScape not found" errors:

1. Verify installation:
   ```bash
   conda list circuitscape
   # OR
   pip list | grep circuitscape
   ```

2. If using conda, activate your environment:
   ```bash
   conda activate your_environment
   ```

### Map Not Displaying

1. Check browser console for errors
2. Verify Mapbox token is set correctly
3. Check that flow data files exist in `data/output/`

### Flow Visualization Not Working

1. Check browser console for JavaScript errors
2. Verify flow JSON files are valid JSON
3. Check that flow data bounds match Australia's extent

## Next Steps

1. **Customize Species**: Edit `scripts/download_data.py` to include your target species
2. **Improve Resistance Surfaces**: Add more landscape factors (roads, urban areas, etc.)
3. **Add More Species Groups**: Extend the visualization to include reptiles, insects, etc.
4. **Climate Scenarios**: Add multiple climate projection scenarios (RCP 4.5, RCP 8.5, etc.)

## Resources

- [CircuitScape Documentation](https://circuitscape.org/)
- [Atlas of Living Australia](https://www.ala.org.au/)
- [Mapbox GL JS Documentation](https://docs.mapbox.com/mapbox-gl-js/)
- [Migrations in Motion (Original)](https://www.maps.tnc.org/migrations-in-motion/)

## Getting Help

- Check the main README.md for more information
- Review CircuitScape documentation for connectivity modeling
- Consult ALA documentation for data access


