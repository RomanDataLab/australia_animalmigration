// Flow field visualization — per-species particle trails on Mapbox GL JS

class FlowVisualization {
    constructor(map) {
        this.map = map;
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.flowData = null;           // Fallback (first loaded)
        this.flowDataByGroup = {};      // Aggregated group flows
        this.flowDataBySpecies = {};    // Per-species flows
        this.animationFrame = null;
        this.pixelRatio = 1;
        this.manifest = null;

        // Active state
        this.activeGroups = { mammals: true, birds: true, amphibians: true };
        this.activeSpecies = {};        // speciesKey -> boolean

        // Color palettes — 10 shades per group
        this.speciesColors = {};        // speciesKey -> 'rgba(r,g,b,'
        this._buildColorPalettes();

        this.params = {
            particleDensity: 1.0,
            particleSpeed: 1.0,
            lineWidth: 1.8,
            opacity: 0.85,
            particleCount: 4500,
            trailLength: 30
        };

        this.australiaBounds = {
            minx: 113.0, miny: -44.0,
            maxx: 154.0, maxy: -10.0
        };
        this.australiaPolygons = [];
        this._loggedOnce = false;

        this.init();
    }

    // ─── Color palettes ──────────────────────────────────────────

    _buildColorPalettes() {
        // 10 distinct shades per group, ordered for maximum contrast
        this._groupPalettes = {
            mammals: [
                [255, 87, 87],    // Bright red
                [255,140, 66],    // Orange
                [230, 57, 70],    // Crimson
                [255,107,129],    // Pink-red
                [204, 51, 51],    // Dark red
                [255,166,  0],    // Amber
                [183, 28, 28],    // Deep red
                [255,138,101],    // Salmon
                [244, 67, 54],    // Material red
                [211, 47, 47],    // Red-brown
            ],
            birds: [
                [ 77,171,247],    // Sky blue
                [ 41,121,255],    // Royal blue
                [100,181,246],    // Light blue
                [ 30, 90,255],    // Vivid blue
                [  0,176,255],    // Cyan-blue
                [ 92,107,192],    // Indigo
                [ 25,118,210],    // Strong blue
                [  3,169,244],    // Light blue vivid
                [121,134,203],    // Lavender blue
                [ 63, 81,181],    // Indigo dark
            ],
            amphibians: [
                [ 81,207,102],    // Bright green
                [ 76,175, 80],    // Material green
                [102,187,106],    // Light green
                [  0,200, 83],    // Vivid green
                [ 46,125, 50],    // Dark green
                [139,195, 74],    // Lime
                [ 56,142, 60],    // Forest green
                [129,199,132],    // Pale green
                [104,159, 56],    // Olive green
                [  0,150,136],    // Teal
            ]
        };
    }

    _assignSpeciesColor(speciesName, group, index) {
        const pal = this._groupPalettes[group];
        if (!pal) return 'rgba(128,128,128,';
        const [r, g, b] = pal[index % pal.length];
        const key = speciesName.replace(/ /g, '_');
        this.speciesColors[key] = `rgba(${r},${g},${b},`;
        return this.speciesColors[key];
    }

    _getSpeciesColorSolid(speciesKey) {
        const base = this.speciesColors[speciesKey];
        if (!base) return '#888';
        return base + '1)';
    }

    // ─── Projection helper (CSS → canvas device pixels) ──────────

    _project(lon, lat) {
        const pt = this.map.project([lon, lat]);
        return { x: pt.x * this.pixelRatio, y: pt.y * this.pixelRatio };
    }

    // ─── Initialization ──────────────────────────────────────────

    init() {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'flow-canvas';
        this.canvas.style.position = 'absolute';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.zIndex = '1';
        this.canvas.style.background = 'transparent';

        const container = this.map.getContainer();
        if (!container) return;

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                container.appendChild(this.canvas);
                this.ctx = this.canvas.getContext('2d');
                if (!this.ctx) return;

                this.resize();
                this.map.on('resize', () => this.resize());
                this.map.on('moveend', () => this._reprojectTrails());
                this.map.on('zoomend', () => this._reprojectTrails());

                this.loadData();
            });
        });
    }

    resize() {
        if (!this.canvas || !this.map) return;
        const container = this.map.getContainer();
        const mc = container.querySelector('canvas.mapboxgl-canvas');
        if (!mc) return;

        const w = mc.width, h = mc.height;
        if (w <= 0 || h <= 0) return;

        this.canvas.width = w;
        this.canvas.height = h;
        const cssW = mc.style.width || mc.getBoundingClientRect().width + 'px';
        const cssH = mc.style.height || mc.getBoundingClientRect().height + 'px';
        this.canvas.style.width = cssW;
        this.canvas.style.height = cssH;
        this.canvas.style.left = mc.style.left || '0';
        this.canvas.style.top = mc.style.top || '0';

        this.pixelRatio = w / (parseFloat(cssW) || container.offsetWidth || 1);
    }

    // ─── GeoJSON ──────────────────────────────────────────────────

    async loadGeoJSON() {
        for (const path of ['data/geojson/australia.geojson', '../data/geojson/australia.geojson']) {
            try {
                const resp = await fetch(path + '?v=' + Date.now());
                if (!resp.ok) continue;
                const geo = await resp.json();

                this.australiaPolygons = [];
                const extract = (coords, type) => {
                    if (type === 'Polygon') this.australiaPolygons.push(coords[0]);
                    else if (type === 'MultiPolygon')
                        for (const p of coords) this.australiaPolygons.push(p[0]);
                };
                if (geo.type === 'FeatureCollection')
                    for (const f of geo.features)
                        extract(f.geometry.coordinates, f.geometry.type);

                let mnLon=Infinity,mxLon=-Infinity,mnLat=Infinity,mxLat=-Infinity;
                for (const ring of this.australiaPolygons)
                    for (const [lon,lat] of ring) {
                        if (lon<mnLon) mnLon=lon; if (lon>mxLon) mxLon=lon;
                        if (lat<mnLat) mnLat=lat; if (lat>mxLat) mxLat=lat;
                    }
                if (isFinite(mnLon)) this.australiaBounds = {
                    minx:mnLon-0.1, miny:mnLat-0.1, maxx:mxLon+0.1, maxy:mxLat+0.1
                };

                // Subtle boundary layer
                this._addBoundaryLayer(geo);
                return true;
            } catch (e) { continue; }
        }
        return false;
    }

    _addBoundaryLayer(geo) {
        const add = () => {
            try {
                if (this.map.getSource('au-boundary')) {
                    if (this.map.getLayer('au-boundary-line')) this.map.removeLayer('au-boundary-line');
                    this.map.removeSource('au-boundary');
                }
                this.map.addSource('au-boundary', { type: 'geojson', data: geo });
                this.map.addLayer({
                    id: 'au-boundary-line', type: 'line', source: 'au-boundary',
                    paint: { 'line-color': '#888', 'line-width': 1, 'line-opacity': 0.3 }
                });
            } catch (e) {
                if (e.message?.includes('Style is not done loading')) setTimeout(add, 300);
            }
        };
        if (this.map.loaded()) add(); else this.map.once('load', add);
    }

    _pointInPolygon(lon, lat, ring) {
        let inside = false;
        for (let i=0, j=ring.length-1; i<ring.length; j=i++) {
            const xi=ring[i][0], yi=ring[i][1], xj=ring[j][0], yj=ring[j][1];
            if (((yi>lat)!==(yj>lat)) && (lon<(xj-xi)*(lat-yi)/(yj-yi)+xi))
                inside=!inside;
        }
        return inside;
    }

    isOnLand(lon, lat) {
        const b = this.australiaBounds;
        if (lon<b.minx || lon>b.maxx || lat<b.miny || lat>b.maxy) return false;
        if (this.australiaPolygons.length > 0) {
            for (const ring of this.australiaPolygons)
                if (this._pointInPolygon(lon, lat, ring)) return true;
            return false;
        }
        return true;
    }

    // ─── Data loading ─────────────────────────────────────────────

    async loadData() {
        await this.loadGeoJSON();

        // Load manifest
        let manifest = null;
        for (const base of ['data/output/', '../data/output/']) {
            try {
                const resp = await fetch(base + 'species_manifest.json?v=' + Date.now());
                if (resp.ok) { manifest = await resp.json(); break; }
            } catch (e) { continue; }
        }

        if (manifest && manifest.groups) {
            this.manifest = manifest;
            await this._loadPerSpeciesFlows(manifest);
        }

        // Also load aggregated group flows (fallback + used for group-level toggle)
        for (const group of ['mammals', 'birds', 'amphibians']) {
            for (const base of ['data/output/', '../data/output/']) {
                try {
                    const resp = await fetch(base + group + '_aggregated_flow.json?v=' + Date.now());
                    if (!resp.ok) continue;
                    this.flowDataByGroup[group] = await resp.json();
                    break;
                } catch (e) { continue; }
            }
        }

        this.flowData = this.flowDataByGroup['mammals'] ||
                         this.flowDataByGroup['birds'] ||
                         this.flowDataByGroup['amphibians'] || null;

        // Build sidebar UI
        this._buildSidebar();

        if (this.flowData || Object.keys(this.flowDataBySpecies).length > 0) {
            this._createParticles();
            this.animate();
            console.log(`Loaded ${Object.keys(this.flowDataBySpecies).length} species flows`);
        } else {
            console.error('No flow data found!');
        }
    }

    async _loadPerSpeciesFlows(manifest) {
        const promises = [];
        for (const [group, speciesList] of Object.entries(manifest.groups)) {
            speciesList.forEach((sp, idx) => {
                const key = sp.scientific.replace(/ /g, '_');
                this.activeSpecies[key] = true;
                this._assignSpeciesColor(sp.scientific, group, idx);

                promises.push((async () => {
                    for (const base of ['data/output/', '../data/output/']) {
                        try {
                            const resp = await fetch(base + sp.file + '?v=' + Date.now());
                            if (!resp.ok) continue;
                            const data = await resp.json();
                            data._group = group;
                            data._speciesKey = key;
                            this.flowDataBySpecies[key] = data;
                            return;
                        } catch (e) { continue; }
                    }
                })());
            });
        }
        await Promise.all(promises);
    }

    // ─── Sidebar UI ───────────────────────────────────────────────

    _buildSidebar() {
        if (!this.manifest) return;

        for (const [group, speciesList] of Object.entries(this.manifest.groups)) {
            const listEl = document.getElementById(group + '-list');
            if (!listEl) continue;

            for (const sp of speciesList) {
                const key = sp.scientific.replace(/ /g, '_');
                const color = this._getSpeciesColorSolid(key);
                const wikiUrl = `https://en.wikipedia.org/wiki/${sp.wiki}`;

                const tile = document.createElement('div');
                tile.className = 'species-tile';
                tile.dataset.species = key;
                tile.style.color = color;

                // Tooltip
                tile.innerHTML =
                    `<img src="" alt="${sp.common}" loading="lazy">` +
                    `<span class="species-border"></span>` +
                    `<span class="species-tooltip">` +
                        `<span class="tt-common">${sp.common}</span><br>` +
                        `<span class="tt-sci">${sp.scientific}</span><br>` +
                        `<span class="tt-hint">double click — see article</span>` +
                    `</span>`;

                // Fetch Wikipedia thumbnail
                this._fetchWikiThumb(sp.wiki, tile.querySelector('img'));

                // Click handling: single = toggle, double = open Wikipedia
                let clickTimer = null;
                tile.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; return; }
                    clickTimer = setTimeout(() => {
                        clickTimer = null;
                        tile.classList.toggle('inactive');
                        this.activeSpecies[key] = !tile.classList.contains('inactive');
                        this._createParticles();
                    }, 250);
                });

                tile.addEventListener('dblclick', (e) => {
                    e.preventDefault();
                    if (clickTimer) { clearTimeout(clickTimer); clickTimer = null; }
                    window.open(wikiUrl, '_blank');
                });

                listEl.appendChild(tile);
            }
        }

        // Group toggles (header checkbox)
        document.querySelectorAll('[data-group-toggle]').forEach(cb => {
            const group = cb.dataset.groupToggle;
            cb.addEventListener('change', (e) => {
                this.activeGroups[group] = e.target.checked;
                const list = document.getElementById(group + '-list');
                if (list) {
                    list.querySelectorAll('.species-tile').forEach(tile => {
                        const key = tile.dataset.species;
                        if (e.target.checked) {
                            tile.classList.remove('inactive');
                            if (key) this.activeSpecies[key] = true;
                        } else {
                            tile.classList.add('inactive');
                            if (key) this.activeSpecies[key] = false;
                        }
                    });
                }
                this._createParticles();
            });
        });

        // Collapsible group sections
        document.querySelectorAll('.group-header').forEach(header => {
            header.addEventListener('click', (e) => {
                if (e.target.tagName === 'INPUT') return;
                const section = header.closest('.group-section');
                section.classList.toggle('collapsed');
            });
        });

        // Advanced controls toggle
        const showCtrl = document.getElementById('show-controls');
        if (showCtrl) {
            showCtrl.addEventListener('change', (e) => {
                document.getElementById('advanced-controls').style.display =
                    e.target.checked ? 'block' : 'none';
            });
        }

        // Slider controls
        const bind = (id, valId, fn) => {
            const el = document.getElementById(id);
            const val = document.getElementById(valId);
            if (el && val) el.addEventListener('input', (e) => {
                const v = parseFloat(e.target.value);
                val.textContent = v.toFixed(1);
                fn(v);
            });
        };
        bind('particle-density', 'density-value', v => this.setParticleDensity(v));
        bind('particle-speed', 'speed-value', v => this.setParticleSpeed(v));
        bind('line-width', 'width-value', v => this.setLineWidth(v));
        bind('opacity', 'opacity-value', v => this.setOpacity(v));
    }

    async _fetchWikiThumb(wikiSlug, imgEl) {
        try {
            // Decode first to avoid double-encoding (e.g. %27 → %2527)
            const decoded = decodeURIComponent(wikiSlug);
            const resp = await fetch(
                `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(decoded)}`
            );
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.thumbnail && data.thumbnail.source) {
                imgEl.src = data.thumbnail.source;
            } else if (data.originalimage && data.originalimage.source) {
                imgEl.src = data.originalimage.source;
            }
        } catch (e) {
            // Leave default grey background
        }
    }

    // ─── Flow vector lookup ───────────────────────────────────────

    getFlowVector(lon, lat, speciesKey) {
        const data = this.flowDataBySpecies[speciesKey] ||
                     this.flowDataByGroup[this.flowDataBySpecies[speciesKey]?._group] ||
                     this.flowData;
        if (!data || !data.u) return { u: 0, v: 0, magnitude: 0 };

        const { bounds } = data;
        const xR = data.x_resolution || data.resolution;
        const yR = data.y_resolution || data.resolution;

        const x = (lon - bounds.minx) / xR;
        const y = (bounds.maxy - lat) / yR;
        const mxY = data.u.length - 1;
        const mxX = data.u[0] ? data.u[0].length - 1 : 0;

        if (x < 0 || y < 0 || x > mxX || y > mxY) return { u:0, v:0, magnitude:0 };

        const x0 = Math.floor(x), y0 = Math.floor(y);
        const x1 = Math.min(x0+1, mxX), y1 = Math.min(y0+1, mxY);
        const fx = x - x0, fy = y - y0;
        const g = (a,r,c) => (a[r] && a[r][c]) || 0;

        return {
            u:   (1-fx)*(1-fy)*g(data.u,y0,x0) + fx*(1-fy)*g(data.u,y0,x1) +
                 (1-fx)*fy*g(data.u,y1,x0)     + fx*fy*g(data.u,y1,x1),
            v:   (1-fx)*(1-fy)*g(data.v,y0,x0) + fx*(1-fy)*g(data.v,y0,x1) +
                 (1-fx)*fy*g(data.v,y1,x0)     + fx*fy*g(data.v,y1,x1),
            magnitude:
                 (1-fx)*(1-fy)*g(data.magnitude,y0,x0) + fx*(1-fy)*g(data.magnitude,y0,x1) +
                 (1-fx)*fy*g(data.magnitude,y1,x0)     + fx*fy*g(data.magnitude,y1,x1)
        };
    }

    // ─── Particle management ──────────────────────────────────────

    _getRandomLandPoint(maxAttempts = 50) {
        const b = this.australiaBounds;
        for (let i = 0; i < maxAttempts; i++) {
            const lon = b.minx + Math.random() * (b.maxx - b.minx);
            const lat = b.miny + Math.random() * (b.maxy - b.miny);
            if (this.isOnLand(lon, lat)) return { lon, lat };
        }
        return { lon: 133+(Math.random()-0.5)*10, lat: -25+(Math.random()-0.5)*8 };
    }

    _getActiveSpeciesKeys() {
        return Object.keys(this.activeSpecies).filter(k => {
            if (!this.activeSpecies[k]) return false;
            const data = this.flowDataBySpecies[k];
            if (!data) return false;
            const group = data._group;
            return group && this.activeGroups[group];
        });
    }

    _createParticles() {
        const count = Math.floor(this.params.particleCount * this.params.particleDensity);
        const activeKeys = this._getActiveSpeciesKeys();
        if (activeKeys.length === 0) { this.particles = []; return; }

        this.particles = [];
        let attempts = 0;
        const maxAttempts = count * 4;

        while (this.particles.length < count && attempts++ < maxAttempts) {
            const pt = this._getRandomLandPoint(15);
            // Round-robin species assignment
            const speciesKey = activeKeys[this.particles.length % activeKeys.length];

            const flow = this.getFlowVector(pt.lon, pt.lat, speciesKey);
            if (flow.magnitude < 0.01) continue;

            const proj = this._project(pt.lon, pt.lat);
            this.particles.push({
                lon: pt.lon, lat: pt.lat,
                x: proj.x, y: proj.y,
                species: speciesKey,
                age: Math.floor(Math.random() * this.params.trailLength),
                maxAge: this.params.trailLength + Math.floor(Math.random() * this.params.trailLength),
                trail: []
            });
        }
        console.log(`Created ${this.particles.length} particles for ${activeKeys.length} species`);
    }

    _reprojectTrails() {
        for (const p of this.particles) {
            try { const pt = this._project(p.lon, p.lat); p.x = pt.x; p.y = pt.y; }
            catch (e) { /* skip */ }
            p.trail = [];
        }
    }

    _resetParticle(p) {
        const pt = this._getRandomLandPoint(15);
        p.lon = pt.lon; p.lat = pt.lat;
        try { const proj = this._project(p.lon, p.lat); p.x = proj.x; p.y = proj.y; }
        catch (e) { /* skip */ }
        p.age = 0; p.trail = [];
    }

    // ─── Animation ────────────────────────────────────────────────

    animate() {
        if (!this.ctx || !this.canvas) {
            this.animationFrame = requestAnimationFrame(() => this.animate());
            return;
        }

        const w = this.canvas.width, h = this.canvas.height;
        if (w === 0 || h === 0) this.resize();

        this.ctx.clearRect(0, 0, w, h);
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        const scaledWidth = this.params.lineWidth * this.pixelRatio;
        let drawn = 0;

        for (const p of this.particles) {
            const sk = p.species;

            // Check species+group still active
            if (!this.activeSpecies[sk]) continue;
            const data = this.flowDataBySpecies[sk];
            if (!data || !this.activeGroups[data._group]) continue;

            const flow = this.getFlowVector(p.lon, p.lat, sk);

            if (flow.magnitude > 0.01) {
                const res = data.resolution || 0.25;
                const step = Math.max(0.04, Math.min(0.15, res * 0.5)) * this.params.particleSpeed;

                const newLon = p.lon + flow.u * step;
                const newLat = p.lat + flow.v * step;

                if (this.isOnLand(newLon, newLat)) {
                    p.trail.push({ x: p.x, y: p.y });
                    if (p.trail.length > this.params.trailLength) p.trail.shift();

                    p.lon = newLon;
                    p.lat = newLat;
                    try {
                        const proj = this._project(p.lon, p.lat);
                        p.x = proj.x; p.y = proj.y;
                    } catch (e) { this._resetParticle(p); continue; }

                    // Draw trail
                    if (p.trail.length >= 2) {
                        const color = this.speciesColors[sk] || 'rgba(128,128,128,';
                        const len = p.trail.length;

                        for (let i = 1; i < len; i++) {
                            const t = i / len;
                            const alpha = t * t * this.params.opacity;
                            this.ctx.beginPath();
                            this.ctx.strokeStyle = color + alpha.toFixed(3) + ')';
                            this.ctx.lineWidth = scaledWidth * (0.3 + 0.7 * t);
                            this.ctx.moveTo(p.trail[i-1].x, p.trail[i-1].y);
                            this.ctx.lineTo(p.trail[i].x, p.trail[i].y);
                            this.ctx.stroke();
                        }

                        // Head segment
                        const last = p.trail[len-1];
                        this.ctx.beginPath();
                        this.ctx.strokeStyle = color + this.params.opacity.toFixed(3) + ')';
                        this.ctx.lineWidth = scaledWidth;
                        this.ctx.moveTo(last.x, last.y);
                        this.ctx.lineTo(p.x, p.y);
                        this.ctx.stroke();

                        drawn++;
                    }
                    p.age++;
                } else {
                    this._resetParticle(p);
                }
            } else {
                p.age += 3;
            }

            if (p.age > p.maxAge) this._resetParticle(p);
        }

        if (!this._loggedOnce) {
            console.log(`Animating: ${drawn} trails, ${Object.keys(this.speciesColors).length} species colors`);
            this._loggedOnce = true;
        }

        this.animationFrame = requestAnimationFrame(() => this.animate());
    }

    // ─── Public controls ──────────────────────────────────────────

    setParticleDensity(v) { this.params.particleDensity = v; this._createParticles(); }
    setParticleSpeed(v)   { this.params.particleSpeed = v; }
    setLineWidth(v)       { this.params.lineWidth = v; }
    setOpacity(v)         { this.params.opacity = v; }
}

// ─── Global interface ─────────────────────────────────────────────

let flowViz = null;

function initFlowVisualization(map) {
    if (!map) { console.error('Map is null'); return; }
    flowViz = new FlowVisualization(map);
}

function toggleSpeciesGroup(group, enabled) {
    // Legacy — now handled internally via sidebar
    if (flowViz) {
        flowViz.activeGroups[group] = enabled;
        flowViz._createParticles();
    }
}

function setParticleDensity(v) { if (flowViz) flowViz.setParticleDensity(v); }
function setParticleSpeed(v)   { if (flowViz) flowViz.setParticleSpeed(v); }
function setLineWidth(v)       { if (flowViz) flowViz.setLineWidth(v); }
function setOpacity(v)         { if (flowViz) flowViz.setOpacity(v); }
