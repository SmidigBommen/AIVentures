/* ============================================================
   AIVentures — battle stage: sprites, effects and turn playback
   ============================================================
   The page reloads after every action. The server sends what the last turn
   did as a list of events (engine/turn_events.py) in data-turn-events, and
   this file plays them back in order: the actor moves, an effect is drawn
   on the target, HP bars step from their old value to the new one.

   Loaded on the arena, victory and defeat pages (after main.js, for SFX). */

(function() {
    'use strict';

    var stage = document.querySelector('.battle-stage');
    if (!stage) return;
    var scene = stage.closest('.battle-scene');

    // Sheet layout shared by every character (see tools/make_sprites.py)
    var SHEET = { cols: 4, rows: 4 };
    var ANIMS = {
        idle:   { row: 0, frames: 4, fps: 4, loop: true },
        attack: { row: 1, frames: 4, fps: 11 },
        hurt:   { row: 2, frames: 2, fps: 6 },
        death:  { row: 3, frames: 4, fps: 6, hold: true }
    };
    var SHOT_COLORS = {
        fire: ['#ffd84a', '#ff7a2a'], cold: ['#ffffff', '#7cc4f0'], lightning: ['#ffffff', '#fff7a8'],
        poison: ['#9ccc5a', '#476f2a'], acid: ['#d6f04a', '#7a9a10'], radiant: ['#fff8d0', '#ffe27a'],
        necrotic: ['#9a5ad0', '#2a1640'], force: ['#d08aff', '#ffffff'], psychic: ['#ff8ad0', '#ffd0f0'],
        thunder: ['#dfe8f5', '#7a8aa6']
    };
    var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function sfx(name) {
        if (typeof SFX !== 'undefined') SFX.play(name);
    }


    // ===== Actors =====
    // An actor is a sprite sheet when one exists for it, otherwise its portrait.
    // Both answer to the same calls; the portrait animates with CSS classes.
    function Actor(el) {
        this.el = el;
        this.sprite = el.querySelector('.sprite');
        this.timer = null;
        this.dead = false;
        if (this.sprite) {
            this.sprite.style.backgroundImage = 'url("' + this.sprite.dataset.sheet + '")';
            this.play('idle');
        }
    }

    Actor.prototype.frame = function(row, col) {
        this.sprite.style.backgroundPosition =
            (col / (SHEET.cols - 1) * 100) + '% ' + (row / (SHEET.rows - 1) * 100) + '%';
    };

    Actor.prototype.play = function(name, done) {
        var self = this;
        if (this.dead && name !== 'death') return;
        if (!this.sprite) {
            // Portrait: restart the CSS animation for this state
            if (name === 'idle') return;
            this.el.classList.remove('pose-attack', 'pose-hurt', 'pose-death');
            void this.el.offsetWidth;
            this.el.classList.add('pose-' + name);
            if (name !== 'death') {
                setTimeout(function() { self.el.classList.remove('pose-' + name); if (done) done(); }, 420);
            }
            return;
        }
        var anim = ANIMS[name];
        var col = 0;
        clearInterval(this.timer);
        this.frame(anim.row, 0);
        this.timer = setInterval(function() {
            col += 1;
            if (col >= anim.frames) {
                if (anim.loop) {
                    col = 0;
                } else {
                    clearInterval(self.timer);
                    if (!anim.hold) self.play('idle');
                    if (done) done();
                    return;
                }
            }
            self.frame(anim.row, col);
        }, 1000 / anim.fps);
    };

    Actor.prototype.pulse = function(cls, ms) {
        var el = this.el;
        el.classList.remove(cls);
        void el.offsetWidth;
        el.classList.add(cls);
        setTimeout(function() { el.classList.remove(cls); }, ms || 450);
    };

    Actor.prototype.die = function() {
        this.dead = true;
        this.play('death');
        this.el.classList.add('is-dead');
    };

    // Centre of the actor's body in stage coordinates
    Actor.prototype.point = function(heightFraction) {
        var box = (this.sprite || this.el.querySelector('.actor-portrait') || this.el).getBoundingClientRect();
        var base = stage.getBoundingClientRect();
        return {
            x: box.left - base.left + box.width / 2,
            y: box.top - base.top + box.height * (heightFraction === undefined ? 0.6 : heightFraction)
        };
    };

    Actor.prototype.float = function(text, cls) {
        var num = document.createElement('span');
        num.className = 'float-number ' + (cls || '');
        num.textContent = text;
        this.el.appendChild(num);
        num.addEventListener('animationend', function() { num.remove(); });
    };

    var actors = {
        player: new Actor(stage.querySelector('[data-actor="player"]')),
        monster: new Actor(stage.querySelector('[data-actor="monster"]'))
    };
    function other(side) { return side === 'player' ? 'monster' : 'player'; }

    // A lunge stops just short of the opponent, whatever the stage width
    function fitLunge() {
        var gap = actors.monster.point().x - actors.player.point().x;
        stage.style.setProperty('--lunge-px', Math.max(40, gap * 0.62) + 'px');
    }
    fitLunge();
    window.addEventListener('resize', fitLunge);


    // ===== Status plates =====
    var plates = {};
    ['player', 'monster'].forEach(function(side) {
        var el = scene.querySelector('[data-combatant="' + side + '"]');
        plates[side] = {
            el: el,
            fill: el.querySelector('.health-bar-fill'),
            text: el.querySelector('[data-hp-now]'),
            max: parseInt(el.dataset.maxHp, 10) || 1,
            hp: parseInt(el.dataset.hp, 10) || 0
        };
    });

    function showHp(side, hp, instant) {
        var plate = plates[side];
        plate.hp = Math.max(0, Math.min(plate.max, hp));
        var pct = plate.hp / plate.max * 100;
        if (instant) plate.fill.style.transition = 'none';
        plate.fill.style.width = pct + '%';
        plate.fill.classList.toggle('hp-low', pct <= 25);
        plate.fill.classList.toggle('hp-mid', pct > 25 && pct <= 50);
        if (instant) { void plate.fill.offsetWidth; plate.fill.style.transition = ''; }
        if (plate.text) plate.text.textContent = plate.hp;
    }
    showHp('player', plates.player.hp, true);
    showHp('monster', plates.monster.hp, true);


    // ===== Effects canvas =====
    // Particles are squares snapped to a coarse grid so they read as pixel art.
    var canvas = stage.querySelector('.stage-fx');
    var ctx = canvas.getContext('2d');
    var GRID = 4;
    var particles = [];
    var running = false;
    var lastTime = 0;

    function fitCanvas() {
        var box = stage.getBoundingClientRect();
        canvas.width = Math.round(box.width);
        canvas.height = Math.round(box.height);
    }
    fitCanvas();
    window.addEventListener('resize', fitCanvas);

    function rand(a, b) { return a + Math.random() * (b - a); }
    function pick(list) { return list[Math.floor(Math.random() * list.length)]; }

    function spawn(p) {
        p.age = -(p.delay || 0);
        p.life = p.life || 500;
        p.size = p.size || GRID;
        particles.push(p);
        if (!running) { running = true; lastTime = 0; requestAnimationFrame(tick); }
    }

    function tick(now) {
        var dt = lastTime ? Math.min(50, now - lastTime) : 16;
        lastTime = now;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles = particles.filter(function(p) {
            p.age += dt;
            if (p.age < 0) return true;
            if (p.age >= p.life) return false;
            var t = p.age / p.life;
            if (p.ring) {
                drawRing(p.x, p.y, p.r0 + (p.r1 - p.r0) * t, p.color, 1 - t);
                return true;
            }
            var step = dt / 1000;
            p.vy = (p.vy || 0) + (p.gravity || 0) * step;
            if (p.drag) { p.vx *= 1 - p.drag * step; p.vy *= 1 - p.drag * step; }
            p.x += (p.vx || 0) * step;
            p.y += p.vy * step;
            ctx.globalAlpha = p.fade === false ? 1 : Math.min(1, (1 - t) * 1.6);
            ctx.fillStyle = p.color;
            var size = p.shrink ? Math.max(GRID / 2, p.size * (1 - t)) : p.size;
            var x = Math.round(p.x / GRID) * GRID, y = Math.round(p.y / GRID) * GRID;
            if (p.plus) {
                ctx.fillRect(x - size, y, size * 3, size);
                ctx.fillRect(x, y - size, size, size * 3);
            } else {
                ctx.fillRect(x, y, size, size);
            }
            return true;
        });
        ctx.globalAlpha = 1;
        if (particles.length) requestAnimationFrame(tick);
        else { running = false; ctx.clearRect(0, 0, canvas.width, canvas.height); }
    }

    function drawRing(cx, cy, radius, color, alpha) {
        var count = Math.max(12, Math.round(radius * 0.9));
        ctx.globalAlpha = Math.max(0, alpha);
        ctx.fillStyle = color;
        for (var i = 0; i < count; i++) {
            var a = i / count * Math.PI * 2;
            ctx.fillRect(Math.round((cx + Math.cos(a) * radius) / GRID) * GRID,
                         Math.round((cy + Math.sin(a) * radius * 0.8) / GRID) * GRID, GRID, GRID);
        }
    }

    // --- building blocks ---
    function burst(at, colors, o) {
        o = o || {};
        for (var i = 0; i < (o.count || 18); i++) {
            var angle = rand(o.from === undefined ? 0 : o.from, o.to === undefined ? Math.PI * 2 : o.to);
            var speed = rand((o.speed || 180) * 0.4, o.speed || 180);
            spawn({
                x: at.x + rand(-6, 6), y: at.y + rand(-6, 6),
                vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
                gravity: o.gravity === undefined ? 300 : o.gravity, drag: o.drag || 1.5,
                life: rand((o.life || 500) * 0.6, o.life || 500), delay: rand(0, o.stagger || 0),
                size: pick(o.sizes || [GRID, GRID, GRID * 2]), color: pick(colors),
                shrink: o.shrink, plus: o.plus
            });
        }
    }

    function ring(at, color, o) {
        o = o || {};
        spawn({ ring: true, x: at.x, y: at.y, r0: o.r0 || 6, r1: o.r1 || 70,
                color: color, life: o.life || 420, delay: o.delay || 0 });
    }

    function rise(at, colors, o) {
        o = o || {};
        for (var i = 0; i < (o.count || 16); i++) {
            spawn({
                x: at.x + rand(-(o.width || 34), o.width || 34), y: at.y + rand(-10, 46),
                vx: rand(-12, 12), vy: -rand(50, o.speed || 130), gravity: 0,
                life: rand(500, o.life || 900), delay: rand(0, o.stagger || 300),
                size: pick(o.sizes || [GRID, GRID * 2]), color: pick(colors), plus: o.plus, shrink: o.shrink
            });
        }
    }

    // A streak of squares along a line or arc, appearing one after another
    function streak(points, colors, o) {
        o = o || {};
        points.forEach(function(pt, i) {
            spawn({ x: pt.x, y: pt.y, vx: 0, vy: 0, gravity: 0, life: o.life || 260,
                    delay: i * (o.step === undefined ? 9 : o.step),
                    size: o.size || GRID * 2, color: pick(colors) });
        });
    }

    function arcPoints(at, dir, radius, from, to, count) {
        var pts = [];
        for (var i = 0; i < count; i++) {
            var a = from + (to - from) * (i / (count - 1));
            pts.push({ x: at.x + Math.cos(a) * radius * dir, y: at.y + Math.sin(a) * radius });
        }
        return pts;
    }

    function linePoints(a, b, count) {
        var pts = [];
        for (var i = 0; i < count; i++) {
            var t = i / (count - 1);
            pts.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
        }
        return pts;
    }

    function boltPoints(at) {
        var pts = [], x = at.x + rand(-30, 30), y = 0;
        while (y < at.y) {
            var nx = x + rand(-26, 26) + (at.x - x) * 0.25, ny = Math.min(at.y, y + rand(18, 34));
            pts = pts.concat(linePoints({ x: x, y: y }, { x: nx, y: ny }, 5));
            x = nx; y = ny;
        }
        return pts;
    }

    function flash(cls) {
        stage.classList.remove('flash-white', 'flash-dark');
        void stage.offsetWidth;
        stage.classList.add(cls);
        setTimeout(function() { stage.classList.remove(cls); }, 260);
    }

    // --- one effect per key; `at` is the target point, `dir` is +1 when it travels rightwards ---
    var FX = {
        slashing: function(at, dir) {
            streak(arcPoints(at, dir, 46, -2.2, 0.9, 16), ['#ffffff', '#dfe8f5', '#b9c6dc']);
            streak(arcPoints(at, dir, 34, -2.0, 0.7, 12), ['#ffffff'], { size: GRID });
            burst(at, ['#e0343c', '#ff6a6a', '#8a1f2a'], { count: 10, speed: 150, life: 420 });
        },
        piercing: function(at, dir) {
            streak(linePoints({ x: at.x - 90 * dir, y: at.y - 6 }, { x: at.x + 14 * dir, y: at.y }, 14),
                   ['#ffffff', '#dfe8f5'], { step: 6 });
            burst(at, ['#ffffff', '#e0343c', '#ffb0b0'], { count: 10, speed: 170, life: 360 });
        },
        bludgeoning: function(at) {
            ring(at, '#fff3c4', { r1: 58, life: 300 });
            burst(at, ['#ffe27a', '#ffffff', '#c9a45a'], { count: 16, speed: 230, life: 380 });
            burst({ x: at.x, y: at.y + 40 }, ['#8a7a60', '#6b5e48'],
                  { count: 10, speed: 90, gravity: 60, life: 600, from: Math.PI, to: Math.PI * 2 });
        },
        fire: function(at) {
            ring(at, '#ff9a3c', { r1: 62, life: 340 });
            rise(at, ['#ffd84a', '#ff9a3c', '#ff5a2a', '#c8343c'], { count: 30, speed: 190, shrink: true });
            burst(at, ['#ffd84a', '#ff7a2a'], { count: 14, speed: 200, gravity: -120, life: 520 });
        },
        cold: function(at) {
            ring(at, '#e8f6ff', { r1: 60, life: 420 });
            burst(at, ['#ffffff', '#bfe6ff', '#7cc4f0', '#4a90d0'],
                  { count: 24, speed: 210, gravity: 120, life: 700, sizes: [GRID, GRID * 2, GRID * 2] });
        },
        lightning: function(at) {
            flash('flash-white');
            streak(boltPoints(at), ['#ffffff', '#fff7a8'], { step: 2, life: 300, size: GRID * 2 });
            streak(boltPoints(at), ['#fff7a8', '#a8c8ff'], { step: 2, life: 220, size: GRID });
            burst(at, ['#ffffff', '#fff7a8', '#a8c8ff'], { count: 18, speed: 260, life: 320, gravity: 0 });
        },
        thunder: function(at) {
            flash('flash-white');
            ring(at, '#dfe8f5', { r1: 50, life: 300 });
            ring(at, '#a8b8d0', { r1: 84, life: 420, delay: 90 });
            ring(at, '#7a8aa6', { r1: 116, life: 520, delay: 180 });
        },
        poison: function(at) {
            rise(at, ['#9ccc5a', '#6fa83c', '#c8f07a', '#476f2a'],
                 { count: 22, speed: 80, life: 1100, sizes: [GRID, GRID * 2, GRID * 3] });
        },
        acid: function(at) {
            burst({ x: at.x, y: at.y - 30 }, ['#d6f04a', '#a8d020', '#7a9a10'],
                  { count: 22, speed: 130, gravity: 520, life: 650 });
            ring({ x: at.x, y: at.y + 34 }, '#d6f04a', { r1: 40, life: 380, delay: 260 });
        },
        radiant: function(at) {
            flash('flash-white');
            ring(at, '#fff3a8', { r1: 76, life: 460 });
            for (var i = -2; i <= 2; i++) {
                streak(linePoints({ x: at.x + i * 16, y: 0 }, { x: at.x + i * 10, y: at.y + 30 }, 12),
                       ['#fff8d0', '#ffe27a'], { step: 12, life: 360, size: GRID * 2 });
            }
            burst(at, ['#ffffff', '#ffe27a'], { count: 14, speed: 160, gravity: -60, life: 560 });
        },
        necrotic: function(at) {
            flash('flash-dark');
            for (var i = 0; i < 26; i++) {
                var a = rand(0, Math.PI * 2), r = rand(60, 96);
                spawn({ x: at.x + Math.cos(a) * r, y: at.y + Math.sin(a) * r,
                        vx: -Math.cos(a) * r * 2.2, vy: -Math.sin(a) * r * 2.2, gravity: 0,
                        life: 430, delay: rand(0, 160), size: pick([GRID, GRID * 2]),
                        color: pick(['#5a2a82', '#2a1640', '#9a5ad0', '#120a1c']) });
            }
            ring(at, '#9a5ad0', { r0: 70, r1: 8, life: 420 });
        },
        force: function(at) {
            ring(at, '#d08aff', { r1: 66, life: 320 });
            ring(at, '#ffffff', { r1: 40, life: 240 });
            burst(at, ['#d08aff', '#8a5ae0', '#ffffff'], { count: 18, speed: 240, gravity: 0, life: 420 });
        },
        psychic: function(at) {
            var head = { x: at.x, y: at.y - 34 };
            ring(head, '#ff8ad0', { r1: 34, life: 380 });
            ring(head, '#ff8ad0', { r1: 34, life: 380, delay: 150 });
            ring(head, '#ffd0f0', { r1: 34, life: 380, delay: 300 });
            burst(head, ['#ff8ad0', '#ffd0f0'], { count: 10, speed: 90, gravity: 0, life: 600 });
        },
        heal: function(at) {
            rise(at, ['#7af08a', '#b8ffc0', '#4ac860'], { count: 14, speed: 110, plus: true, sizes: [GRID] });
            ring({ x: at.x, y: at.y + 34 }, '#7af08a', { r1: 46, life: 520 });
        },
        regen: function(at) {
            rise(at, ['#7af08a', '#b8ffc0'], { count: 7, speed: 90, plus: true, sizes: [GRID] });
        },
        buff: function(at) {
            rise(at, ['#ffe27a', '#ffffff', '#e0b040'], { count: 18, speed: 170, sizes: [GRID] });
            ring({ x: at.x, y: at.y + 34 }, '#ffe27a', { r1: 50, life: 480 });
        },
        debuff: function(at) {
            for (var i = 0; i < 16; i++) {
                spawn({ x: at.x + rand(-34, 34), y: at.y - rand(40, 80), vx: 0, vy: rand(60, 130), gravity: 0,
                        life: rand(500, 800), delay: rand(0, 260), size: GRID,
                        color: pick(['#9a5ad0', '#5a2a82', '#d0a8ff']) });
            }
        },
        shield: function(at, dir) {
            streak(arcPoints({ x: at.x, y: at.y }, -dir, 44, -1.3, 1.3, 16),
                   ['#8ac4ff', '#ffffff', '#4a90e0'], { step: 14, life: 620 });
            ring(at, '#8ac4ff', { r0: 40, r1: 52, life: 520 });
        },
        stun: function(at) {
            var head = { x: at.x, y: at.y - 46 };
            for (var i = 0; i < 5; i++) {
                streak(arcPoints(head, 1, 26, i * 1.25, i * 1.25 + 2.6, 8), ['#ffe27a', '#ffffff'],
                       { step: 55, life: 240, size: GRID });
            }
        },
        rage: function(at) {
            flash('flash-dark');
            rise(at, ['#ff5a2a', '#c8343c', '#ffd84a'], { count: 26, speed: 220, shrink: true });
            ring(at, '#ff5a2a', { r1: 80, life: 420 });
        },
        bleed: function(at) {
            burst(at, ['#e0343c', '#8a1f2a', '#ff6a6a'],
                  { count: 14, speed: 70, gravity: 520, life: 700, from: 0, to: Math.PI });
        },
        burn: function(at) {
            rise(at, ['#ffd84a', '#ff9a3c', '#ff5a2a'], { count: 14, speed: 130, shrink: true });
        },
        impact: function(at) {
            burst(at, ['#ffffff', '#dfe8f5'], { count: 14, speed: 190, life: 360 });
        }
    };

    // Something flying from the actor to its target: an arrow, a bolt of fire
    function projectile(fromSide, key) {
        var a = actors[fromSide].point(0.45), b = actors[other(fromSide)].point(0.55);
        streak(linePoints(a, b, 22), SHOT_COLORS[key] || ['#ffffff', '#dfe8f5'],
               { step: 9, life: 150, size: SHOT_COLORS[key] ? GRID * 2 : GRID });
    }

    function playFx(key, side, fromSide) {
        var at = actors[side].point();
        var dir = fromSide === 'player' ? 1 : -1;
        (FX[key] || FX.impact)(at, dir);
    }


    // ===== Banner =====
    var banner = stage.querySelector('.stage-banner');
    var bannerTimer = null;
    function announce(text, side) {
        if (!text) return;
        banner.textContent = text;
        banner.className = 'stage-banner is-shown from-' + side;
        clearTimeout(bannerTimer);
        bannerTimer = setTimeout(function() { banner.classList.remove('is-shown'); }, 900);
    }


    // ===== Turn playback =====
    function applyHp(ev) {
        ['player', 'monster'].forEach(function(side) {
            var delta = ev[side];
            if (!delta) return;
            showHp(side, plates[side].hp + delta);
            actors[side].float((delta > 0 ? '+' : '') + delta,
                               delta > 0 ? 'float-heal' : (ev.outcome === 'crit' ? 'float-crit' : ''));
        });
    }

    function impact(ev) {
        var target = other(ev.actor);
        if (ev.outcome === 'miss') {
            actors[target].pulse('pose-dodge', 380);
            actors[target].float('Miss', 'float-miss');
            sfx('miss');
            return;
        }
        playFx(ev.fx, target, ev.actor);
        if (ev[target] < 0) actors[target].play('hurt');
        actors[target].pulse('is-hit', 300);
        if (ev.outcome === 'crit') {
            stage.classList.add('is-shaking');
            setTimeout(function() { stage.classList.remove('is-shaking'); }, 420);
            sfx('crit');
        } else {
            sfx(ev.kind === 'ability' ? 'spell' : 'hit');
        }
        if (ev.outcome === 'half') actors[target].float('Resisted', 'float-miss');
        applyHp(ev);
    }

    // Each kind returns how long to wait before the next event (ms)
    var KINDS = {
        attack: function(ev) {
            actors[ev.actor].play('attack');
            if (ev.ranged) projectile(ev.actor, ev.fx);
            else actors[ev.actor].pulse('pose-lunge', 460);
            setTimeout(function() { impact(ev); }, 230);
            return 760;
        },
        ability: function(ev) {
            var self = actors[ev.actor];
            if (ev.outcome === null) {          // on the user: heal, ward, war cry
                self.pulse('pose-cast', 520);
                playFx(ev.fx, ev.actor, ev.actor);
                sfx(ev.fx === 'heal' ? 'heal' : 'spell');
                applyHp(ev);
                return 760;
            }
            self.play('attack');
            self.pulse(ev.ranged ? 'pose-cast' : 'pose-lunge', 460);
            if (ev.ranged) setTimeout(function() { projectile(ev.actor, ev.fx); }, 90);
            setTimeout(function() { impact(ev); }, ev.ranged ? 310 : 230);
            return 860;
        },
        defend: function(ev) {
            playFx('shield', ev.actor, other(ev.actor));
            sfx('defend');
            return 560;
        },
        item: function(ev) {
            actors[ev.actor].pulse('pose-cast', 520);
            playFx('heal', ev.actor, ev.actor);
            sfx('heal');
            applyHp(ev);
            return 700;
        },
        flee: function(ev) {
            actors[ev.actor].pulse('pose-dodge', 380);
            actors[ev.actor].float('No escape', 'float-miss');
            return 560;
        },
        stunned: function(ev) {
            playFx('stun', ev.actor, ev.actor);
            actors[ev.actor].float('Stunned', 'float-miss');
            return 640;
        },
        condition: function(ev) {
            playFx(ev.fx, ev.actor, ev.actor);
            if (ev[ev.actor] < 0) actors[ev.actor].pulse('is-hit', 300);
            applyHp(ev);
            return 620;
        },
        enrage: function(ev) {
            playFx('rage', ev.actor, ev.actor);
            actors[ev.actor].pulse('pose-cast', 520);
            return 700;
        }
    };

    function finish() {
        showHp('player', finalHp.player);
        showHp('monster', finalHp.monster);
        var finale = stage.dataset.finale;
        if (finale === 'victory') actors.monster.die();
        if (finale === 'defeat') actors.player.die();
    }

    function playTurn(events) {
        var i = 0;
        (function next() {
            if (i >= events.length) { finish(); return; }
            var ev = events[i++];
            announce(ev.name, ev.actor);
            var wait = (KINDS[ev.kind] || KINDS.condition)(ev);
            setTimeout(next, wait);
        })();
    }

    var events = [];
    try { events = JSON.parse(stage.dataset.turnEvents || '[]'); } catch (e) { events = []; }
    var finalHp = { player: plates.player.hp, monster: plates.monster.hp };

    // Play each turn once: a refresh or the back button shows the result without replaying it
    var turnId = stage.dataset.battleKey + '#' + stage.dataset.turnSeq + (stage.dataset.finale || '');
    var seen = null;
    try { seen = sessionStorage.getItem('battleTurn'); } catch (e) { /* storage unavailable */ }
    try { sessionStorage.setItem('battleTurn', turnId); } catch (e) { /* storage unavailable */ }

    if (!events.length || seen === turnId || reducedMotion) {
        finish();
        if (seen === turnId || reducedMotion) {
            // The death has already been shown; go straight to the last frame
            ['player', 'monster'].forEach(function(side) {
                if (actors[side].dead) actors[side].el.classList.add('is-dead-still');
            });
        }
        return;
    }

    // Rewind the bars to where they stood before this turn, then play it forward
    events.forEach(function(ev) {
        plates.player.hp -= ev.player;
        plates.monster.hp -= ev.monster;
    });
    showHp('player', plates.player.hp, true);
    showHp('monster', plates.monster.hp, true);
    setTimeout(function() { playTurn(events); }, 250);
})();
