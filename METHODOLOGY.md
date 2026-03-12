# Migration of Animals — Australia: Methodology

## 1. Introduction

This document describes the methodology used to build an interactive web map visualising predicted climate-driven migration flows for 30 Australian species across three taxonomic groups: mammals (10), birds (10) and amphibians (10). The visualisation combines species occurrence data, synthetic resistance surfaces and particle-trail animation to show the average direction each group needs to move to track hospitable climates under projected warming.

## 2. Species Selection

Thirty species were chosen to represent a range of mobility traits, habitat requirements and geographic distributions within Australia.

### Mammals

| # | Scientific name | Common name |
|---|----------------|-------------|
| 1 | *Macropus giganteus* | Eastern Grey Kangaroo |
| 2 | *Phascolarctos cinereus* | Koala |
| 3 | *Tachyglossus aculeatus* | Short-beaked Echidna |
| 4 | *Macropus rufus* | Red Kangaroo |
| 5 | *Vombatus ursinus* | Common Wombat |
| 6 | *Trichosurus vulpecula* | Common Brushtail Possum |
| 7 | *Isoodon obesulus* | Southern Brown Bandicoot |
| 8 | *Perameles nasuta* | Long-nosed Bandicoot |
| 9 | *Wallabia bicolor* | Swamp Wallaby |
| 10 | *Pseudocheirus peregrinus* | Common Ringtail Possum |

### Birds

| # | Scientific name | Common name |
|---|----------------|-------------|
| 1 | *Dromaius novaehollandiae* | Emu |
| 2 | *Cacatua galerita* | Sulphur-crested Cockatoo |
| 3 | *Gymnorhina tibicen* | Australian Magpie |
| 4 | *Platycercus eximius* | Eastern Rosella |
| 5 | *Corvus coronoides* | Australian Raven |
| 6 | *Acanthiza pusilla* | Brown Thornbill |
| 7 | *Meliphaga lewinii* | Lewin's Honeyeater |
| 8 | *Pardalotus punctatus* | Spotted Pardalote |
| 9 | *Rhipidura leucophrys* | Willie Wagtail |
| 10 | *Eolophus roseicapilla* | Galah |

### Amphibians

| # | Scientific name | Common name |
|---|----------------|-------------|
| 1 | *Litoria caerulea* | Green Tree Frog |
| 2 | *Limnodynastes dumerilii* | Eastern Banjo Frog |
| 3 | *Crinia signifera* | Common Eastern Froglet |
| 4 | *Litoria peronii* | Peron's Tree Frog |
| 5 | *Limnodynastes tasmaniensis* | Spotted Grass Frog |
| 6 | *Litoria ewingii* | Brown Tree Frog |
| 7 | *Uperoleia laevigata* | Smooth Toadlet |
| 8 | *Litoria raniformis* | Growling Grass Frog |
| 9 | *Pseudophryne bibronii* | Bibron's Toadlet |
| 10 | *Litoria verreauxii* | Verreaux's Tree Frog |

## 3. Data Acquisition

### 3.1 Species Occurrence Records

Occurrence records were obtained from the Atlas of Living Australia (ALA) using the Galah Python API (Atlas of Living Australia, 2024). For each species, all verified records within the study extent were downloaded with the following quality filters:

- **Basis of record**: human observation, machine observation or specimen
- **Coordinate uncertainty**: < 10 000 m
- **Geographic extent**: 113.0–154.0 °E, 44.0–10.0 °S

Each record includes decimal longitude and latitude (WGS 84), observation date and data-resource provenance. Records containing invalid or null coordinates were discarded during processing.

### 3.2 Australia Boundary

A GeoJSON polygon of the Australian coastline was used for two purposes: (i) constructing a binary land mask at each grid resolution and (ii) constraining particles to land during visualisation. Point-in-polygon testing uses the ray-casting algorithm (Shimrat, 1962).

## 4. Flow Vector Generation

### 4.1 Density Grid

For each species the occurrence points are binned into a regular grid covering the study extent. Two grid resolutions are used:

| Level | Width | Height | Cell size |
|-------|-------|--------|-----------|
| Per-species | 80 | 68 | ~0.51° lon × 0.50° lat |
| Aggregated (group) | 160 | 136 | ~0.26° lon × 0.25° lat |

The raw count grid is smoothed with a Gaussian kernel (σ = 4.0 cells for per-species, σ = 5.0 for aggregated) and normalised to [0, 1] by dividing by the maximum value (Jones *et al.*, 1996).

### 4.2 Flow Components

The flow vector at each land cell is the sum of three components.

#### Density-gradient dispersal

The spatial gradient of the smoothed density surface gives the local direction of increasing habitat suitability:

```
u_disp = ∂density/∂x × 0.2
v_disp = −∂density/∂y × 0.2
```

#### Climate-shift vector

A constant poleward (southward in the Southern Hemisphere) vector represents the expected direction of climate-envelope movement (Lawler *et al.*, 2013):

| Group | u (east–west) | v (north–south) |
|-------|---------------|-----------------|
| Mammals | +0.03 | −0.12 |
| Birds | −0.04 | −0.08 |
| Amphibians | +0.01 | −0.15 |

The climate vector is weighted by a broadened habitat mask (Gaussian σ = 6.0, scaled ×3, clipped to [0, 1]) so that flow appears only in ecologically plausible areas.

#### Stochastic noise

Low-amplitude Gaussian noise (μ = 0, σ = 0.02) weighted by the habitat mask adds spatial variation that prevents unrealistically parallel streamlines.

### 4.3 Resistance-Aware Steering

After summing the three components, the flow is steered by the conductance surface (inverse of resistance):

```
conductance = 1 / clamp(resistance, 0.05, 1.0)
∇conductance = (∂C/∂x, ∂C/∂y)
```

The conductance gradient is added to the flow with a group-specific weight:

| Group | Resistance steering weight |
|-------|---------------------------|
| Mammals | 0.35 |
| Birds | 0.08 |
| Amphibians | 0.45 |

Flow magnitude is additionally scaled by normalised conductance (clipped to [0.15, 1.0]) so that particles slow in high-resistance areas such as arid deserts and steep mountain ranges.

### 4.4 Post-processing

1. Both u and v components are smoothed (Gaussian σ = 2.0) to remove high-frequency artefacts.
2. Vectors are normalised to unit length; magnitude is recalculated as 0.7 × habitat weight + 0.3 × density.
3. Ocean cells and cells with magnitude < 0.02 are zeroed.

### 4.5 Output Format

Each species and group flow is saved as a JSON file containing three 2D arrays (u, v, magnitude) plus geographic metadata (bounds, resolution). Row 0 corresponds to the northernmost latitude; column 0 to the westernmost longitude.

## 5. Resistance Surfaces

### 5.1 Rationale

Landscape resistance modifies the cost of animal movement. Mountains, deserts and water bodies impede terrestrial species differently from birds. Because the project environment lacked GDAL/rasterio for reading large remote-sensing datasets, a synthetic terrain model was constructed from known Australian geography.

### 5.2 Synthetic Elevation

An elevation raster was built from Gaussian functions centred on major physiographic features:

| Feature | Centre | Peak elevation |
|---------|--------|----------------|
| Great Dividing Range | ~149 °E, −38 to −15 °S | 1 200 m |
| Australian Alps | 148.5 °E, −36.5 °S | 800 m |
| MacDonnell Ranges | 134 °E, −24 °S | 600 m |
| Flinders Ranges | 138.5 °E, −31.5 °S | 500 m |
| Western Plateau | west of 135 °E | +300 m base |

Coastal cells (within 5 % of maximum coast distance) are reduced to 30 % of base elevation.

### 5.3 Aridity Index

An aridity proxy (0 = wet, 1 = arid) was derived from Euclidean distance to the coastline, modified by latitude-zone multipliers that reflect Australia's rainfall patterns:

| Zone | Multiplier | Rationale |
|------|-----------|-----------|
| Tropical north (> −20 °S) | ×0.4 | Monsoon rainfall |
| Southeast (< −30 °S, > 145 °E) | ×0.3 | Temperate rainfall |
| Tasmania (< −40 °S, 144–149 °E) | ×0.2 | High rainfall |
| East-coast strip (> 148 °E) | ×0.5 | Orographic rainfall |
| Southwest WA (< −30 °S, < 120 °E) | ×0.6 | Mediterranean climate |

The result is Gaussian-smoothed (σ = 2.0) and clipped to [0, 1].

### 5.4 Ruggedness

Terrain ruggedness is the magnitude of the elevation gradient, normalised to [0, 1].

### 5.5 Group-Specific Resistance

The final resistance surface for each group is a weighted sum:

| Group | Base | Aridity weight | Ruggedness weight | Elevation weight |
|-------|------|---------------|-------------------|-----------------|
| Mammals | 0.10 | 0.40 | 0.35 | 0.15 |
| Birds | 0.05 | 0.15 | 0.05 | 0.00 |
| Amphibians | 0.10 | 0.55 | 0.25 | 0.10 |

Land cells are normalised to [0.01, 0.99]; ocean cells are set to 1.0 (impassable). A final Gaussian smoothing (σ = 1.5) ensures visual coherence. Output files are saved as NumPy arrays at both grid resolutions.

## 6. Visualisation

### 6.1 Map Platform

The base map uses Mapbox GL JS v2.15.0 in flat Mercator projection (EPSG:3857) centred on [134.0 °E, −28.0 °S] at zoom 3.8, showing all of Australia including Tasmania. Globe mode and map rotation are disabled.

### 6.2 Particle-Trail Animation

An HTML5 Canvas overlay renders up to 4 500 particles simultaneously. Each particle:

1. Is placed randomly on land (ray-casting point-in-polygon test).
2. Is assigned to one of the active species by round-robin.
3. Advances each frame by the bilinearly interpolated flow vector at its current position.
4. Maintains a 30-position trail buffer; older positions are drawn with quadratically decaying alpha and tapered line width.
5. Is reset to a new random land point when it reaches maximum age, moves off land, or enters a zero-flow area.

Device pixel ratio (DPR) correction ensures canvas coordinates match Mapbox screen coordinates on high-DPI displays.

### 6.3 Colour Encoding

Each group uses a 10-shade palette so that individual species are visually distinguishable:

- **Mammals**: red spectrum (bright red → amber → deep red)
- **Birds**: blue spectrum (sky blue → royal blue → indigo)
- **Amphibians**: green spectrum (bright green → lime → teal)

### 6.4 Interactive Controls

| Control | Behaviour |
|---------|-----------|
| Species image tile (click) | Toggle species on/off (greyscale when off) |
| Species image tile (double-click) | Open Wikipedia article in new tab |
| Species image tile (hover) | Tooltip with common and scientific name |
| Group header checkbox | Toggle all species in group |
| Group header (click) | Collapse/expand species image grid |
| Move button | Enable map panning and zooming; hide flows |
| Stop button (default) | Lock map position; show flows |
| Advanced sliders | Adjust particle density, speed, line width, opacity |

Species thumbnail images are fetched at runtime from the Wikipedia REST API (`/api/rest_v1/page/summary/{title}`).

## 7. Pipeline Summary

```
┌─────────────────────────────────────────┐
│ 1. Download occurrence data (ALA/Galah) │
│    → data/species/{species}.json        │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 2. Build resistance surfaces            │
│    Synthetic elevation + aridity +      │
│    ruggedness → per-group resistance    │
│    → data/resistance/{group}_*.npy      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 3. Generate flow vectors                │
│    Density gradient + climate shift +   │
│    resistance steering → u, v, mag      │
│    → web/data/output/{species}_flow.json│
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 4. Visualise (browser)                  │
│    Mapbox GL JS + Canvas particle trails│
│    30 colour-coded species, interactive │
└─────────────────────────────────────────┘
```

## 8. Limitations

- **Synthetic terrain**: The resistance model uses known geographic features rather than satellite-derived elevation and land cover. This is a reasonable approximation for continental-scale flows but misses local detail.
- **Static climate vector**: A single constant poleward shift is applied per group rather than spatially varying climate velocity derived from General Circulation Model output.
- **No dispersal constraints**: The flow model does not enforce species-specific maximum dispersal distances or generation times.
- **Occurrence bias**: ALA records are biased toward populated coastal regions; the broad Gaussian smoothing partially compensates but interior flows remain sparse for many species.
- **No temporal dynamics**: The visualisation shows a single time-integrated direction, not a sequence of projected future distributions.

## 9. Software and Dependencies

| Component | Version / Source |
|-----------|-----------------|
| Python | 3.14 |
| NumPy | ≥ 1.21 |
| SciPy | ≥ 1.7 |
| Requests | ≥ 2.26 |
| Galah (ALA API) | ≥ 0.12 |
| Mapbox GL JS | 2.15.0 (CDN) |
| HTML5 Canvas | Browser-native |

## References

Atlas of Living Australia (2024) *Atlas of Living Australia*. Available at: https://www.ala.org.au/ (Accessed: 9 March 2026).

Galah Development Team (2024) *galah-python: Atlas of Living Australia data in Python*. Available at: https://galah.ala.org.au/Python/ (Accessed: 9 March 2026).

Jones, M.C., Marron, J.S. and Sheather, S.J. (1996) 'A brief survey of bandwidth selection for density estimation', *Journal of the American Statistical Association*, 91(433), pp. 401–407. doi:10.1080/01621459.1996.10476701.

Lawler, J.J., Ruesch, A.S., Olden, J.D. and McRae, B.H. (2013) 'Projected climate-driven faunal movement routes', *Ecology Letters*, 16(8), pp. 1014–1022. doi:10.1111/ele.12132.

McRae, B.H., Dickson, B.G., Keitt, T.H. and Shah, V.B. (2008) 'Using circuit theory to model connectivity in ecology, evolution, and conservation', *Ecology*, 89(10), pp. 2712–2724. doi:10.1890/07-1861.1.

Mapbox (2024) *Mapbox GL JS*. Available at: https://docs.mapbox.com/mapbox-gl-js/ (Accessed: 9 March 2026).

Shimrat, M. (1962) 'Algorithm 112: Position of point relative to polygon', *Communications of the ACM*, 5(8), p. 434. doi:10.1145/368637.368653.

Wikimedia Foundation (2024) *Wikipedia REST API*. Available at: https://en.wikipedia.org/api/rest_v1/ (Accessed: 9 March 2026).
