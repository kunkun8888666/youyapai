(function () {
    function init() {
        var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        var canvas = document.getElementById('bg-canvas');
        var ctx = canvas ? canvas.getContext('2d') : null;
        if (!canvas || !ctx) return;

        var W = 0, H = 0, DPR = 1;
        var lines = [];
        var dots = [];
        var sparkles = [];
        var lastTs = 0;
        var time = 0;

        var LINE_COUNT = 6;
        var LINE_COLORS = [
            [255, 107, 53],
            [255, 140, 90],
            [255, 160, 100],
            [255, 107, 53],
            [255, 193, 7],
            [255, 120, 70],
            [255, 150, 95],
            [255, 107, 53],
            [255, 170, 110],
            [255, 130, 80]
        ];

        function getDensity() {
            var area = W * H;
            return Math.min(Math.max(Math.floor(area / 12000), 50), 180);
        }

        function resize() {
            DPR = Math.min(window.devicePixelRatio || 1, 2);
            W = window.innerWidth;
            H = window.innerHeight;
            canvas.width = W * DPR;
            canvas.height = H * DPR;
            canvas.style.width = W + 'px';
            canvas.style.height = H + 'px';
            ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
            initAll();
        }

        function initAll() {
            initLines();
            initDots();
            sparkles = [];
            for (var i = 0; i < 40; i++) spawnSparkle(true);
        }

        function initLines() {
            lines = [];
            for (var i = 0; i < LINE_COUNT; i++) {
                var yBase = H * (0.08 + (i / (LINE_COUNT - 1)) * 0.84);
                lines.push({
                    yBase: yBase,
                    amp: 50 + Math.random() * 120,
                    freq: 0.002 + Math.random() * 0.004,
                    speed: 0.4 + Math.random() * 0.6,
                    phase: Math.random() * Math.PI * 2,
                    driftPhase: Math.random() * Math.PI * 2,
                    driftAmp: 20 + Math.random() * 30,
                    driftSpeed: 0.4 + Math.random() * 0.5,
                    width: 0.7 + Math.random() * 1.2,
                    alpha: 0.1 + Math.random() * 0.15,
                    colorIdx: i % LINE_COLORS.length,
                    pulseSpeed: 0.3 + Math.random() * 0.4,
                    pulseWidth: 100 + Math.random() * 180,
                    pulseAlpha: 0.3 + Math.random() * 0.25
                });
            }
        }

        function initDots() {
            dots = [];
            var count = getDensity();
            for (var i = 0; i < count; i++) {
                dots.push({
                    x: Math.random() * W,
                    y: Math.random() * H,
                    r: Math.random() * 1.0 + 0.3,
                    baseA: Math.random() * 0.25 + 0.1,
                    twinkleFreq: 0.8 + Math.random() * 2.5,
                    phase: Math.random() * Math.PI * 2
                });
            }
        }

        function waveY(line, x, t) {
            return line.yBase
                + Math.sin(x * line.freq + line.phase + t * line.speed) * line.amp
                + Math.sin(x * line.freq * 2.1 + line.phase * 1.3 + t * line.speed * 1.5) * line.amp * 0.35
                + Math.sin(t * line.driftSpeed + line.driftPhase) * line.driftAmp;
        }

        function drawSmoothLine(points) {
            ctx.moveTo(points[0].x, points[0].y);
            for (var i = 1; i < points.length - 1; i++) {
                var xc = (points[i].x + points[i + 1].x) / 2;
                var yc = (points[i].y + points[i + 1].y) / 2;
                ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
            }
            ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
        }

        function drawLines(t) {
            for (var li = 0; li < lines.length; li++) {
                var ln = lines[li];
                var col = LINE_COLORS[ln.colorIdx];
                var step = 12;
                var pts = [];
                for (var x = -30; x <= W + 30; x += step) {
                    pts.push({ x: x, y: waveY(ln, x, t) });
                }

                ctx.beginPath();
                drawSmoothLine(pts);
                ctx.strokeStyle = 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',' + ln.alpha + ')';
                ctx.lineWidth = ln.width;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.stroke();

                var rawPos = (t * ln.pulseSpeed) % 1.4;
                var pulsePos = rawPos - 0.2;
                var pulseX = pulsePos * (W + 200) - 100;
                var grad = ctx.createLinearGradient(pulseX - ln.pulseWidth, 0, pulseX + ln.pulseWidth, 0);
                grad.addColorStop(0, 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',0)');
                grad.addColorStop(0.5, 'rgba(255,210,160,' + ln.pulseAlpha + ')');
                grad.addColorStop(1, 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',0)');

                ctx.beginPath();
                drawSmoothLine(pts);
                ctx.strokeStyle = grad;
                ctx.lineWidth = ln.width * 2.2;
                ctx.stroke();
            }
        }

        function drawDots(dt, t) {
            ctx.globalCompositeOperation = 'lighter';
            for (var i = 0; i < dots.length; i++) {
                var d = dots[i];
                d.phase += d.twinkleFreq * dt;
                var a = d.baseA + Math.sin(d.phase) * d.baseA * 0.6;
                a = Math.max(0.03, a);
                ctx.beginPath();
                ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(255,140,90,' + a + ')';
                ctx.fill();
            }
        }

        function spawnSparkle(randomLife) {
            var r = Math.random();
            var tier = r < 0.25 ? 'big' : (r < 0.55 ? 'med' : 'small');
            var cfg = {
                big: { size: [1.8, 3.2], life: [0.9, 1.8], cross: false },
                med: { size: [1.2, 2.2], life: [0.5, 1.0], cross: false },
                small: { size: [0.5, 1.0], life: [0.3, 0.7], cross: false }
            }[tier];
            var ms = cfg.size[0] + Math.random() * (cfg.size[1] - cfg.size[0]);
            var ml = cfg.life[0] + Math.random() * (cfg.life[1] - cfg.life[0]);
            var sp = {
                x: Math.random() * W,
                y: Math.random() * H,
                r: 0, maxR: ms,
                a: 0,
                age: randomLife ? Math.random() * ml : 0,
                maxAge: ml,
                fadeIn: 0.2,
                fadeOut: 0.5,
                vx: (Math.random() - 0.5) * 8,
                vy: (Math.random() - 0.5) * 8,
                cross: cfg.cross,
                tier: tier
            };
            if (randomLife) {
                var p = Math.min(1, sp.age / sp.maxAge);
                if (p < sp.fadeIn) {
                    var e = p / sp.fadeIn;
                    sp.r = sp.maxR * (1 - Math.pow(1 - e, 3));
                    sp.a = 1 - Math.pow(1 - e, 3);
                } else if (p > 1 - sp.fadeOut) {
                    var e2 = Math.min(1, (p - (1 - sp.fadeOut)) / sp.fadeOut);
                    sp.r = sp.maxR * (1 - e2 * e2 * e2);
                    sp.a = 1 - e2 * e2 * e2;
                } else {
                    sp.r = sp.maxR;
                    sp.a = 1;
                }
            }
            sparkles.push(sp);
        }

        function drawCross(cx, cy, size, alpha) {
            var len = size * 2.2;
            var w = Math.max(1.2, size * 0.25);
            var g1 = ctx.createLinearGradient(cx - len, cy, cx + len, cy);
            g1.addColorStop(0, 'rgba(255,255,255,0)');
            g1.addColorStop(0.4, 'rgba(255,245,230,' + (alpha * 0.7) + ')');
            g1.addColorStop(0.5, 'rgba(255,255,255,' + alpha + ')');
            g1.addColorStop(0.6, 'rgba(255,245,230,' + (alpha * 0.7) + ')');
            g1.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = g1;
            ctx.fillRect(cx - len, cy - w / 2, len * 2, w);
            var g2 = ctx.createLinearGradient(cx, cy - len, cx, cy + len);
            g2.addColorStop(0, 'rgba(255,255,255,0)');
            g2.addColorStop(0.4, 'rgba(255,245,230,' + (alpha * 0.7) + ')');
            g2.addColorStop(0.5, 'rgba(255,255,255,' + alpha + ')');
            g2.addColorStop(0.6, 'rgba(255,245,230,' + (alpha * 0.7) + ')');
            g2.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = g2;
            ctx.fillRect(cx - w / 2, cy - len, w, len * 2);
            ctx.beginPath();
            ctx.arc(cx, cy, Math.max(0.5, size * 0.9), 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,255,255,' + Math.min(1, alpha * 1.5) + ')';
            ctx.fill();
        }

        function drawSparkles(dt) {
            var spawnChance = 5 * dt;
            if (dt > 0 && sparkles.length < 80 && Math.random() < spawnChance) {
                spawnSparkle();
            }
            if (dt <= 0) return;

            for (var i = sparkles.length - 1; i >= 0; i--) {
                var s = sparkles[i];
                s.age += dt;
                s.x += s.vx * dt;
                s.y += s.vy * dt;
                var p = s.age / s.maxAge;

                if (p < s.fadeIn) {
                    var e = p / s.fadeIn;
                    s.r = s.maxR * (1 - Math.pow(1 - e, 3));
                    s.a = 1 - Math.pow(1 - e, 3);
                } else if (p > 1 - s.fadeOut) {
                    var e2 = Math.min(1, (p - (1 - s.fadeOut)) / s.fadeOut);
                    s.r = s.maxR * (1 - e2 * e2 * e2);
                    s.a = 1 - e2 * e2 * e2;
                } else {
                    s.r = s.maxR;
                    s.a = 1;
                }
                s.r = Math.max(0, s.r);
                s.a = Math.max(0, s.a);

                var gr = Math.max(0.5, s.r * (s.cross ? 10 : (s.tier === 'med' ? 7 : 4)));
                var g = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, gr);
                var coreA = Math.min(1, s.a * 1.3);
                g.addColorStop(0, 'rgba(255,255,255,' + coreA + ')');
                g.addColorStop(0.12, 'rgba(255,220,180,' + s.a + ')');
                g.addColorStop(0.35, 'rgba(255,140,90,' + (s.a * 0.45) + ')');
                g.addColorStop(0.7, 'rgba(255,107,53,' + (s.a * 0.1) + ')');
                g.addColorStop(1, 'rgba(255,107,53,0)');
                ctx.beginPath();
                ctx.arc(s.x, s.y, gr, 0, Math.PI * 2);
                ctx.fillStyle = g;
                ctx.fill();

                if (s.cross) {
                    drawCross(s.x, s.y, s.r, s.a);
                } else {
                    ctx.beginPath();
                    ctx.arc(s.x, s.y, Math.max(0.5, s.r), 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(255,240,220,' + s.a + ')';
                    ctx.fill();
                }

                if (s.age >= s.maxAge) sparkles.splice(i, 1);
            }
            ctx.globalCompositeOperation = 'source-over';
        }

        // 页面不可见时暂停渲染，节省资源
        var running = true;
        document.addEventListener('visibilitychange', function () {
            running = !document.hidden;
            if (running) { lastTs = 0; requestAnimationFrame(frame); }
        });

        function frame(ts) {
            if (!running) return;
            requestAnimationFrame(frame);
            if (!lastTs) lastTs = ts;
            var dt = Math.min((ts - lastTs) / 1000, 0.05);
            lastTs = ts;

            var animScale = prefersReduced ? 0.15 : 1;
            time += dt * animScale;
            ctx.clearRect(0, 0, W, H);
            drawLines(time);
            drawDots(dt * animScale, time);
            drawSparkles(dt * animScale);
        }

        window.addEventListener('resize', resize, { passive: true });
        resize();
        requestAnimationFrame(frame);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
