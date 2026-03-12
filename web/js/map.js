// Mapbox initialization and setup

// Wait for Mapbox library to load
function waitForMapbox(callback) {
    if (typeof mapboxgl !== 'undefined') {
        console.log('Mapbox GL JS is available');
        callback();
    } else {
        console.log('Waiting for Mapbox GL JS to load...');
        setTimeout(() => waitForMapbox(callback), 100);
    }
}

// Initialize when both Mapbox and DOM are ready
waitForMapbox(async () => {
    console.log('Mapbox GL JS loaded, setting up map...');
    
    // Mapbox access token
    let mapboxToken = null;
    let mapboxStyle = 'mapbox://styles/mapbox/dark-v11'; // Default style

    // Try to get from config file first
    if (window.MAPBOX_CONFIG) {
        mapboxToken = window.MAPBOX_CONFIG.accessToken;
        if (window.MAPBOX_CONFIG.style) {
            mapboxStyle = window.MAPBOX_CONFIG.style;
        }
    }

    // Fallback: Try to get token from URL parameter (for testing)
    if (!mapboxToken) {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('token')) {
            mapboxToken = urlParams.get('token');
        }
    }

    // Fallback: Try to get from window config (if set by server)
    if (!mapboxToken && window.MAPBOX_TOKEN) {
        mapboxToken = window.MAPBOX_TOKEN;
    }

    // Fallback for Vercel/static deploys: fetch token from serverless API.
    if (!mapboxToken) {
        try {
            const resp = await fetch('/api/mapbox-token', { cache: 'no-store' });
            if (resp.ok) {
                const payload = await resp.json();
                if (payload && payload.token) {
                    mapboxToken = payload.token;
                }
                if (payload && payload.style) {
                    mapboxStyle = payload.style;
                }
            }
        } catch (e) {
            console.warn('Could not load token from /api/mapbox-token');
        }
    }

    if (!mapboxToken) {
        console.error('Mapbox token not found! Please set it in web/js/config.js');
        alert('Mapbox token not found! Please check web/js/config.js');
        mapboxToken = 'YOUR_MAPBOX_ACCESS_TOKEN'; // Fallback to prevent errors
    } else {
        console.log('Mapbox token loaded from config:', mapboxToken.substring(0, 20) + '...');
    }

    mapboxgl.accessToken = mapboxToken;

    // Wait for DOM to be ready before initializing map
    let map = null;

    // ─── Move / Stop mode buttons ─────────────────────────────
    function setupModeButtons(mapRef) {
        const btnMove = document.getElementById('btn-move');
        const btnStop = document.getElementById('btn-stop');
        if (!btnMove || !btnStop || !mapRef) return;

        function enableMapInteraction() {
            mapRef.scrollZoom.enable();
            mapRef.boxZoom.enable();
            mapRef.dragPan.enable();
            mapRef.keyboard.enable();
            mapRef.doubleClickZoom.enable();
            mapRef.touchZoomRotate.enable();
        }

        function disableMapInteraction() {
            mapRef.scrollZoom.disable();
            mapRef.boxZoom.disable();
            mapRef.dragPan.disable();
            mapRef.keyboard.disable();
            mapRef.doubleClickZoom.disable();
            mapRef.touchZoomRotate.disable();
        }

        btnMove.addEventListener('click', () => {
            btnMove.classList.add('active');
            btnStop.classList.remove('active');
            enableMapInteraction();
            // Hide flows during navigation
            const flowCanvas = document.getElementById('flow-canvas');
            if (flowCanvas) flowCanvas.style.display = 'none';
        });

        btnStop.addEventListener('click', () => {
            btnStop.classList.add('active');
            btnMove.classList.remove('active');
            disableMapInteraction();
            // Show flows
            const flowCanvas = document.getElementById('flow-canvas');
            if (flowCanvas) flowCanvas.style.display = '';
            // Resize flow canvas to match current map state
            if (typeof flowViz !== 'undefined' && flowViz) {
                flowViz.resize();
                flowViz._reprojectTrails();
            }
        });

        // Start in Stop mode (interactions disabled)
        disableMapInteraction();
    }

    // Initialize map when DOM is ready
    function initMap() {
        console.log('Initializing map...');
        // Ensure map container exists and has dimensions
        const mapContainer = document.getElementById('map');
        if (!mapContainer) {
            console.error('Map container not found!');
            return;
        }
        
        console.log('Map container found:', {
            width: mapContainer.offsetWidth,
            height: mapContainer.offsetHeight,
            computedStyle: window.getComputedStyle(mapContainer).display
        });
        
        // Set minimum dimensions if not set
        if (mapContainer.offsetWidth === 0 || mapContainer.offsetHeight === 0) {
            mapContainer.style.width = '100%';
            mapContainer.style.height = '100vh';
            console.log('Set map container dimensions');
        }
        
        try {
            // Initialize map centered on Australia with flat Mercator projection
            // Using EPSG:3857 (Web Mercator) - same as Mapbox GL default
            // Explicitly disable globe mode and set to flat 2D view
            map = new mapboxgl.Map({
                container: 'map',
                style: mapboxStyle, // Style from config (or default light style)
                center: [134.0, -28.0], // Center of Australia (includes Tasmania)
                zoom: 3.8,
                minZoom: 3,
                maxZoom: 10,
                // Use Mercator projection (EPSG:3857) for flat map - explicitly disable globe
                projection: 'mercator',
                // Disable 3D/globe view - force flat 2D
                pitch: 0,        // No pitch (flat view)
                bearing: 0,      // No rotation
                // Disable interactive rotation and pitch
                dragRotate: false,
                touchPitch: false,
                touchZoomRotate: false,
                // Interactions will be disabled after load (Stop mode default)
            });
            
            console.log('Map initialized with flat Mercator projection (EPSG:3857) - 2D view');
            
            console.log('Map object created');
            
            // Export map instance for use in other scripts
            window.mapInstance = map;

            // Disable all interactions immediately (Stop mode is default)
            map.scrollZoom.disable();
            map.boxZoom.disable();
            map.dragPan.disable();
            map.keyboard.disable();
            map.doubleClickZoom.disable();
        } catch (error) {
            console.error('Error initializing map:', error);
            alert('Error initializing map: ' + error.message);
            return;
        }
        
        // Add navigation controls
        map.addControl(new mapboxgl.NavigationControl(), 'top-right');
        
        // Add scale control
        map.addControl(new mapboxgl.ScaleControl({
            maxWidth: 100,
            unit: 'metric'
        }), 'bottom-right');
        
        // Wait for map to load before initializing flow visualization
        map.on('load', () => {
            console.log('Map loaded successfully');
            console.log('Map container dimensions:', {
                width: map.getContainer().offsetWidth,
                height: map.getContainer().offsetHeight
            });
            
            // Force flat 2D view - disable any globe/3D mode
            map.setPitch(0);
            map.setBearing(0);
            
            // Disable interactive rotation and pitch
            map.dragRotate.disable();
            map.touchZoomRotate.disableRotation();
            map.touchPitch.disable();
            
            // Ensure projection is set to mercator (flat) - disable globe
            try {
                // Check current projection
                const currentProjection = map.getProjection ? map.getProjection() : null;
                console.log('Current projection:', currentProjection);
                
                // Force mercator projection
                if (map.setProjection) {
                    map.setProjection('mercator');
                    console.log('Projection set to mercator (flat)');
                }
            } catch (e) {
                console.warn('Could not set projection:', e);
            }
            
            // Disable globe mode in style if it exists
            try {
                const style = map.getStyle();
                if (style) {
                    // Check if style has globe projection
                    if (style.projection && style.projection.name === 'globe') {
                        map.setProjection('mercator');
                        console.log('Globe mode disabled in style, switched to mercator');
                    }
                    
                    // Force remove globe projection from style if present
                    // Some Mapbox styles have globe enabled by default
                    if (style.projection) {
                        console.log('Style projection:', style.projection);
                        // Remove globe projection
                        map.setProjection('mercator');
                    }
                }
            } catch (e) {
                console.warn('Error checking style:', e);
            }
            
            // Additional check: ensure projection is mercator after a short delay
            // This handles cases where the style loads globe mode after initial load
            setTimeout(() => {
                try {
                    const currentProj = map.getProjection ? map.getProjection() : null;
                    if (currentProj && currentProj.name === 'globe') {
                        console.log('Globe detected, forcing mercator projection');
                        map.setProjection('mercator');
                        map.setPitch(0);
                        map.setBearing(0);
                    }
                } catch (e) {
                    // Ignore
                }
            }, 500);
            
            // Ensure map is visible and properly sized
            map.resize();
            
            // Force a repaint to ensure map is fully rendered
            setTimeout(() => {
                map.resize();
                console.log('Map resized after load');
                
                // Wait a bit longer to ensure map is fully rendered before adding overlay
                setTimeout(() => {
                    console.log('Checking for initFlowVisualization function...');
                    if (typeof initFlowVisualization === 'function') {
                        console.log('Initializing flow visualization...');
                        initFlowVisualization(map);
                    } else {
                        console.warn('initFlowVisualization function not found. Make sure flow.js is loaded.');
                        // Try again after a delay in case scripts are still loading
                        setTimeout(() => {
                            if (typeof initFlowVisualization === 'function') {
                                console.log('Retrying flow visualization initialization...');
                                initFlowVisualization(map);
                            }
                        }, 1000);
                    }

                    // Setup Move/Stop mode buttons
                    setupModeButtons(map);
                }, 500); // Wait for map to fully render
            }, 100);
        });
        
        // Handle map errors
        map.on('error', (e) => {
            console.error('Map error:', e);
            if (e.error && e.error.message) {
                console.error('Map error message:', e.error.message);
                // Don't show alert for style loading errors that might be temporary
                if (!e.error.message.includes('style')) {
                    alert('Map error: ' + e.error.message);
                }
            }
        });
        
        // Also handle style load to ensure map renders
        map.on('style.load', () => {
            console.log('Map style loaded, forcing resize...');
            
            // Force flat projection when style loads (in case style enables globe)
            try {
                map.setProjection('mercator');
                map.setPitch(0);
                map.setBearing(0);
                console.log('Forced flat projection on style load');
            } catch (e) {
                console.warn('Error setting projection on style load:', e);
            }
            
            // Ensure map is visible and properly rendered
            map.resize();
            
            // Force a repaint to ensure map background stays visible
            setTimeout(() => {
                map.triggerRepaint();
            }, 100);
        });
        
        // Handle map movement to ensure background stays visible
        map.on('move', () => {
            // Ensure map continues to render during movement
            map.triggerRepaint();
        });
        
        map.on('moveend', () => {
            // Force repaint after movement ends
            map.triggerRepaint();
        });
        
        // Handle render to ensure map is visible
        map.on('render', () => {
            // Map is rendering
        });
    }

    // Initialize map when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMap);
    } else {
        // DOM is already ready
        initMap();
    }
    
    // UI event listeners are now handled by flow.js _buildSidebar()
});
