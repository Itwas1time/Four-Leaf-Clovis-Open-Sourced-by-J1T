/**
 * ARCHAEO-SCAN Atlas — Site Inspector Panel
 *
 * Manages the right sidebar that shows detailed information
 * about selected H3 cells, known sites, and other features.
 */

import { scoreToColor } from './demo.js';
import { escapeHtml, unitScore } from './safe_html.js';

const ALL_LAYERS = [
    'lidar_anomaly', 'hydro_proximity', 'soil_anomaly', 'terrain_anomaly',
    'crop_mark', 'shelter_probability', 'known_site_proximity',
    'oral_history_reference', 'citizen_report_density',
];

const LAYER_LABELS = {
    lidar_anomaly: 'LiDAR Anomaly',
    hydro_proximity: 'Hydro Proximity',
    soil_anomaly: 'Soil Anomaly',
    terrain_anomaly: 'Terrain Anomaly',
    crop_mark: 'Crop Mark',
    shelter_probability: 'Shelter Probability',
    known_site_proximity: 'Known Site Proximity',
    oral_history_reference: 'Oral History',
    citizen_report_density: 'Citizen Reports',
};

export class Inspector {
    constructor() {
        this.panel = document.getElementById('inspector-panel');
        this.emptyState = document.getElementById('inspector-empty');
        this.content = document.getElementById('inspector-content');
        this.toggle = document.getElementById('inspector-panel-toggle');

        this.toggle.addEventListener('click', () => this.togglePanel());
    }

    togglePanel() {
        this.panel.classList.toggle('collapsed');
        this.toggle.innerHTML = this.panel.classList.contains('collapsed') ? '&laquo;' : '&raquo;';
        this.toggle.title = this.panel.classList.contains('collapsed') ? 'Expand (I)' : 'Collapse (I)';
    }

    show() {
        if (this.panel.classList.contains('collapsed')) {
            this.panel.classList.remove('collapsed');
            this.toggle.innerHTML = '&raquo;';
        }
    }

    /**
     * Display scored cell data in the inspector.
     */
    showCell(properties) {
        this.show();
        this.emptyState.classList.add('hidden');
        this.content.classList.remove('hidden');

        const score = properties.composite_score || 0;
        const confidence = properties.confidence || 0;
        const layerScores = properties.layer_scores || {};
        const factors = properties.contributing_factors || [];
        const cellId = properties.cell_id || '--';
        const lat = properties.center_lat;
        const lon = properties.center_lon;

        // Score hero
        const scoreEl = document.getElementById('insp-score-value');
        scoreEl.textContent = (score * 100).toFixed(1) + '%';
        scoreEl.style.color = scoreToColor(score);

        // Confidence
        const confBar = document.getElementById('insp-confidence-bar');
        confBar.style.width = (confidence * 100) + '%';
        document.getElementById('insp-confidence-text').textContent =
            `${(confidence * 100).toFixed(0)}% (${properties.layer_count || Object.keys(layerScores).length} layers)`;

        // Layer scores
        const scoresEl = document.getElementById('insp-layer-scores');
        scoresEl.innerHTML = '';

        const sortedLayers = Object.entries(layerScores).sort((a, b) => b[1] - a[1]);
        for (const [layer, rawValue] of sortedLayers) {
            const val = unitScore(rawValue);
            const row = document.createElement('div');
            row.className = 'layer-score-row';
            row.innerHTML = `
                <span class="layer-score-name">${escapeHtml(LAYER_LABELS[layer] || layer.replace(/_/g, ' '))}</span>
                <div class="score-bar-wrap">
                    <div class="score-bar-fill" style="width:${val * 100}%;background:${scoreToColor(val)}"></div>
                </div>
                <span class="layer-score-val">${val.toFixed(2)}</span>
            `;
            scoresEl.appendChild(row);
        }

        // Contributing factors
        const factorsEl = document.getElementById('insp-factors');
        factorsEl.innerHTML = '';
        for (const f of factors) {
            const li = document.createElement('li');
            li.textContent = f;
            factorsEl.appendChild(li);
        }

        // Location
        document.getElementById('insp-coords').textContent =
            lat !== undefined ? `${lat.toFixed(5)}, ${lon.toFixed(5)}` : '--';
        document.getElementById('insp-h3').textContent = cellId;
        document.getElementById('insp-region').textContent = ''; // Would need reverse geocoding

        // Data layers present
        const dataEl = document.getElementById('insp-data-layers');
        dataEl.innerHTML = '';
        let presentCount = 0;

        for (const layer of ALL_LAYERS) {
            const present = layerScores[layer] !== undefined && layerScores[layer] > 0;
            if (present) presentCount++;

            const row = document.createElement('div');
            row.className = 'data-layer-row';
            row.innerHTML = `
                <span class="data-layer-check ${present ? 'present' : 'missing'}">${present ? '\u2713' : '\u2014'}</span>
                <span>${LAYER_LABELS[layer] || layer}</span>
            `;
            dataEl.appendChild(row);
        }

        document.getElementById('insp-layer-summary').textContent =
            `${presentCount} of ${ALL_LAYERS.length} layers collected for this cell`;
    }

    /**
     * Display a known site in the inspector.
     */
    showKnownSite(properties) {
        this.show();
        this.emptyState.classList.add('hidden');
        this.content.classList.remove('hidden');

        const scoreEl = document.getElementById('insp-score-value');
        scoreEl.textContent = 'Known Site';
        scoreEl.style.color = '#f59e0b';
        document.getElementById('insp-score-label').textContent = properties.type || 'Archaeological Site';

        const confBar = document.getElementById('insp-confidence-bar');
        confBar.style.width = '100%';
        document.getElementById('insp-confidence-text').textContent = 'Confirmed';

        document.getElementById('insp-layer-scores').innerHTML =
            `<div class="no-data-msg">Known site — no scoring needed</div>`;

        const factorsEl = document.getElementById('insp-factors');
        factorsEl.innerHTML = '';
        const li = document.createElement('li');
        li.textContent = `${properties.name} — ${properties.period}`;
        factorsEl.appendChild(li);

        document.getElementById('insp-coords').textContent = '--';
        document.getElementById('insp-h3').textContent = '--';
        document.getElementById('insp-region').textContent = '';

        document.getElementById('insp-data-layers').innerHTML = '';
        document.getElementById('insp-layer-summary').textContent = '';
    }

    /**
     * Clear the inspector and show empty state.
     */
    clear() {
        this.emptyState.classList.remove('hidden');
        this.content.classList.add('hidden');
    }
}
