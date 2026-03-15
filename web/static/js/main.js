// AIVentures — Enhanced UI

// ===== Sound Effects (Web Audio API) =====
const SFX = {
    _ctx: null,

    _getCtx() {
        if (!this._ctx) {
            this._ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this._ctx.state === 'suspended') this._ctx.resume();
        return this._ctx;
    },

    play(type) {
        try { this['_' + type](); } catch(e) {}
    },

    _osc(freq, type, duration, vol) {
        const ctx = this._getCtx();
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = type;
        o.frequency.value = freq;
        g.gain.setValueAtTime(vol || 0.15, ctx.currentTime);
        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
        o.connect(g).connect(ctx.destination);
        o.start();
        o.stop(ctx.currentTime + duration);
    },

    _noise(duration, freq, vol) {
        const ctx = this._getCtx();
        const buf = ctx.createBuffer(1, ctx.sampleRate * duration, ctx.sampleRate);
        const d = buf.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * duration * 0.3));
        const src = ctx.createBufferSource();
        src.buffer = buf;
        const f = ctx.createBiquadFilter();
        f.type = 'lowpass';
        f.frequency.value = freq || 800;
        const g = ctx.createGain();
        g.gain.value = vol || 0.2;
        src.connect(f).connect(g).connect(ctx.destination);
        src.start();
    },

    _hit() {
        this._noise(0.12, 600, 0.25);
        this._osc(120, 'sine', 0.1, 0.2);
    },

    _miss() {
        this._noise(0.15, 2000, 0.08);
    },

    _defend() {
        this._osc(300, 'triangle', 0.15, 0.12);
        setTimeout(() => this._osc(400, 'triangle', 0.1, 0.08), 80);
    },

    _heal() {
        this._osc(523, 'sine', 0.25, 0.1);
        setTimeout(() => this._osc(659, 'sine', 0.25, 0.1), 120);
        setTimeout(() => this._osc(784, 'sine', 0.35, 0.12), 240);
    },

    _victory() {
        const notes = [523, 659, 784, 1047];
        notes.forEach((n, i) => {
            setTimeout(() => this._osc(n, 'sine', 0.3, 0.12), i * 150);
            setTimeout(() => this._osc(n * 0.5, 'triangle', 0.3, 0.06), i * 150);
        });
    },

    _defeat() {
        const notes = [300, 250, 200, 150];
        notes.forEach((n, i) => {
            setTimeout(() => this._osc(n, 'sawtooth', 0.5, 0.08), i * 200);
        });
    },

    _levelup() {
        const notes = [523, 587, 659, 784, 880, 1047];
        notes.forEach((n, i) => {
            setTimeout(() => {
                this._osc(n, 'sine', 0.2, 0.1);
                this._osc(n * 1.5, 'triangle', 0.15, 0.05);
            }, i * 80);
        });
    },

    _coin() {
        this._osc(1200, 'sine', 0.08, 0.1);
        setTimeout(() => this._osc(1800, 'sine', 0.12, 0.08), 60);
    },

    _click() {
        this._noise(0.03, 3000, 0.06);
    },

    _spell() {
        this._osc(440, 'sine', 0.15, 0.08);
        setTimeout(() => this._osc(660, 'sine', 0.15, 0.08), 80);
        setTimeout(() => this._osc(880, 'triangle', 0.2, 0.06), 160);
    }
};


// ===== Toast System =====
function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration || 3500;
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(function() {
        toast.classList.add('toast-out');
        setTimeout(function() { toast.remove(); }, 300);
    }, duration);
}

function initToasts() {
    document.querySelectorAll('[data-toast]').forEach(function(el) {
        showToast(el.dataset.toast, el.dataset.toastType || 'info');
        el.remove();
    });

    // Clean query params from URL after reading toasts
    if (window.location.search && document.querySelector('[data-toast]') === null) {
        var url = window.location.pathname;
        window.history.replaceState({}, '', url);
    }
}


// ===== Confetti =====
function showConfetti() {
    var container = document.createElement('div');
    container.className = 'confetti-container';
    document.body.appendChild(container);

    var colors = ['#daa520', '#ffd700', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96e6a1', '#f0c850'];
    for (var i = 0; i < 60; i++) {
        var piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = Math.random() * 100 + '%';
        piece.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDuration = (Math.random() * 2 + 1.5) + 's';
        piece.style.animationDelay = Math.random() * 0.6 + 's';
        piece.style.width = (Math.random() * 8 + 6) + 'px';
        piece.style.height = (Math.random() * 8 + 6) + 'px';
        if (Math.random() > 0.5) piece.style.borderRadius = '50%';
        container.appendChild(piece);
    }

    setTimeout(function() { container.remove(); }, 4500);
}

// ===== Screen Shake =====
function screenShake() {
    document.body.style.animation = 'screenShake 0.5s ease-in-out';
    setTimeout(function() { document.body.style.animation = ''; }, 600);
}


// ===== Selection Cards =====
function initSelectionCards() {
    var cards = document.querySelectorAll('.selection-card[data-value]');
    var input = document.getElementById('selected-value');
    var btn = document.getElementById('continue-btn');
    if (!cards.length) return;

    cards.forEach(function(card) {
        card.addEventListener('click', function() {
            cards.forEach(function(c) { c.classList.remove('selected'); });
            this.classList.add('selected');
            if (input) input.value = this.dataset.value;
            if (btn) btn.disabled = false;
            SFX.play('click');
        });
    });
}


// ===== Skill Counter =====
function initSkillCounter() {
    var container = document.querySelector('[data-max-skills]');
    if (!container) return;

    var max = parseInt(container.dataset.maxSkills);
    var checkboxes = container.querySelectorAll('.skill-checkbox');
    var counter = document.getElementById('skill-count');

    function update() {
        var checked = container.querySelectorAll('.skill-checkbox:checked').length;
        if (counter) counter.textContent = checked;
        checkboxes.forEach(function(cb) {
            if (!cb.checked) cb.disabled = checked >= max;
        });
    }

    checkboxes.forEach(function(cb) {
        cb.addEventListener('change', function() {
            SFX.play('click');
            update();
        });
    });
}


// ===== Battle Log =====
function initBattleLog() {
    var log = document.querySelector('.battle-log');
    if (!log) return;
    log.scrollTop = log.scrollHeight;

    // Play sound for most recent log entry
    var last = log.querySelector('.log-entry:last-child');
    if (last) {
        if (last.classList.contains('damage')) SFX.play('hit');
        else if (last.classList.contains('miss')) SFX.play('miss');
        else if (last.classList.contains('heal')) SFX.play('heal');
        else if (last.classList.contains('defend')) SFX.play('defend');
        else if (last.classList.contains('ability')) SFX.play('spell');
    }
}


// ===== Health Bar Colors =====
function initHealthBars() {
    document.querySelectorAll('.health-bar-fill[data-hp-percent]').forEach(function(bar) {
        var pct = parseInt(bar.dataset.hpPercent || '100');
        if (pct <= 25) {
            bar.style.boxShadow = '0 0 12px rgba(198, 40, 40, 0.8)';
        } else if (pct <= 50) {
            bar.style.boxShadow = '0 0 10px rgba(249, 168, 37, 0.7)';
        }
    });
}


// ===== Auto Effects =====
function initAutoEffects() {
    // Confetti trigger
    if (document.querySelector('[data-confetti]')) {
        showConfetti();
    }

    // Screen shake trigger
    if (document.querySelector('[data-screen-shake]')) {
        screenShake();
    }

    // Auto-play sounds
    document.querySelectorAll('[data-sound]').forEach(function(el) {
        SFX.play(el.dataset.sound);
    });
}


// ===== Shop Tabs =====
function initShopTabs() {
    var tabContainer = document.querySelector('.shop-tabs');
    if (!tabContainer) return;

    var tabs = tabContainer.querySelectorAll('.shop-tab');
    var panels = document.querySelectorAll('.shop-tab-panel');

    // Auto-select tab from URL param
    var params = new URLSearchParams(window.location.search);
    var activeTab = params.get('tab');
    if (activeTab) {
        tabs.forEach(function(t) { t.classList.remove('active'); });
        panels.forEach(function(p) { p.classList.remove('active'); });
        var targetTab = tabContainer.querySelector('[data-tab="' + activeTab + '"]');
        var targetPanel = document.getElementById('tab-' + activeTab);
        if (targetTab) targetTab.classList.add('active');
        if (targetPanel) targetPanel.classList.add('active');
    }

    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            var target = this.dataset.tab;
            tabs.forEach(function(t) { t.classList.remove('active'); });
            panels.forEach(function(p) { p.classList.remove('active'); });
            this.classList.add('active');
            var panel = document.getElementById('tab-' + target);
            if (panel) panel.classList.add('active');
            // Update URL without reload
            var url = new URL(window.location);
            url.searchParams.set('tab', target);
            window.history.replaceState({}, '', url);
            SFX.play('click');
        });
    });
}


// ===== Active Nav Link =====
function initActiveNav() {
    var path = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(function(link) {
        var href = link.getAttribute('href');
        if (path === href || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
        }
    });
}


// ===== Init =====
document.addEventListener('DOMContentLoaded', function() {
    initSelectionCards();
    initSkillCounter();
    initToasts();
    initBattleLog();
    initHealthBars();
    initAutoEffects();
    initActiveNav();
    initShopTabs();
});
