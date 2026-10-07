/**
 * ARCHAEO-SCAN Atlas — Main Application
 *
 * Initializes MapLibre GL JS, manages layers, wires up all panels,
 * and orchestrates the full interactive map experience.
 */

import { loadAllDemoData, scoreToColor, scoreToHex, DEMO_SITES } from './demo.js';
import { Timeline } from './timeline.js';
import { Inspector } from './inspector.js';
import { escapeHtml, unitScore } from './safe_html.js';

const h3 = window.h3;

// ============================================================
// Configuration
// ============================================================

const BASE_LAYERS = {
    dark: {
        tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png'],
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/">OSM</a>',
    },
    satellite: {
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
        attribution: '&copy; Esri',
    },
    topo: {
        tiles: ['https://a.tile.opentopomap.org/{z}/{x}/{y}.png'],
        attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> &copy; OSM',
    },
    terrain: {
        tiles: ['https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}@2x.png'],
        attribution: '&copy; <a href="https://stadiamaps.com/">Stadia</a> &copy; <a href="https://stamen.com/">Stamen</a>',
    },
};

const US_CENTER = [-98.5795, 39.8283]; // [lon, lat] for MapLibre
const DEFAULT_ZOOM = 4;

// ============================================================
// App State
// ============================================================

const state = {
    map: null,
    minimap: null,
    timeline: null,
    inspector: null,
    activeBasemap: 'dark',
    activeLayers: new Set(),
    demoLoaded: false,
    demoData: null,
    settings: {
        scoreThreshold: 0,
        preset: 'default',
        resolution: 8,
        animSpeed: 30000,
        colorScheme: 'blue-yellow-red',
        obfuscate: true,
    },
    measuring: null, // null | 'distance' | 'area'
    measurePoints: [],
    contextCoords: null,
};

// ============================================================
// Map Initialization
// ============================================================

function initMap() {
    const basemap = BASE_LAYERS[state.activeBasemap];

    state.map = new maplibregl.Map({
        container: 'map',
        style: {
            version: 8,
            sources: {
                basemap: {
                    type: 'raster',
                    tiles: basemap.tiles,
                    tileSize: 256,
                    attribution: basemap.attribution,
                    maxzoom: 19,
                },
            },
            layers: [
                {
                    id: 'basemap-layer',
                    type: 'raster',
                    source: 'basemap',
                },
            ],
        },
        center: US_CENTER,
        zoom: DEFAULT_ZOOM,
        maxZoom: 18,
        minZoom: 2,
        preserveDrawingBuffer: true, // needed for screenshots
    });

    // Controls
    state.map.addControl(new maplibregl.NavigationControl(), 'top-right');
    state.map.addControl(new maplibregl.ScaleControl({ unit: 'imperial' }), 'bottom-left');

    state.map.on('load', onMapLoad);
    state.map.on('mousemove', onMapMouseMove);
    state.map.on('click', onMapClick);
    state.map.on('contextmenu', onMapContextMenu);
    state.map.on('moveend', onMapMoveEnd);

    // Initialize minimap
    initMinimap();
}

function onMapLoad() {
    // Add empty sources for data layers — populated when demo/API data arrives
    state.map.addSource('scores', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
    });

    state.map.addSource('known-sites', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
    });

    state.map.addSource('historical-refs', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
    });

    // H3 Grid / Scores layer — filled hexagons
    state.map.addLayer({
        id: 'h3-grid-fill',
        type: 'fill',
        source: 'scores',
        paint: {
            'fill-color': [
                'interpolate', ['linear'], ['get', 'composite_score'],
                0.0, '#2563eb',
                0.2, '#3b82f6',
                0.5, '#eab308',
                0.7, '#f97316',
                1.0, '#dc2626',
            ],
            'fill-opacity': 0.6,
        },
        layout: { visibility: 'none' },
    });

    // H3 Grid outlines
    state.map.addLayer({
        id: 'h3-grid-outline',
        type: 'line',
        source: 'scores',
        paint: {
            'line-color': [
                'interpolate', ['linear'], ['get', 'composite_score'],
                0.0, '#2563eb',
                0.5, '#eab308',
                1.0, '#dc2626',
            ],
            'line-width': 1,
            'line-opacity': 0.8,
        },
        layout: { visibility: 'none' },
    });

    // Known sites layer
    state.map.addLayer({
        id: 'known-sites-layer',
        type: 'circle',
        source: 'known-sites',
        paint: {
            'circle-radius': 7,
            'circle-color': '#f59e0b',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#92400e',
        },
        layout: { visibility: 'none' },
    });

    // Known sites labels
    state.map.addLayer({
        id: 'known-sites-labels',
        type: 'symbol',
        source: 'known-sites',
        layout: {
            'text-field': ['get', 'name'],
            'text-size': 11,
            'text-offset': [0, 1.5],
            'text-anchor': 'top',
            visibility: 'none',
        },
        paint: {
            'text-color': '#f59e0b',
            'text-halo-color': '#0d1117',
            'text-halo-width': 1,
        },
    });

    // Historical refs layer
    state.map.addLayer({
        id: 'historical-refs-layer',
        type: 'circle',
        source: 'historical-refs',
        paint: {
            'circle-radius': 6,
            'circle-color': '#a78bfa',
            'circle-stroke-width': 1.5,
            'circle-stroke-color': '#6d28d9',
        },
        layout: { visibility: 'none' },
    });

    // Measure line source/layer
    state.map.addSource('measure', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
    });
    state.map.addLayer({
        id: 'measure-line',
        type: 'line',
        source: 'measure',
        paint: {
            'line-color': '#58a6ff',
            'line-width': 2,
            'line-dasharray': [4, 2],
        },
    });
    state.map.addLayer({
        id: 'measure-points',
        type: 'circle',
        source: 'measure',
        filter: ['==', '$type', 'Point'],
        paint: {
            'circle-radius': 4,
            'circle-color': '#58a6ff',
            'circle-stroke-width': 1,
            'circle-stroke-color': '#fff',
        },
    });

    // Parse URL state
    parseURLState();

    // Update header coords
    onMapMoveEnd();
}

// ============================================================
// Basemap Switching
// ============================================================

function switchBasemap(name) {
    if (!BASE_LAYERS[name]) return;
    state.activeBasemap = name;

    const source = state.map.getSource('basemap');
    if (source) {
        // MapLibre doesn't support changing raster tiles directly,
        // so we remove and re-add the source
        state.map.removeLayer('basemap-layer');
        state.map.removeSource('basemap');

        const basemap = BASE_LAYERS[name];
        state.map.addSource('basemap', {
            type: 'raster',
            tiles: basemap.tiles,
            tileSize: 256,
            attribution: basemap.attribution,
            maxzoom: 19,
        });

        // Re-add basemap layer at the bottom
        const layers = state.map.getStyle().layers;
        const firstDataLayer = layers[0]?.id;
        state.map.addLayer({
            id: 'basemap-layer',
            type: 'raster',
            source: 'basemap',
        }, firstDataLayer);
    }

    updateURLState();
}

// ============================================================
// Layer Visibility
// ============================================================

const LAYER_TO_MAP_LAYERS = {
    'h3-grid': ['h3-grid-fill', 'h3-grid-outline'],
    'known-sites': ['known-sites-layer', 'known-sites-labels'],
    'historical-refs': ['historical-refs-layer'],
    // Placeholder layers — no map layers yet, but track them
    'terrain-anomalies': [],
    'crop-marks': [],
    'soil-anomalies': [],
    'hydrology': [],
    'geology': [],
    'lidar-coverage': [],
    'cave-predictions': [],
    'citizen-reports': [],
    'paleo-coastlines': [],
    'ice-sheets': [],
    'land-ownership': [],
    'survey-status': [],
};

function setLayerVisibility(layerName, visible) {
    const mapLayers = LAYER_TO_MAP_LAYERS[layerName] || [];

    if (visible) {
        state.activeLayers.add(layerName);
    } else {
        state.activeLayers.delete(layerName);
    }

    for (const mlId of mapLayers) {
        if (state.map.getLayer(mlId)) {
            state.map.setLayoutProperty(mlId, 'visibility', visible ? 'visible' : 'none');
        }
    }

    // Show legend when h3-grid is active
    const legend = document.getElementById('legend');
    if (state.activeLayers.has('h3-grid')) {
        legend.classList.remove('hidden');
    } else {
        legend.classList.add('hidden');
    }

    // Update active layer count
    document.getElementById('active-layer-count').textContent =
        `${state.activeLayers.size} layer${state.activeLayers.size !== 1 ? 's' : ''} active`;

    // Activate opacity slider
    const item = document.querySelector(`.layer-item[data-layer="${layerName}"]`);
    if (item) {
        item.classList.toggle('active', visible);
    }

    updateURLState();
}

function setLayerOpacity(layerName, opacity) {
    const mapLayers = LAYER_TO_MAP_LAYERS[layerName] || [];
    for (const mlId of mapLayers) {
        if (state.map.getLayer(mlId)) {
            const layer = state.map.getLayer(mlId);
            if (layer.type === 'fill') {
                state.map.setPaintProperty(mlId, 'fill-opacity', opacity);
            } else if (layer.type === 'line') {
                state.map.setPaintProperty(mlId, 'line-opacity', opacity);
            } else if (layer.type === 'circle') {
                state.map.setPaintProperty(mlId, 'circle-opacity', opacity);
            } else if (layer.type === 'symbol') {
                state.map.setPaintProperty(mlId, 'text-opacity', opacity);
            }
        }
    }
}

// ============================================================
// Demo Data Loading
// ============================================================

function loadDemoData() {
    if (state.demoLoaded) return;

    const btn = document.getElementById('load-demo-btn');
    btn.textContent = 'Loading...';
    btn.disabled = true;

    // Use setTimeout to let the UI update
    setTimeout(() => {
        try {
            state.demoData = loadAllDemoData(state.settings.resolution);

            // Push data into map sources
            state.map.getSource('scores').setData(state.demoData.scores);
            state.map.getSource('known-sites').setData(state.demoData.knownSites);
            state.map.getSource('historical-refs').setData(state.demoData.historicalRefs);

            // Auto-enable key layers
            const checkbox = document.querySelector('input[data-layer="h3-grid"]');
            if (checkbox && !checkbox.checked) {
                checkbox.checked = true;
                setLayerVisibility('h3-grid', true);
            }
            const sitesCheck = document.querySelector('input[data-layer="known-sites"]');
            if (sitesCheck && !sitesCheck.checked) {
                sitesCheck.checked = true;
                setLayerVisibility('known-sites', true);
            }

            state.demoLoaded = true;
            btn.textContent = 'Demo Loaded';

            // No spatial demonstration is bundled in this source-only candidate.
        } catch (e) {
            console.error('Failed to generate demo data:', e);
            btn.textContent = 'Load Demo Data';
            btn.disabled = false;
        }
    }, 50);
}

// ============================================================
// Map Event Handlers
// ============================================================

function onMapMouseMove(e) {
    const { lng, lat } = e.lngLat;

    // Update cursor coordinates
    document.getElementById('cursor-coords').textContent =
        `${lat.toFixed(5)}, ${lng.toFixed(5)}`;

    // Show H3 cell under cursor
    try {
        const cellId = h3.latLngToCell(lat, lng, state.settings.resolution);
        document.getElementById('cursor-h3').textContent = cellId;
    } catch {
        document.getElementById('cursor-h3').textContent = '';
    }

    // Tooltip for scored cells
    const tooltip = document.getElementById('map-tooltip');
    const features = state.map.queryRenderedFeatures(e.point, {
        layers: ['h3-grid-fill'],
    });

    if (features.length > 0) {
        const props = features[0].properties;
        const score = unitScore(props.composite_score);
        let factors = props.contributing_factors;
        if (typeof factors === 'string') {
            try { factors = JSON.parse(factors); } catch { factors = []; }
        }

        tooltip.innerHTML = `
            <div class="tooltip-score" style="color:${scoreToColor(score)}">${(score * 100).toFixed(1)}%</div>
            <div class="tooltip-factors">${Array.isArray(factors) ? factors.slice(0, 2).map(escapeHtml).join('<br>') : ''}</div>
        `;
        tooltip.style.left = (e.originalEvent.clientX + 12) + 'px';
        tooltip.style.top = (e.originalEvent.clientY - 12) + 'px';
        tooltip.classList.remove('hidden');
        state.map.getCanvas().style.cursor = 'pointer';
    } else {
        // Check known sites
        const siteFeatures = state.map.queryRenderedFeatures(e.point, {
            layers: ['known-sites-layer'],
        });
        if (siteFeatures.length > 0) {
            const props = siteFeatures[0].properties;
            tooltip.innerHTML = `
                <div style="color:#f59e0b;font-weight:600">${escapeHtml(props.name)}</div>
                <div class="tooltip-factors">${escapeHtml(props.period)} ${props.type ? '- ' + escapeHtml(props.type) : ''}</div>
            `;
            tooltip.style.left = (e.originalEvent.clientX + 12) + 'px';
            tooltip.style.top = (e.originalEvent.clientY - 12) + 'px';
            tooltip.classList.remove('hidden');
            state.map.getCanvas().style.cursor = 'pointer';
        } else {
            tooltip.classList.add('hidden');
            state.map.getCanvas().style.cursor = state.measuring ? 'crosshair' : '';
        }
    }
}

function onMapClick(e) {
    // If measuring, handle measure click
    if (state.measuring) {
        handleMeasureClick(e);
        return;
    }

    // Check scored cells
    const features = state.map.queryRenderedFeatures(e.point, {
        layers: ['h3-grid-fill'],
    });

    if (features.length > 0) {
        const props = features[0].properties;
        // Parse JSON strings from GeoJSON properties
        let layerScores = props.layer_scores;
        let factors = props.contributing_factors;
        if (typeof layerScores === 'string') {
            try { layerScores = JSON.parse(layerScores); } catch { layerScores = {}; }
        }
        if (typeof factors === 'string') {
            try { factors = JSON.parse(factors); } catch { factors = []; }
        }

        state.inspector.showCell({
            ...props,
            layer_scores: layerScores,
            contributing_factors: factors,
        });
        return;
    }

    // Check known sites
    const siteFeatures = state.map.queryRenderedFeatures(e.point, {
        layers: ['known-sites-layer'],
    });

    if (siteFeatures.length > 0) {
        state.inspector.showKnownSite(siteFeatures[0].properties);
        return;
    }

    // Click on empty area — hide context menu
    document.getElementById('context-menu').classList.add('hidden');
}

function onMapContextMenu(e) {
    e.preventDefault();
    const menu = document.getElementById('context-menu');
    state.contextCoords = e.lngLat;

    menu.style.left = e.originalEvent.clientX + 'px';
    menu.style.top = e.originalEvent.clientY + 'px';
    menu.classList.remove('hidden');
}

function onMapMoveEnd() {
    if (!state.map) return;
    const center = state.map.getCenter();
    document.getElementById('header-coords').textContent =
        `${center.lat.toFixed(4)}, ${center.lng.toFixed(4)}`;

    // Update minimap viewport indicator
    updateMinimapViewport();
    updateURLState();
}

// ============================================================
// Minimap
// ============================================================

function initMinimap() {
    state.minimap = new maplibregl.Map({
        container: 'minimap',
        style: {
            version: 8,
            sources: {
                minibase: {
                    type: 'raster',
                    tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
                    tileSize: 256,
                    maxzoom: 6,
                },
            },
            layers: [{ id: 'minibase', type: 'raster', source: 'minibase' }],
        },
        center: US_CENTER,
        zoom: 2,
        interactive: false,
        attributionControl: false,
    });

    state.minimap.on('load', () => {
        state.minimap.addSource('viewport-box', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
        });
        state.minimap.addLayer({
            id: 'viewport-outline',
            type: 'line',
            source: 'viewport-box',
            paint: {
                'line-color': '#58a6ff',
                'line-width': 1.5,
            },
        });
        state.minimap.addLayer({
            id: 'viewport-fill',
            type: 'fill',
            source: 'viewport-box',
            paint: {
                'fill-color': '#58a6ff',
                'fill-opacity': 0.1,
            },
        });
    });

    // Click minimap to fly to location
    document.getElementById('minimap').addEventListener('click', (e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const lngLat = state.minimap.unproject([x, y]);
        state.map.flyTo({ center: lngLat, zoom: 6, duration: 1500 });
    });
}

function updateMinimapViewport() {
    if (!state.minimap || !state.map) return;
    const bounds = state.map.getBounds();
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();

    const box = {
        type: 'Feature',
        geometry: {
            type: 'Polygon',
            coordinates: [[
                [sw.lng, sw.lat],
                [ne.lng, sw.lat],
                [ne.lng, ne.lat],
                [sw.lng, ne.lat],
                [sw.lng, sw.lat],
            ]],
        },
    };

    const source = state.minimap.getSource('viewport-box');
    if (source) {
        source.setData({ type: 'FeatureCollection', features: [box] });
    }
}

// ============================================================
// Measurement Tools
// ============================================================

function startMeasure(mode) {
    // Toggle off if already in this mode
    if (state.measuring === mode) {
        cancelMeasure();
        return;
    }
    cancelMeasure();
    state.measuring = mode;
    state.measurePoints = [];
    state.map.getCanvas().style.cursor = 'crosshair';

    document.getElementById(mode === 'distance' ? 'btn-measure-dist' : 'btn-measure-area')
        .classList.add('active');
}

function cancelMeasure() {
    state.measuring = null;
    state.measurePoints = [];
    state.map.getCanvas().style.cursor = '';
    state.map.getSource('measure')?.setData({ type: 'FeatureCollection', features: [] });
    document.getElementById('btn-measure-dist').classList.remove('active');
    document.getElementById('btn-measure-area').classList.remove('active');

    // Remove any popups
    const popups = document.querySelectorAll('.maplibregl-popup');
    popups.forEach(p => p.remove());
}

function handleMeasureClick(e) {
    const pt = [e.lngLat.lng, e.lngLat.lat];
    state.measurePoints.push(pt);

    if (state.measuring === 'distance' && state.measurePoints.length === 2) {
        const [p1, p2] = state.measurePoints;
        const dist = haversineKm(p1[1], p1[0], p2[1], p2[0]);

        state.map.getSource('measure').setData({
            type: 'FeatureCollection',
            features: [
                { type: 'Feature', geometry: { type: 'LineString', coordinates: [p1, p2] } },
                { type: 'Feature', geometry: { type: 'Point', coordinates: p1 } },
                { type: 'Feature', geometry: { type: 'Point', coordinates: p2 } },
            ],
        });

        new maplibregl.Popup({ closeOnClick: true })
            .setLngLat([(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2])
            .setHTML(`<strong>${dist.toFixed(2)} km</strong> (${(dist * 0.621371).toFixed(2)} mi)`)
            .addTo(state.map);

        setTimeout(() => cancelMeasure(), 100);
    } else if (state.measuring === 'area' && state.measurePoints.length >= 3) {
        // Show polygon, click again near first point to close
        const coords = [...state.measurePoints, state.measurePoints[0]];
        const features = [
            { type: 'Feature', geometry: { type: 'Polygon', coordinates: [coords] } },
            ...state.measurePoints.map(p => ({ type: 'Feature', geometry: { type: 'Point', coordinates: p } })),
        ];
        state.map.getSource('measure').setData({ type: 'FeatureCollection', features });

        // Check if clicked near the first point (close polygon)
        const firstPt = state.measurePoints[0];
        const distToFirst = haversineKm(pt[1], pt[0], firstPt[1], firstPt[0]);
        if (state.measurePoints.length > 3 && distToFirst < 0.5) {
            const area = polygonAreaKm2(state.measurePoints);
            const center = polygonCenter(state.measurePoints);

            new maplibregl.Popup({ closeOnClick: true })
                .setLngLat(center)
                .setHTML(`<strong>${area.toFixed(2)} km&sup2;</strong>`)
                .addTo(state.map);

            setTimeout(() => cancelMeasure(), 100);
        }
    } else {
        // Update visualization while measuring
        const features = [
            ...state.measurePoints.map(p => ({ type: 'Feature', geometry: { type: 'Point', coordinates: p } })),
        ];
        if (state.measurePoints.length >= 2) {
            features.push({
                type: 'Feature',
                geometry: { type: 'LineString', coordinates: state.measurePoints },
            });
        }
        state.map.getSource('measure').setData({ type: 'FeatureCollection', features });
    }
}

function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function polygonAreaKm2(points) {
    // Shoelace formula on projected coords (approximate for small areas)
    const R = 6371;
    let area = 0;
    const n = points.length;
    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        const xi = points[i][0] * Math.PI / 180 * R * Math.cos(points[i][1] * Math.PI / 180);
        const yi = points[i][1] * Math.PI / 180 * R;
        const xj = points[j][0] * Math.PI / 180 * R * Math.cos(points[j][1] * Math.PI / 180);
        const yj = points[j][1] * Math.PI / 180 * R;
        area += xi * yj - xj * yi;
    }
    return Math.abs(area / 2);
}

function polygonCenter(points) {
    const n = points.length;
    const lon = points.reduce((s, p) => s + p[0], 0) / n;
    const lat = points.reduce((s, p) => s + p[1], 0) / n;
    return [lon, lat];
}

// ============================================================
// Search
// ============================================================

function toggleSearch() {
    const bar = document.getElementById('search-bar');
    const input = document.getElementById('search-input');
    if (bar.classList.contains('hidden')) {
        bar.classList.remove('hidden');
        input.focus();
    } else {
        bar.classList.add('hidden');
        input.value = '';
        document.getElementById('search-results').classList.add('hidden');
    }
}

function handleSearch(query) {
    const results = document.getElementById('search-results');
    if (!query.trim()) {
        results.classList.add('hidden');
        return;
    }

    const items = [];

    // Check for coordinate input (lat, lon)
    const coordMatch = query.match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/);
    if (coordMatch) {
        const lat = parseFloat(coordMatch[1]);
        const lon = parseFloat(coordMatch[2]);
        items.push({
            name: `${lat.toFixed(4)}, ${lon.toFixed(4)}`,
            action: () => state.map.flyTo({ center: [lon, lat], zoom: 12, duration: 1500 }),
        });
    }

    // Search demo data regions
    const q = query.toLowerCase();
    for (const [key, site] of Object.entries(DEMO_SITES)) {
        if (site.name.toLowerCase().includes(q)) {
            items.push({
                name: site.name,
                detail: site.period,
                action: () => {
                    if (!state.demoLoaded) loadDemoData();
                    state.map.flyTo({ center: [site.center[1], site.center[0]], zoom: 12, duration: 1500 });
                },
            });
        }
    }

    // Search known sites in demo data
    if (state.demoData) {
        for (const feature of state.demoData.knownSites.features) {
            if (feature.properties.name.toLowerCase().includes(q)) {
                const coords = feature.geometry.coordinates;
                items.push({
                    name: feature.properties.name,
                    detail: feature.properties.period,
                    action: () => {
                        state.map.flyTo({ center: coords, zoom: 14, duration: 1500 });
                        state.inspector.showKnownSite(feature.properties);
                    },
                });
            }
        }
    }

    // Well-known US places
    const places = {
        'new york': [-74.006, 40.7128],
        'los angeles': [-118.2437, 34.0522],
        'chicago': [-87.6298, 41.8781],
        'new mexico': [-105.8701, 34.5199],
        'louisiana': [-91.8, 31.0],
        'ohio valley': [-83.0, 39.5],
        'great lakes': [-84.0, 44.5],
        'mississippi': [-89.6, 32.7],
        'colorado': [-105.5, 39.0],
        'illinois': [-89.4, 40.0],
    };
    for (const [name, coords] of Object.entries(places)) {
        if (name.includes(q)) {
            items.push({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                action: () => state.map.flyTo({ center: coords, zoom: 7, duration: 1500 }),
            });
        }
    }

    if (items.length === 0) {
        results.innerHTML = '<div class="search-result"><span class="search-result-name">No results found</span></div>';
    } else {
        results.innerHTML = items.map((item, i) => `
            <div class="search-result" data-index="${i}">
                <span class="search-result-name">${escapeHtml(item.name)}</span>
                <span class="search-result-score">${escapeHtml(item.detail)}</span>
            </div>
        `).join('');

        results.querySelectorAll('.search-result').forEach((el, i) => {
            el.addEventListener('click', () => {
                items[i].action();
                toggleSearch();
            });
        });
    }

    results.classList.remove('hidden');
}

// ============================================================
// Export
// ============================================================

function doExport(format) {
    if (format === 'png') {
        const canvas = state.map.getCanvas();
        const link = document.createElement('a');
        link.download = 'archaeo-scan-atlas.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    } else if (format === 'geojson' || format === 'csv') {
        if (!state.demoData) return;

        const bounds = state.map.getBounds();
        const visible = state.demoData.scores.features.filter(f => {
            const [lon, lat] = [f.properties.center_lon || 0, f.properties.center_lat || 0];
            // Swap: check lat is in lat range, lon is in lon range
            return lat >= bounds.getSouth() && lat <= bounds.getNorth() &&
                   lon >= bounds.getWest() && lon <= bounds.getEast();
        });

        let blob;
        if (format === 'geojson') {
            const data = { type: 'FeatureCollection', features: visible };
            blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        } else {
            const header = 'cell_id,lat,lon,composite_score,confidence,layer_count\n';
            const rows = visible.map(f => {
                const p = f.properties;
                return `${p.cell_id},${p.center_lat},${p.center_lon},${p.composite_score},${p.confidence},${p.layer_count}`;
            });
            blob = new Blob([header + rows.join('\n')], { type: 'text/csv' });
        }

        const link = document.createElement('a');
        link.download = `archaeo-scan-export.${format}`;
        link.href = URL.createObjectURL(blob);
        link.click();
        URL.revokeObjectURL(link.href);
    }

    document.getElementById('export-modal').classList.add('hidden');
}

// ============================================================
// URL State
// ============================================================

function parseURLState() {
    const hash = location.hash.slice(1);
    if (!hash) return;

    const params = new URLSearchParams(hash);
    const lat = parseFloat(params.get('lat'));
    const lon = parseFloat(params.get('lon'));
    const zoom = parseFloat(params.get('zoom'));
    const time = parseInt(params.get('time'), 10);
    const base = params.get('base');
    const layers = params.get('layers');

    if (!isNaN(lat) && !isNaN(lon)) {
        state.map.setCenter([lon, lat]);
    }
    if (!isNaN(zoom)) {
        state.map.setZoom(zoom);
    }
    if (base && BASE_LAYERS[base]) {
        switchBasemap(base);
        document.querySelector(`input[name="basemap"][value="${base}"]`).checked = true;
    }
    if (!isNaN(time) && state.timeline) {
        state.timeline.currentBP = time;
        state.timeline.rangeEl.value = time;
        state.timeline._updateDisplay();
    }
    if (layers) {
        for (const l of layers.split(',')) {
            const cb = document.querySelector(`input[data-layer="${l}"]`);
            if (cb) {
                cb.checked = true;
                setLayerVisibility(l, true);
            }
        }
    }
}

function updateURLState() {
    if (!state.map) return;
    const center = state.map.getCenter();
    const zoom = state.map.getZoom();
    const params = new URLSearchParams();
    params.set('lat', center.lat.toFixed(4));
    params.set('lon', center.lng.toFixed(4));
    params.set('zoom', zoom.toFixed(1));
    if (state.timeline && state.timeline.currentBP > 0) {
        params.set('time', state.timeline.currentBP);
    }
    params.set('base', state.activeBasemap);
    if (state.activeLayers.size > 0) {
        params.set('layers', [...state.activeLayers].join(','));
    }
    history.replaceState(null, '', '#' + params.toString());
}

// ============================================================
// Context Menu
// ============================================================

function initContextMenu() {
    document.addEventListener('click', () => {
        document.getElementById('context-menu').classList.add('hidden');
    });

    document.querySelectorAll('.ctx-item').forEach(el => {
        el.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            if (!state.contextCoords) return;

            if (action === 'copy-coords') {
                const text = `${state.contextCoords.lat.toFixed(6)}, ${state.contextCoords.lng.toFixed(6)}`;
                navigator.clipboard.writeText(text).catch(() => {});
            } else if (action === 'whats-here') {
                // Query features at this point
                const point = state.map.project(state.contextCoords);
                const features = state.map.queryRenderedFeatures(point, {
                    layers: ['h3-grid-fill'],
                });
                if (features.length > 0) {
                    const props = features[0].properties;
                    let layerScores = props.layer_scores;
                    let factors = props.contributing_factors;
                    if (typeof layerScores === 'string') {
                        try { layerScores = JSON.parse(layerScores); } catch { layerScores = {}; }
                    }
                    if (typeof factors === 'string') {
                        try { factors = JSON.parse(factors); } catch { factors = []; }
                    }
                    state.inspector.showCell({ ...props, layer_scores: layerScores, contributing_factors: factors });
                } else {
                    // Show coordinates in inspector
                    new maplibregl.Popup({ closeOnClick: true })
                        .setLngLat(state.contextCoords)
                        .setHTML(`<div style="font-family:var(--font-mono);font-size:11px">${state.contextCoords.lat.toFixed(6)}, ${state.contextCoords.lng.toFixed(6)}<br><span style="color:#8b949e">No scored data at this location</span></div>`)
                        .addTo(state.map);
                }
            }
        });
    });
}

// ============================================================
// Keyboard Shortcuts
// ============================================================

function initKeyboard() {
    document.addEventListener('keydown', (e) => {
        // Don't capture when typing in inputs
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            if (e.key === 'Escape') {
                e.target.blur();
                toggleSearch();
            }
            return;
        }

        switch (e.key) {
            case 'l':
            case 'L':
                document.getElementById('layer-panel').classList.toggle('collapsed');
                break;
            case 'i':
            case 'I':
                state.inspector.togglePanel();
                break;
            case 't':
            case 'T':
                document.getElementById('timeslider').style.display =
                    document.getElementById('timeslider').style.display === 'none' ? '' : 'none';
                break;
            case 'f':
            case 'F':
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen?.();
                } else {
                    document.exitFullscreen?.();
                }
                break;
            case 's':
            case 'S':
                toggleSearch();
                break;
            case 'd':
            case 'D':
                loadDemoData();
                break;
            case 'Escape':
                cancelMeasure();
                document.querySelectorAll('.modal-overlay').forEach(m => m.classList.add('hidden'));
                document.getElementById('context-menu').classList.add('hidden');
                document.getElementById('search-bar').classList.add('hidden');
                break;
            case ' ':
                e.preventDefault();
                state.timeline?.togglePlay();
                break;
            case 'ArrowLeft':
                state.timeline?.stepBack();
                break;
            case 'ArrowRight':
                state.timeline?.stepForward();
                break;
            case '1':
                switchBasemap('dark');
                document.querySelector('input[name="basemap"][value="dark"]').checked = true;
                break;
            case '2':
                switchBasemap('satellite');
                document.querySelector('input[name="basemap"][value="satellite"]').checked = true;
                break;
            case '3':
                switchBasemap('topo');
                document.querySelector('input[name="basemap"][value="topo"]').checked = true;
                break;
            case '4':
                switchBasemap('terrain');
                document.querySelector('input[name="basemap"][value="terrain"]').checked = true;
                break;
        }
    });
}

// ============================================================
// Settings
// ============================================================

function initSettings() {
    const threshold = document.getElementById('setting-score-threshold');
    const thresholdVal = document.getElementById('setting-score-value');
    threshold.addEventListener('input', () => {
        const val = parseInt(threshold.value, 10) / 100;
        thresholdVal.textContent = val.toFixed(2);
        state.settings.scoreThreshold = val;
        applyScoreThreshold(val);
    });

    document.getElementById('setting-preset').addEventListener('change', (e) => {
        state.settings.preset = e.target.value;
        const presetName = e.target.options[e.target.selectedIndex].text;
        document.getElementById('preset-indicator').textContent = presetName;
    });

    document.getElementById('setting-resolution').addEventListener('change', (e) => {
        state.settings.resolution = parseInt(e.target.value, 10);
    });

    document.getElementById('setting-anim-speed').addEventListener('change', (e) => {
        state.settings.animSpeed = parseInt(e.target.value, 10);
        if (state.timeline) state.timeline.setSpeed(state.settings.animSpeed);
    });

    document.getElementById('setting-color-scheme').addEventListener('change', (e) => {
        state.settings.colorScheme = e.target.value;
        applyColorScheme(e.target.value);
    });
}

function applyScoreThreshold(threshold) {
    if (!state.map.getLayer('h3-grid-fill')) return;
    state.map.setFilter('h3-grid-fill', ['>=', ['get', 'composite_score'], threshold]);
    state.map.setFilter('h3-grid-outline', ['>=', ['get', 'composite_score'], threshold]);
}

function applyColorScheme(scheme) {
    if (!state.map.getLayer('h3-grid-fill')) return;
    let colorExpr;
    if (scheme === 'green-yellow-red') {
        colorExpr = [
            'interpolate', ['linear'], ['get', 'composite_score'],
            0.0, '#22c55e',
            0.5, '#eab308',
            1.0, '#dc2626',
        ];
    } else if (scheme === 'single-ramp') {
        colorExpr = [
            'interpolate', ['linear'], ['get', 'composite_score'],
            0.0, '#1e3a5f',
            0.5, '#3b82f6',
            1.0, '#93c5fd',
        ];
    } else {
        colorExpr = [
            'interpolate', ['linear'], ['get', 'composite_score'],
            0.0, '#2563eb',
            0.2, '#3b82f6',
            0.5, '#eab308',
            0.7, '#f97316',
            1.0, '#dc2626',
        ];
    }
    state.map.setPaintProperty('h3-grid-fill', 'fill-color', colorExpr);
}

// ============================================================
// Wire Up UI Controls
// ============================================================

function initControls() {
    // Basemap radios
    document.querySelectorAll('input[name="basemap"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            switchBasemap(e.target.value);
        });
    });

    // Layer checkboxes
    document.querySelectorAll('input[type="checkbox"][data-layer]').forEach(cb => {
        cb.addEventListener('change', (e) => {
            setLayerVisibility(e.target.dataset.layer, e.target.checked);
        });
    });

    // Layer opacity sliders
    document.querySelectorAll('.layer-opacity').forEach(slider => {
        slider.addEventListener('input', (e) => {
            setLayerOpacity(e.target.dataset.layer, parseInt(e.target.value, 10) / 100);
        });
    });

    // Layer panel toggle
    document.getElementById('layer-panel-toggle').addEventListener('click', () => {
        document.getElementById('layer-panel').classList.toggle('collapsed');
    });

    // Demo data button
    document.getElementById('load-demo-btn').addEventListener('click', loadDemoData);

    // Toolbar buttons
    document.getElementById('btn-search').addEventListener('click', toggleSearch);
    document.getElementById('btn-measure-dist').addEventListener('click', () => startMeasure('distance'));
    document.getElementById('btn-measure-area').addEventListener('click', () => startMeasure('area'));
    document.getElementById('btn-screenshot').addEventListener('click', () => doExport('png'));
    document.getElementById('btn-export').addEventListener('click', () => {
        document.getElementById('export-modal').classList.remove('hidden');
    });
    document.getElementById('btn-settings').addEventListener('click', () => {
        document.getElementById('settings-modal').classList.remove('hidden');
    });
    document.getElementById('btn-about').addEventListener('click', () => {
        document.getElementById('about-modal').classList.remove('hidden');
    });

    // Search input
    document.getElementById('search-input').addEventListener('input', (e) => {
        handleSearch(e.target.value);
    });
    document.getElementById('search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleSearch(e.target.value);
    });
    document.getElementById('search-close').addEventListener('click', toggleSearch);

    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modalId = e.target.dataset.modal;
            document.getElementById(modalId).classList.add('hidden');
        });
    });

    // Modal overlay click-to-close
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.classList.add('hidden');
        });
    });

    // Export buttons
    document.querySelectorAll('[data-export]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            doExport(e.target.dataset.export);
        });
    });

    // Legend close
    document.getElementById('legend-close').addEventListener('click', () => {
        document.getElementById('legend').classList.add('hidden');
    });
}

// ============================================================
// Boot
// ============================================================

function init() {
    initMap();
    state.timeline = new Timeline();
    state.inspector = new Inspector();
    initControls();
    initContextMenu();
    initKeyboard();
    initSettings();
}

document.addEventListener('DOMContentLoaded', init);
