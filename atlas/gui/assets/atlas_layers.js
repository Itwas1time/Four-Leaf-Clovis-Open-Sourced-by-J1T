window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.atlas = window.dash_clientside.atlas || {};
window.dash_clientside.atlas.escapeHtml = function(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function(char) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};

window.dash_clientside.atlas.hexStyle = function(feature) {
    var s = (feature && feature.properties && feature.properties.composite_score) || 0;
    var r = Math.round(36 + s * 190);
    var g = Math.round(103 + s * 60);
    var b = Math.round(60 + (1 - s) * 120);
    return {
        fillColor: 'rgb(' + r + ',' + g + ',' + b + ')',
        color: 'rgb(' + r + ',' + g + ',' + b + ')',
        weight: s >= 0.65 ? 1.8 : 0.9,
        opacity: 0.8,
        fillOpacity: 0.18 + s * 0.45
    };
};

window.dash_clientside.atlas.hotspotMarkerPointToLayer = function(feature, latlng) {
    var p = feature.properties || {};
    var rawScore = Number(p.composite_score);
    var score = Number.isFinite(rawScore) ? Math.round(Math.max(0, Math.min(1, rawScore)) * 100) : 0;
    var label = (p.zone_name || p.name || 'Hotspot');
    var rank = p.rank || '?';
    var html = [
        '<div class="atlas-hotspot">',
        '<div class="atlas-hotspot-rank">', window.dash_clientside.atlas.escapeHtml(rank), '</div>',
        '<div class="atlas-hotspot-body">',
        '<div class="atlas-hotspot-title">', window.dash_clientside.atlas.escapeHtml(label), '</div>',
        '<div class="atlas-hotspot-meta">', score, '/100 research index</div>',
        '</div></div>'
    ].join('');
    return L.marker(latlng, {
        icon: L.divIcon({
            className: 'atlas-hotspot-icon',
            html: html,
            iconSize: [184, 52],
            iconAnchor: [24, 26]
        }),
        title: label,
        riseOnHover: true,
        zIndexOffset: 2000
    });
};

window.dash_clientside.atlas.knownSitePointToLayer = function(_feature, latlng) {
    return L.circleMarker(latlng, {
        radius: 7,
        fillColor: '#fbbf24',
        color: '#7c2d12',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.95
    });
};

window.dash_clientside.atlas.nearbySitePointToLayer = function(_feature, latlng) {
    return L.circleMarker(latlng, {
        radius: 6,
        fillColor: '#f97316',
        color: '#7c2d12',
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.72
    });
};

window.dash_clientside.atlas.paleoContextPointToLayer = function(_feature, latlng) {
    return L.circleMarker(latlng, {
        radius: 5,
        fillColor: '#06b6d4',
        color: '#164e63',
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.78
    });
};

window.dash_clientside.atlas.tribalBoundaryStyle = function(feature) {
    var p = feature.properties || {};
    var kind = (p.boundary_type || '').toLowerCase();
    var color = kind.indexOf('alaska') >= 0 ? '#60a5fa' : kind.indexOf('trust') >= 0 ? '#fb923c' : '#f59e0b';
    return {
        fillColor: color,
        color: color,
        weight: 2,
        opacity: 0.82,
        fillOpacity: 0.12
    };
};

window.dash_clientside.atlas.nativeTerritoryStyle = function(feature) {
    var p = feature.properties || {};
    var hist = !!p.is_historical;
    return {
        fillColor: hist ? '#8b5cf6' : '#7c3aed',
        color: hist ? '#a78bfa' : '#7c3aed',
        weight: hist ? 1.5 : 2,
        opacity: 0.78,
        fillOpacity: hist ? 0.08 : 0.12,
        dashArray: hist ? '6 4' : null
    };
};

window.dash_clientside.atlas.bindFeatureLabel = function(feature, layer) {
    var p = (feature && feature.properties) || {};
    if (p.cluster) {
        var count = Number(p.point_count) || 0;
        if (layer && layer.bindTooltip) {
            layer.bindTooltip(count + ' grouped records · click to zoom', {sticky: true, direction: 'top', opacity: 0.98, className: 'atlas-feature-tooltip'});
        }
        if (layer && layer.on) {
            layer.on('click', function() {
                window.dash_clientside.set_props('selected-map-feature-store', {
                    data: {cluster_count: count, selected_at: Date.now()}
                });
                if (layer._map && layer.getLatLng) {
                    layer._map.setView(layer.getLatLng(), Math.min(layer._map.getMaxZoom(), layer._map.getZoom() + 2));
                }
            });
        }
        return;
    }
    var title = p.name || p.zone_name || 'Feature';
    var parts = [];
    if (p.site_type) parts.push(p.site_type);
    if (p.period) parts.push(p.period);
    if (p.source) parts.push(p.source);
    var escapeHtml = function(value) {
        return String(value).replace(/[&<>"']/g, function(char) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
        });
    };
    var text = '<div class="atlas-tooltip-title">' + escapeHtml(title) + '</div>';
    if (parts.length) {
        text += '<div class="atlas-tooltip-meta">' + parts.map(escapeHtml).join(' | ') + '</div>';
    }
    if (layer && layer.bindTooltip) {
        layer.bindTooltip(text, {sticky: true, direction: 'top', opacity: 0.98, className: 'atlas-feature-tooltip'});
    }
    if (layer && layer.on) {
        layer.on('click', function() {
            window.dash_clientside.set_props('selected-map-feature-store', {
                data: {feature: feature, selected_at: Date.now()}
            });
        });
    }
};
