/**
 * ARCHAEO-SCAN Atlas — Timeline / TimeSlider Controller
 *
 * Manages the time slider, animation playback, and period metadata.
 * Drives temporal layers (paleo-coastlines, ice sheets) when available.
 */

// ============================================================
// Static timeline data (fallback if API unavailable)
// ============================================================

const PERIODS = [
    { years_bp: 0,     label: 'Present',                sea_level_m: 0,    ice_coverage: 'No significant ice coverage',                    cultural_period: 'Modern' },
    { years_bp: 500,   label: 'Contact',                 sea_level_m: 0,    ice_coverage: 'Modern ice coverage',                            cultural_period: 'De Soto, Coronado — European contact' },
    { years_bp: 1000,  label: 'Mississippian',           sea_level_m: 0,    ice_coverage: 'Modern',                                         cultural_period: 'Cahokia, Moundville — complex chiefdoms' },
    { years_bp: 2000,  label: 'Woodland',                sea_level_m: 0,    ice_coverage: 'Modern',                                         cultural_period: 'Hopewell, Adena — mound building intensifies' },
    { years_bp: 5000,  label: 'Late Archaic',            sea_level_m: -3,   ice_coverage: 'Modern ice coverage',                            cultural_period: 'Poverty Point, Watson Brake' },
    { years_bp: 10000, label: 'Early Holocene',          sea_level_m: -40,  ice_coverage: 'Laurentide remnant over Hudson Bay',             cultural_period: 'Early Archaic — broad adaptation' },
    { years_bp: 12900, label: 'Younger Dryas',           sea_level_m: -60,  ice_coverage: 'Brief re-advance, cold snap',                    cultural_period: 'Folsom, Dalton — megafauna extinction' },
    { years_bp: 13500, label: 'Clovis',                  sea_level_m: -70,  ice_coverage: 'Rapid retreat, corridor fully open',             cultural_period: 'Clovis — first widespread North American culture' },
    { years_bp: 15000, label: 'Deglaciation',            sea_level_m: -80,  ice_coverage: 'Ice-free corridor beginning to open',            cultural_period: 'Pre-Clovis (Paisley Caves, Monte Verde)' },
    { years_bp: 20000, label: 'Last Glacial Maximum',    sea_level_m: -120, ice_coverage: 'Maximum extent — 2km thick over Great Lakes',    cultural_period: 'Pre-Clovis (contested)' },
    { years_bp: 25000, label: 'Pre-LGM',                 sea_level_m: -100, ice_coverage: 'Laurentide and Cordilleran sheets growing',      cultural_period: 'Pre-human (contested)' },
];

// Tick marks for the slider display
const TICK_MARKS = [
    { bp: 25000, label: '25k BP' },
    { bp: 20000, label: 'LGM' },
    { bp: 15000, label: '15k BP' },
    { bp: 13500, label: 'Clovis' },
    { bp: 12900, label: 'YD' },
    { bp: 10000, label: '10k BP' },
    { bp: 5000,  label: '5k BP' },
    { bp: 2000,  label: 'Woodland' },
    { bp: 1000,  label: 'Mississippian' },
    { bp: 500,   label: 'Contact' },
    { bp: 0,     label: 'Now' },
];

// ============================================================
// Timeline class
// ============================================================

export class Timeline {
    constructor() {
        this.periods = [...PERIODS].sort((a, b) => a.years_bp - b.years_bp);
        this.currentBP = 0;
        this.playing = false;
        this.animationId = null;
        this.animationSpeed = 30000; // ms for full sweep
        this.listeners = [];

        this._initDOM();
        this._fetchFromAPI();
    }

    _initDOM() {
        this.rangeEl = document.getElementById('time-range');
        this.playBtn = document.getElementById('time-play');
        this.ticksEl = document.getElementById('time-ticks');
        this.dateEl = document.getElementById('time-date');
        this.seaEl = document.getElementById('time-sea-level');
        this.cultureEl = document.getElementById('time-culture');
        this.iceEl = document.getElementById('time-ice');

        // Build tick marks
        this._buildTicks();

        // Range input handler
        this.rangeEl.addEventListener('input', () => {
            this.currentBP = parseInt(this.rangeEl.value, 10);
            this._updateDisplay();
            this._notifyListeners();
        });

        // Play button
        this.playBtn.addEventListener('click', () => this.togglePlay());
    }

    _buildTicks() {
        this.ticksEl.innerHTML = '';
        for (const tick of TICK_MARKS) {
            const span = document.createElement('span');
            span.textContent = tick.label;
            span.addEventListener('click', () => {
                this.currentBP = tick.bp;
                this.rangeEl.value = tick.bp;
                this._updateDisplay();
                this._notifyListeners();
            });
            this.ticksEl.appendChild(span);
        }
    }

    async _fetchFromAPI() {
        try {
            const res = await fetch('/api/timeline');
            if (res.ok) {
                const data = await res.json();
                if (data.periods && data.periods.length > 0) {
                    this.periods = data.periods.sort((a, b) => a.years_bp - b.years_bp);
                }
            }
        } catch {
            // Use static fallback — already loaded
        }
    }

    _getPeriodForBP(bp) {
        // Find the two periods that bracket the current BP and interpolate
        const sorted = this.periods;
        if (bp <= sorted[0].years_bp) return sorted[0];
        if (bp >= sorted[sorted.length - 1].years_bp) return sorted[sorted.length - 1];

        for (let i = 1; i < sorted.length; i++) {
            if (bp <= sorted[i].years_bp) {
                // Return the nearest period
                const dist0 = bp - sorted[i - 1].years_bp;
                const dist1 = sorted[i].years_bp - bp;
                return dist0 <= dist1 ? sorted[i - 1] : sorted[i];
            }
        }
        return sorted[sorted.length - 1];
    }

    _interpolateSeaLevel(bp) {
        const sorted = this.periods;
        if (bp <= sorted[0].years_bp) return sorted[0].sea_level_m;
        if (bp >= sorted[sorted.length - 1].years_bp) return sorted[sorted.length - 1].sea_level_m;

        for (let i = 1; i < sorted.length; i++) {
            if (bp <= sorted[i].years_bp) {
                const t = (bp - sorted[i - 1].years_bp) / (sorted[i].years_bp - sorted[i - 1].years_bp);
                return sorted[i - 1].sea_level_m + t * (sorted[i].sea_level_m - sorted[i - 1].sea_level_m);
            }
        }
        return 0;
    }

    _updateDisplay() {
        const period = this._getPeriodForBP(this.currentBP);
        const seaLevel = this._interpolateSeaLevel(this.currentBP);

        if (this.currentBP === 0) {
            this.dateEl.textContent = 'Present';
        } else {
            this.dateEl.textContent = `${this.currentBP.toLocaleString()} years ago`;
        }

        this.seaEl.textContent = `Sea level: ${seaLevel >= 0 ? '+' : ''}${Math.round(seaLevel)}m`;
        this.cultureEl.textContent = period.cultural_period;
        this.iceEl.textContent = period.ice_coverage;
    }

    _notifyListeners() {
        const period = this._getPeriodForBP(this.currentBP);
        const seaLevel = this._interpolateSeaLevel(this.currentBP);
        for (const fn of this.listeners) {
            fn({ bp: this.currentBP, period, seaLevel });
        }
    }

    onChange(fn) {
        this.listeners.push(fn);
    }

    togglePlay() {
        if (this.playing) {
            this.pause();
        } else {
            this.play();
        }
    }

    play() {
        this.playing = true;
        this.playBtn.innerHTML = '&#9646;&#9646;'; // pause icon
        this.playBtn.classList.add('playing');

        // If at present, start from max
        if (this.currentBP <= 0) {
            this.currentBP = 25000;
            this.rangeEl.value = 25000;
        }

        const startBP = this.currentBP;
        const startTime = performance.now();
        const duration = this.animationSpeed * (startBP / 25000);

        const animate = (now) => {
            if (!this.playing) return;
            const elapsed = now - startTime;
            const progress = Math.min(1, elapsed / duration);

            this.currentBP = Math.round(startBP * (1 - progress));
            this.rangeEl.value = this.currentBP;
            this._updateDisplay();
            this._notifyListeners();

            if (progress < 1) {
                this.animationId = requestAnimationFrame(animate);
            } else {
                this.pause();
            }
        };

        this.animationId = requestAnimationFrame(animate);
    }

    pause() {
        this.playing = false;
        this.playBtn.innerHTML = '&#9654;'; // play icon
        this.playBtn.classList.remove('playing');
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    setSpeed(ms) {
        this.animationSpeed = ms;
    }

    stepBack() {
        // Jump to previous period
        const sorted = [...this.periods].sort((a, b) => a.years_bp - b.years_bp);
        for (let i = sorted.length - 1; i >= 0; i--) {
            if (sorted[i].years_bp > this.currentBP) {
                this.currentBP = sorted[i].years_bp;
                this.rangeEl.value = this.currentBP;
                this._updateDisplay();
                this._notifyListeners();
                return;
            }
        }
    }

    stepForward() {
        // Jump to next period (closer to present)
        const sorted = [...this.periods].sort((a, b) => b.years_bp - a.years_bp);
        for (let i = sorted.length - 1; i >= 0; i--) {
            if (sorted[i].years_bp < this.currentBP) {
                this.currentBP = sorted[i].years_bp;
                this.rangeEl.value = this.currentBP;
                this._updateDisplay();
                this._notifyListeners();
                return;
            }
        }
    }
}
