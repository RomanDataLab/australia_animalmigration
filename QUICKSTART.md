# Quick Start Guide

Get up and running quickly with a demo visualization.

## Minimal Setup (5 minutes)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Mapbox Token

1. Sign up at https://account.mapbox.com/ (free)
2. Copy your access token
3. Edit `web/js/map.js` line 4, replace `YOUR_MAPBOX_ACCESS_TOKEN`

### 3. Run Demo

```bash
cd web
python -m http.server 8000
```

Open http://localhost:8000?token=YOUR_TOKEN (replace YOUR_TOKEN)

The demo includes sample flow data that creates a circular flow pattern for visualization testing.

## What You'll See

- Interactive map of Australia
- Animated flow particles showing migration direction
- Controls to toggle species groups (mammals, birds, amphibians)
- Advanced visualization controls

## Next Steps

To use real data:

1. **Download real species data**: Run `python scripts/download_data.py`
2. **Process data**: Run `python scripts/process_species.py`
3. **Create resistance surfaces**: Use GIS software or Python
4. **Run CircuitScape**: `python scripts/run_circuitscape.py`
5. **Generate flows**: `python scripts/generate_flow.py`
6. **Update web/js/flow.js**: Modify `loadFlowData()` to load your real flow JSON files

See SETUP.md for detailed instructions.


