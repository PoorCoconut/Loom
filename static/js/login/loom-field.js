/* Drifting story nodes behind the login card. Calm by design:
   few nodes, slow drift, faint threads. The cursor gently draws nearby nodes in. */
(() => {
  const canvas = document.getElementById('loom-field');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const GOLD = [217, 169, 78], LILAC = [185, 166, 245];
  const LINK = 150, REACH = 190;
  let w = 0, h = 0, dpr = 1, nodes = [], pulse = null, last = 0, raf = 0;
  const mouse = { x: -9999, y: -9999, on: false };

  const rand = (a, b) => a + Math.random() * (b - a);
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth; h = window.innerHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round(Math.min(46, Math.max(18, (w * h) / 30000)));
    nodes = Array.from({ length: count }, () => ({
      x: rand(0, w), y: rand(0, h), vx: rand(-.12, .12), vy: rand(-.12, .12),
      r: rand(1.8, 4.2), c: Math.random() < .7 ? GOLD : LILAC, ph: rand(0, 6.28),
      hollow: Math.random() < .35,
    }));
    if (reduce) draw(0);
  }

  function step(dt) {
    for (const n of nodes) {
      if (mouse.on) { // a soft pull toward the cursor, nothing dramatic
        const dx = mouse.x - n.x, dy = mouse.y - n.y, d = Math.hypot(dx, dy);
        if (d < REACH && d > 1) { const f = (1 - d / REACH) * 0.006 * dt; n.vx += (dx / d) * f; n.vy += (dy / d) * f; }
      }
      const sp = Math.hypot(n.vx, n.vy), max = .35;
      if (sp > max) { n.vx *= max / sp; n.vy *= max / sp; }
      n.vx *= .998; n.vy *= .998;
      n.x += n.vx * dt * .06 * 16 / 16; n.y += n.vy * dt * .06 * 16 / 16;
      if (n.x < -20) n.x = w + 20; if (n.x > w + 20) n.x = -20;
      if (n.y < -20) n.y = h + 20; if (n.y > h + 20) n.y = -20;
    }
  }

  function draw(t) {
    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 1;
    const links = [];
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j], d = Math.hypot(a.x - b.x, a.y - b.y);
      if (d < LINK) {
        const al = (1 - d / LINK) * .22;
        ctx.strokeStyle = rgba(LILAC, al); ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        links.push([a, b]);
      }
    }
    if (mouse.on) for (const n of nodes) {
      const d = Math.hypot(mouse.x - n.x, mouse.y - n.y);
      if (d < REACH) { ctx.strokeStyle = rgba(GOLD, (1 - d / REACH) * .45); ctx.beginPath(); ctx.moveTo(n.x, n.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke(); }
    }
    for (const n of nodes) {
      const glow = .55 + .25 * Math.sin(t / 1400 + n.ph);
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, 6.283);
      if (n.hollow) { ctx.strokeStyle = rgba(n.c, glow); ctx.lineWidth = 1.4; ctx.stroke(); ctx.lineWidth = 1; }
      else { ctx.fillStyle = rgba(n.c, glow); ctx.shadowColor = rgba(n.c, .6); ctx.shadowBlur = 8; ctx.fill(); ctx.shadowBlur = 0; }
    }
    // one small "story spark" travelling along a thread at a time
    if (!reduce) {
      if (!pulse && links.length && t % 3000 < 40) { const [a, b] = links[Math.floor(Math.random() * links.length)]; pulse = { a, b, t0: t }; }
      if (pulse) {
        const p = (t - pulse.t0) / 1500;
        if (p >= 1) pulse = null;
        else { const x = pulse.a.x + (pulse.b.x - pulse.a.x) * p, y = pulse.a.y + (pulse.b.y - pulse.a.y) * p;
          ctx.beginPath(); ctx.arc(x, y, 2.6, 0, 6.283); ctx.fillStyle = 'rgba(255,243,212,.9)'; ctx.shadowColor = '#f0cf86'; ctx.shadowBlur = 12; ctx.fill(); ctx.shadowBlur = 0; }
      }
    }
  }

  function loop(t) {
    const dt = Math.min(t - last || 16, 50); last = t;
    step(dt); draw(t); raf = requestAnimationFrame(loop);
  }

  window.addEventListener('resize', resize);
  window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; mouse.on = true; }, { passive: true });
  window.addEventListener('mouseleave', () => { mouse.on = false; });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) cancelAnimationFrame(raf); else if (!reduce) { last = 0; raf = requestAnimationFrame(loop); }
  });
  resize();
  if (!reduce) raf = requestAnimationFrame(loop);
})();
