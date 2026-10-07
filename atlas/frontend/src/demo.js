// Source-only candidate: no named-site demo coordinates or synthetic rankings.
const SCORE_COLORS = [
    [0.0, [37, 99, 235]],    // #2563eb
    [0.2, [59, 130, 246]],   // #3b82f6
    [0.5, [234, 179, 8]],    // #eab308
    [0.7, [249, 115, 22]],   // #f97316
    [1.0, [220, 38, 38]],    // #dc2626
];

export function scoreToColor(score) {
    for (let i = 1; i < SCORE_COLORS.length; i++) {
        const [t1, c1] = SCORE_COLORS[i - 1];
        const [t2, c2] = SCORE_COLORS[i];
        if (score <= t2) {
            const t = (score - t1) / (t2 - t1);
            const r = Math.round(c1[0] + t * (c2[0] - c1[0]));
            const g = Math.round(c1[1] + t * (c2[1] - c1[1]));
            const b = Math.round(c1[2] + t * (c2[2] - c1[2]));
            return `rgb(${r},${g},${b})`;
        }
    }
    return 'rgb(220,38,38)';
}

export function scoreToHex(score) {
    for (let i = 1; i < SCORE_COLORS.length; i++) {
        const [t1, c1] = SCORE_COLORS[i - 1];
        const [t2, c2] = SCORE_COLORS[i];
        if (score <= t2) {
            const t = (score - t1) / (t2 - t1);
            const r = Math.round(c1[0] + t * (c2[0] - c1[0]));
            const g = Math.round(c1[1] + t * (c2[1] - c1[1]));
            const b = Math.round(c1[2] + t * (c2[2] - c1[2]));
            return '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
        }
    }
    return '#dc2626';
}


export const DEMO_SITES = {};
export function loadAllDemoData() {
  const empty = () => ({type: 'FeatureCollection', features: []});
  return {scores: empty(), knownSites: empty(), historicalRefs: empty(), regions: []};
}
