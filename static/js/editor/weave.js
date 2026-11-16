/* Weave: horizontal branching-story graph. Editor mode + Reader mode in one screen. */
(() => {
  'use strict';

  /* ------------------------------------------------------------------ boot */
  const boot = JSON.parse(document.getElementById('weave-data').textContent);
  const CSRF = document.querySelector('meta[name="csrf-token"]').content;
  const NW = 240, NH = 108, COLX = 350, ROWY = 150;
  const REQ = { eq: '=', neq: '≠', gt: '>', gte: '≥', lt: '<', lte: '≤' };
  const REQ_WORDS = { eq: 'equals', neq: 'does not equal', gt: 'greater than', gte: 'at least', lt: 'less than', lte: 'at most' };
  const MOD = { set: 'set to', add: 'add', subtract: 'subtract', toggle: 'toggle' };

  const S = {
    story: boot.story,
    nodes: new Map(boot.nodes.map(n => [n.id, n])),
    paths: new Map(boot.paths.map(p => [p.id, p])),
    vars: boot.variables.slice(),
    canEdit: boot.canEdit,
    mode: boot.canEdit ? 'edit' : 'read',
    selNode: null, selPath: null,
    view: { x: 60, y: 60, k: 1 },
    wide: false, branchKind: 'new', showMap: !!(boot.prefs && boot.prefs.revealMap),
    read: null,
  };

  const $ = id => document.getElementById(id);
  const root = $('weave'), stage = $('stage'), world = $('world'), nodesEl = $('nodes'),
        labelsEl = $('labels'), threadsG = $('threads-g'), ghost = $('ghost-thread'),
        panel = $('panel'), toastEl = $('toast');
  const NS = 'http://www.w3.org/2000/svg';

  /* ------------------------------------------------------------------ helpers */
  const h = (tag, props, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') e.className = v;
      else if (k === 'on') for (const [ev, fn] of Object.entries(v)) e.addEventListener(ev, fn);
      else if (k === 'dataset') Object.assign(e.dataset, v);
      else if (k in e) e[k] = v;
      else e.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid == null || kid === false) continue;
      e.append(kid.nodeType ? kid : document.createTextNode(kid));
    }
    return e;
  };
  const svgEl = (tag, attrs) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
    return e;
  };

  let toastTimer;
  function toast(msg, isError) {
    toastEl.textContent = msg;
    toastEl.classList.toggle('is-error', !!isError);
    toastEl.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('is-on'), isError ? 3800 : 1800);
  }

  async function api(method, path, body) {
    let res;
    try {
      res = await fetch(boot.apiBase + path, {
        method, keepalive: true,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (e) { toast('Could not reach the server.', true); throw e; }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { toast(data.error || 'Something went wrong.', true); throw new Error(data.error || res.status); }
    return data;
  }

  const outgoing = id => [...S.paths.values()].filter(p => p.source === id);
  const incoming = id => [...S.paths.values()].filter(p => p.target === id);
  const kidsOf = id => [...new Set(outgoing(id).map(p => p.target))];
  const isEnding = id => outgoing(id).length === 0;
  const varById = id => S.vars.find(v => v.id === id);
  const nodeTitle = id => (S.nodes.get(id) || {}).title || 'Untitled';
  const words = t => (t.trim().match(/\S+/g) || []).length;

  /* ------------------------------------------------------------------ auto layout */
  function autoLayout() {
    const ids = [...S.nodes.keys()];
    if (!ids.length) return;
    const hasIn = new Set(); S.paths.forEach(p => hasIn.add(p.target));
    const roots = [];
    if (S.story.start && S.nodes.has(S.story.start)) roots.push(S.story.start);
    ids.forEach(id => { if (!hasIn.has(id) && !roots.includes(id)) roots.push(id); });

    const depth = new Map(), stack = new Set();
    const dfs = (id, d) => {
      if (stack.has(id) || (depth.get(id) ?? -1) >= d) return;
      depth.set(id, d); stack.add(id);
      kidsOf(id).forEach(t => dfs(t, d + 1));
      stack.delete(id);
    };
    roots.forEach(r => dfs(r, 0));
    ids.forEach(id => { if (!depth.has(id)) { roots.push(id); dfs(id, 0); } });

    const placed = new Set(); let row = 0;
    const place = id => {
      placed.add(id);
      const n = S.nodes.get(id); n.x = depth.get(id) * COLX;
      const kids = kidsOf(id).filter(k => !placed.has(k) && depth.get(k) === depth.get(id) + 1);
      const ys = kids.map(place).filter(y => y != null);
      n.y = ys.length ? Math.round((ys[0] + ys[ys.length - 1]) / 2) : (row++) * ROWY;
      return n.y;
    };
    roots.forEach(r => { if (!placed.has(r)) place(r); });
    ids.forEach(id => { if (!placed.has(id)) place(id); });

    const cols = new Map();
    ids.forEach(id => { const n = S.nodes.get(id); (cols.get(n.x) || cols.set(n.x, []).get(n.x)).push(n); });
    cols.forEach(list => {
      list.sort((a, b) => a.y - b.y);
      for (let i = 1; i < list.length; i++) if (list[i].y < list[i - 1].y + ROWY) list[i].y = list[i - 1].y + ROWY;
    });
  }

  function freeSpot(x, y) {
    const clash = () => [...S.nodes.values()].some(n => Math.abs(n.x - x) < NW + 30 && Math.abs(n.y - y) < NH + 30);
    let guard = 0; while (clash() && guard++ < 60) y += ROWY;
    return { x: Math.round(x), y: Math.round(y) };
  }

  const savePositions = ids => api('POST', '/positions/', {
    positions: ids.map(id => ({ id, x: S.nodes.get(id).x, y: S.nodes.get(id).y })),
  }).catch(() => {});

  /* ------------------------------------------------------------------ camera */
  function applyView(glide) {
    world.classList.toggle('is-gliding', !!glide);
    world.style.transform = `translate(${S.view.x}px, ${S.view.y}px) scale(${S.view.k})`;
  }
  function zoomAt(factor, cx, cy) {
    const k = Math.min(2, Math.max(0.2, S.view.k * factor)), r = k / S.view.k;
    S.view.x = cx - (cx - S.view.x) * r; S.view.y = cy - (cy - S.view.y) * r; S.view.k = k;
    applyView();
  }
  function fitView(glide = true) {
    const ns = [...S.nodes.values()]; if (!ns.length) return;
    const r = stage.getBoundingClientRect(), pad = 90;
    const minX = Math.min(...ns.map(n => n.x)), maxX = Math.max(...ns.map(n => n.x)) + NW;
    const minY = Math.min(...ns.map(n => n.y)), maxY = Math.max(...ns.map(n => n.y)) + NH;
    const k = Math.min(1.1, Math.max(0.25, Math.min((r.width - pad * 2) / (maxX - minX), (r.height - pad * 2) / (maxY - minY))));
    S.view = { k, x: (r.width - (maxX - minX) * k) / 2 - minX * k, y: (r.height - (maxY - minY) * k) / 2 - minY * k };
    applyView(glide);
  }
  function focusNode(id) {
    const n = S.nodes.get(id); if (!n) return;
    const r = stage.getBoundingClientRect(), k = Math.max(0.8, Math.min(1.1, S.view.k));
    S.view = { k, x: r.width / 2 - (n.x + NW / 2) * k, y: r.height / 2 - (n.y + NH / 2) * k };
    applyView(true);
  }
  const toWorld = (cx, cy) => {
    const r = stage.getBoundingClientRect();
    return { x: (cx - r.left - S.view.x) / S.view.k, y: (cy - r.top - S.view.y) / S.view.k };
  };

  /* ------------------------------------------------------------------ graph rendering */
  const nodeEls = new Map();

  function nodeKind(id) {
    const cls = [];
    if (S.story.start === id) cls.push('node--start');
    if (isEnding(id)) cls.push('node--ending'); else if (outgoing(id).length > 1) cls.push('node--branch');
    return cls;
  }
  const kindLabel = id => S.story.start === id && isEnding(id) ? 'Opening · ending'
    : S.story.start === id ? 'Opening' : isEnding(id) ? 'Ending'
    : outgoing(id).length > 1 ? `${outgoing(id).length} branches` : 'One path';

  function readSets() {
    if (!S.read) return { visited: new Set(), walked: new Set(), current: null };
    const visited = new Set([S.read.current]), walked = new Set();
    S.read.hist.forEach(e => { visited.add(e.node); walked.add(e.path); });
    return { visited, walked, current: S.read.current };
  }
  const fogOn = () => S.mode === 'read' && (!S.canEdit || !S.showMap);

  function renderNodes() {
    const rs = readSets(), reading = S.mode === 'read';
    for (const [id, el] of nodeEls) if (!S.nodes.has(id)) { el.remove(); nodeEls.delete(id); }
    for (const n of S.nodes.values()) {
      let el = nodeEls.get(n.id);
      if (!el) {
        el = h('div', { class: 'node', dataset: { id: n.id } },
          h('div', { class: 'node__top' }, h('i', { class: 'node__badge' }), h('span', { class: 'js-kind' })),
          h('div', { class: 'node__title' }), h('div', { class: 'node__snippet' }),
          h('button', { class: 'node__handle', title: 'Drag to connect or create a branch', tabindex: -1 }, '+'));
        nodeEls.set(n.id, el); nodesEl.append(el);
      }
      el.className = ['node', ...nodeKind(n.id)].join(' ');
      el.style.left = n.x + 'px'; el.style.top = n.y + 'px';
      el.querySelector('.js-kind').textContent = kindLabel(n.id);
      el.querySelector('.node__title').textContent = n.title || 'Untitled scene';
      const sn = el.querySelector('.node__snippet');
      sn.textContent = n.text.trim() || 'Nothing written yet…';
      sn.classList.toggle('is-empty', !n.text.trim());
      if (!reading) el.classList.toggle('is-selected', S.selNode === n.id);
      else {
        const seen = rs.visited.has(n.id);
        el.classList.toggle('is-visited', seen && n.id !== rs.current);
        el.classList.toggle('is-current', n.id === rs.current);
        if (fogOn()) el.classList.toggle('is-fogged', !seen);
        else el.classList.toggle('is-dim', !seen);
      }
    }
  }

  const curve = (a, b) => {
    const x1 = a.x + NW, y1 = a.y + NH / 2, x2 = b.x - 4, y2 = b.y + NH / 2;
    const c = Math.max(80, Math.abs(x2 - x1) / 2);
    return { d: `M${x1} ${y1} C${x1 + c} ${y1} ${x2 - c} ${y2} ${x2} ${y2}`,
             mx: (x1 + 3 * (x1 + c) + 3 * (x2 - c) + x2) / 8, my: (y1 * 4 + y2 * 4) / 8 };
  };

  function renderThreads() {
    threadsG.replaceChildren(); labelsEl.replaceChildren();
    const rs = readSets(), reading = S.mode === 'read';
    for (const p of S.paths.values()) {
      const a = S.nodes.get(p.source), b = S.nodes.get(p.target); if (!a || !b) continue;
      const g = curve(a, b);
      const walked = reading && rs.walked.has(p.id);
      const sel = !reading && (S.selPath === p.id || S.selNode === p.source);
      const cls = ['thread-group'];
      if (walked) cls.push('is-walked');
      if (sel) cls.push('is-selected');
      if (reading && !walked) cls.push('is-dim');
      if (p.conditions.some(c => c.req)) cls.push('is-locked');
      const grp = svgEl('g', { class: cls.join(' ') });
      const line = svgEl('path', { class: 'thread', d: g.d, 'marker-end': `url(#${walked || sel ? 'arrow-gold' : 'arrow'})` });
      const hit = svgEl('path', { class: 'thread-hit', d: g.d });
      if (!reading) hit.addEventListener('click', e => { e.stopPropagation(); selectPath(p.id); });
      grp.append(line, hit); threadsG.append(grp);

      const lbl = h('div', { class: 'label' + (S.selPath === p.id && !reading ? ' is-selected' : '') + (walked ? ' is-walked' : '') + (reading && !walked ? ' is-dim' : ''),
        title: p.text, on: reading ? {} : { click: e => { e.stopPropagation(); selectPath(p.id); } } },
        p.conditions.some(c => c.req) ? h('span', { class: 'lock' }, '⚿') : null, p.text || '…');
      lbl.style.left = g.mx + 'px'; lbl.style.top = g.my + 'px';
      labelsEl.append(lbl);
    }
  }

  function renderStats() {
    const ends = [...S.nodes.keys()].filter(isEnding).length;
    $('stats').replaceChildren(
      h('span', { class: 'chip' }, `${S.nodes.size} scenes`),
      h('span', { class: 'chip' }, `${S.paths.size} choices`),
      h('span', { class: 'chip chip--gold' }, `${ends} endings`));
    $('empty-state').hidden = S.nodes.size > 0;
    $('status-eyebrow').textContent = S.mode === 'read' ? 'Reading' : (S.story.published ? 'Published · weaving' : 'Weaving · draft');
  }

  function renderGraph() { renderNodes(); renderThreads(); renderStats(); world.classList.toggle('fog', fogOn()); }

  /* ------------------------------------------------------------------ selection */
  function selectNode(id, opts = {}) {
    flushSaves();
    S.selNode = id; S.selPath = opts.path ?? null;
    renderGraph(); renderPanel();
    if (opts.scrollToPath) panel.querySelector('.choice.is-selected')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  function selectPath(pid) { const p = S.paths.get(pid); if (p) selectNode(p.source, { path: pid, scrollToPath: true }); }
  const deselect = () => { flushSaves(); S.selNode = null; S.selPath = null; renderGraph(); renderPanel(); };

  /* ------------------------------------------------------------------ autosave */
  const pending = new Map(); // nodeId -> {patch, timer}
  const statusEl = () => panel.querySelector('.panel__status');
  function setStatus(text, cls) { const s = statusEl(); if (s) { s.textContent = text; s.className = 'panel__status ' + (cls || ''); } }

  function queueSave(id, patch, delay = 700) {
    const entry = pending.get(id) || { patch: {} };
    Object.assign(entry.patch, patch);
    clearTimeout(entry.timer);
    entry.timer = setTimeout(() => commit(id), delay);
    pending.set(id, entry);
    setStatus('Unsaved…', 'is-saving');
  }
  async function commit(id) {
    const entry = pending.get(id); if (!entry) return;
    pending.delete(id); clearTimeout(entry.timer);
    setStatus('Saving…', 'is-saving');
    try { await api('PATCH', `/nodes/${id}/`, entry.patch); setStatus('Saved ✓'); }
    catch (e) { setStatus('Not saved', 'is-error'); }
  }
  function flushSaves() { [...pending.keys()].forEach(commit); }
  window.addEventListener('beforeunload', flushSaves);

  /* ------------------------------------------------------------------ mutations */
  async function createNode({ x, y, parent, choice, title }) {
    const data = await api('POST', '/nodes/', { title: title || 'Untitled scene', x, y, parent, choice_text: choice });
    const n = data.node; S.nodes.set(n.id, n);
    if (data.start) S.story.start = data.start;
    if (data.path) S.paths.set(data.path.id, data.path);
    return data;
  }
  async function linkNodes(source, target, text) {
    const data = await api('POST', '/paths/', { source, target, text: text || 'Continue' });
    S.paths.set(data.path.id, data.path); return data.path;
  }
  async function deleteNode(id) {
    if (!confirm(`Delete “${nodeTitle(id)}” and every thread connected to it?`)) return;
    await api('DELETE', `/nodes/${id}/`);
    [...S.paths.values()].forEach(p => { if (p.source === id || p.target === id) S.paths.delete(p.id); });
    S.nodes.delete(id); pending.delete(id);
    if (S.story.start === id) S.story.start = null;
    deselect(); toast('Scene removed');
  }

  /* ------------------------------------------------------------------ edit panel */
  function renderPanel() {
    const top = panel.scrollTop;
    panel.className = 'panel' + (S.mode === 'read' ? ' panel--read' : '');
    root.classList.toggle('panel-wide', S.mode === 'edit' && S.wide);
    panel.replaceChildren(S.mode === 'read' ? readerView() : (S.selNode && S.nodes.has(S.selNode) ? nodePanel(S.nodes.get(S.selNode)) : overviewPanel()));
    panel.scrollTop = S.mode === 'read' ? 0 : top;
  }

  function overviewPanel() {
    const ends = [...S.nodes.keys()].filter(isEnding).length;
    const branches = [...S.nodes.keys()].filter(id => outgoing(id).length > 1).length;
    const startN = S.story.start && S.nodes.get(S.story.start);
    const varName = h('input', { type: 'text', placeholder: 'variable_name', maxLength: 100 });
    const varType = h('select', {}, h('option', { value: 'int' }, 'number'), h('option', { value: 'bool' }, 'yes / no'), h('option', { value: 'string' }, 'text'));
    const varDef = h('input', { type: 'text', placeholder: 'start value' });
    const addVar = async () => {
      try {
        const d = await api('POST', '/variables/', { name: varName.value, type: varType.value, default: varDef.value });
        S.vars.push(d.variable); renderPanel();
      } catch (e) {}
    };
    return h('div', { class: 'panel__inner' },
      h('div', { class: 'panel__row panel__row--between' },
        h('span', { class: 'chip chip--gold' }, '✦ Story overview'),
        h('span', { class: 'panel__hint' }, S.story.published ? 'Published' : 'Draft')),
      h('h2', { style: 'font-size:2.2rem;margin:.8rem 0 .2rem' }, S.story.title),
      h('p', { class: 'panel__hint' }, S.story.synopsis || 'No synopsis yet.'),
      h('div', { class: 'stat-grid' },
        stat(S.nodes.size, 'Scenes'), stat(branches, 'Forks'), stat(ends, 'Endings')),
      h('div', { class: 'panel__sub' }, 'Opening scene'),
      startN
        ? h('div', { class: 'panel__row' }, h('span', {}, startN.title),
            h('button', { class: 'btn btn--sm', on: { click: () => { selectNode(startN.id); focusNode(startN.id); } } }, 'Go to it'))
        : h('p', { class: 'panel__hint' }, 'No opening scene yet — select a scene and choose “Make this the opening”.'),
      h('div', { class: 'panel__sub' }, 'Story variables'),
      h('p', { class: 'panel__hint' }, 'Things your readers carry along (gold, a key, trust…). Choices can require or change them.'),
      h('div', { style: 'margin-top:.7rem' }, S.vars.length ? S.vars.map(v =>
        h('div', { class: 'var-row' }, h('code', {}, v.name), h('span', { class: 'chip' }, v.type === 'int' ? 'number' : v.type === 'bool' ? 'yes/no' : 'text'),
          h('small', {}, `starts at ${v.default || '—'}`),
          h('button', { class: 'icon-btn', title: 'Delete variable', on: { click: async () => {
            if (!confirm(`Delete “${v.name}” and the conditions that use it?`)) return;
            await api('DELETE', `/variables/${v.id}/`).catch(() => null);
            S.vars = S.vars.filter(x => x.id !== v.id);
            S.paths.forEach(p => { p.conditions = p.conditions.filter(c => c.variable !== v.id); });
            renderGraph(); renderPanel();
          } } }, '×'))) : null),
      h('div', { class: 'var-form' }, varName, varType, varDef, h('button', { class: 'btn btn--sm', on: { click: addVar } }, 'Add')),
      h('div', { class: 'panel__sub' }, 'Tips'),
      h('p', { class: 'panel__hint' }, 'Click a scene to write it. Drag the golden + out of a scene to grow a branch (drop on empty space for a new scene, or on another scene to link them). Scroll to zoom, drag the background to pan.'));
  }
  const stat = (n, l) => h('div', { class: 'stat' }, h('b', {}, n), h('span', {}, l));

  function nodePanel(n) {
    const outs = outgoing(n.id);
    const title = h('input', { class: 'title-input', type: 'text', value: n.title, maxLength: 150, placeholder: 'Scene title',
      on: { input: e => { n.title = e.target.value; nodeEls.get(n.id).querySelector('.node__title').textContent = n.title || 'Untitled scene'; queueSave(n.id, { title: n.title }, 600); } } });
    const count = h('span', { class: 'count' }, `${words(n.text)} words`);
    const ta = h('textarea', { placeholder: 'Once upon a thread…  Write what happens in this scene. The reader sees exactly this.',
      spellcheck: true, on: { input: e => {
        n.text = e.target.value; count.textContent = `${words(n.text)} words`;
        const sn = nodeEls.get(n.id).querySelector('.node__snippet'); sn.textContent = n.text.trim() || 'Nothing written yet…'; sn.classList.toggle('is-empty', !n.text.trim());
        queueSave(n.id, { text: n.text });
      } } });
    ta.value = n.text;

    const isStart = S.story.start === n.id;
    return h('div', { class: 'panel__inner' },
      h('div', { class: 'panel__row panel__row--between' },
        h('button', { class: 'btn btn--ghost btn--sm', on: { click: deselect } }, '← Overview'),
        h('span', { class: 'chip' + (isEnding(n.id) ? '' : ' chip--moss') }, kindLabel(n.id)),
        h('span', { class: 'panel__status' }, 'Saved ✓'),
        h('button', { class: 'btn btn--ghost btn--sm', title: 'Wider writing space', on: { click: () => { S.wide = !S.wide; renderPanel(); } } }, S.wide ? '⇥ Narrow' : '⇤ Wide')),
      title,
      h('div', { class: 'scroll-field' }, ta, count),

      h('div', { class: 'panel__sub' }, `Where it leads · ${outs.length}`),
      outs.length === 0 ? h('p', { class: 'panel__hint' }, 'No paths yet — this scene is an ending. Add a branch below to continue the story.') : null,
      outs.map(choiceRow),
      branchForm(n),

      h('div', { class: 'panel__sub' }, 'Scene extras'),
      h('div', { class: 'stack' },
        extra('Image URL', 'url', n.image, v => { n.image = v; queueSave(n.id, { image: v }, 400); }),
        extra('Audio URL', 'url', n.audio, v => { n.audio = v; queueSave(n.id, { audio: v }, 400); })),

      h('div', { class: 'panel__sub' }, 'Scene actions'),
      h('div', { class: 'panel__row' },
        h('button', { class: 'btn', disabled: isStart, on: { click: async () => { await api('POST', '/start/', { node: n.id }).catch(() => null); S.story.start = n.id; renderGraph(); renderPanel(); toast('This is now the opening scene'); } } }, isStart ? '✦ This is the opening' : 'Make this the opening'),
        h('button', { class: 'btn btn--danger', on: { click: () => deleteNode(n.id) } }, 'Delete scene')));
  }

  const extra = (label, type, val, onChange) =>
    h('label', {}, label, h('input', { type, value: val || '', placeholder: 'https://…', on: { input: e => onChange(e.target.value) } }));

  function choiceRow(p) {
    const sel = h('select', { on: { change: async e => {
      const d = await api('PATCH', `/paths/${p.id}/`, { target: +e.target.value }).catch(() => null);
      if (d) { Object.assign(p, { target: d.path.target }); renderGraph(); renderPanel(); }
    } } }, [...S.nodes.values()].filter(x => x.id !== p.source).map(x => h('option', { value: x.id, selected: x.id === p.target }, x.title || 'Untitled')));
    sel.value = p.target;
    const txt = h('input', { type: 'text', value: p.text, maxLength: 255, placeholder: 'What the reader chooses…', on: {
      input: e => { p.text = e.target.value; renderThreads(); },
      change: e => api('PATCH', `/paths/${p.id}/`, { text: e.target.value }).catch(() => null) } });

    return h('div', { class: 'choice' + (S.selPath === p.id ? ' is-selected' : '') },
      h('div', { class: 'choice__head' }, h('span', { class: 'choice__arrow' }, '↳'), txt,
        h('button', { class: 'icon-btn', title: 'Cut this thread', on: { click: async () => {
          await api('DELETE', `/paths/${p.id}/`).catch(() => null);
          if (!S.paths.has(p.id)) return; S.paths.delete(p.id); if (S.selPath === p.id) S.selPath = null; renderGraph(); renderPanel();
        } } }, '×')),
      h('div', { class: 'choice__target' }, 'leads to', sel,
        h('button', { class: 'btn btn--sm', on: { click: () => { selectNode(p.target); focusNode(p.target); } } }, 'Open')),
      conditionBlock(p));
  }

  function conditionBlock(p) {
    const label = c => {
      const v = varById(c.variable); const name = v ? v.name : '?';
      return [c.req ? `needs ${name} ${REQ[c.req]} ${c.value}` : null,
              c.mod ? (c.mod === 'toggle' ? `toggles ${name}` : `${name}: ${MOD[c.mod]} ${c.value}`) : null].filter(Boolean).join(' · ');
    };
    const chips = p.conditions.map(c => h('span', { class: 'chip chip--gold' }, label(c),
      h('button', { title: 'Remove', on: { click: async () => {
        await api('DELETE', `/conditions/${c.id}/`).catch(() => null);
        p.conditions = p.conditions.filter(x => x.id !== c.id); renderGraph(); renderPanel();
      } } }, '×')));

    let form = null;
    if (!S.vars.length) form = h('p', { class: 'panel__hint' }, 'Add a story variable in the overview to give this choice conditions.');
    else {
      const v = h('select', {}, S.vars.map(x => h('option', { value: x.id }, x.name)));
      const rq = h('select', {}, h('option', { value: '' }, 'no requirement'), Object.entries(REQ_WORDS).map(([k, t]) => h('option', { value: k }, 'needs: ' + t)));
      const md = h('select', {}, h('option', { value: '' }, 'no change'), Object.entries(MOD).map(([k, t]) => h('option', { value: k }, 'then: ' + t)));
      const val = h('input', { type: 'text', placeholder: 'value' });
      form = h('div', { class: 'cond-form' }, v, rq, md, val, h('button', { class: 'btn btn--sm', on: { click: async () => {
        const d = await api('POST', `/paths/${p.id}/conditions/`, { variable: +v.value, req: rq.value, mod: md.value, value: val.value }).catch(() => null);
        if (d) { p.conditions.push(d.condition); renderGraph(); renderPanel(); }
      } } }, 'Add'));
    }
    return h('details', { class: 'cond-box', open: p.conditions.length > 0 },
      h('summary', {}, p.conditions.length ? `Conditions (${p.conditions.length})` : 'Add a condition'),
      h('div', { class: 'conds' }, chips), form);
  }

  function branchForm(n) {
    const isNew = S.branchKind === 'new';
    const choice = h('input', { type: 'text', placeholder: 'Choice text — what the reader sees', maxLength: 255 });
    const name = h('input', { type: 'text', placeholder: 'Title of the new scene', maxLength: 150 });
    const targets = [...S.nodes.values()].filter(x => x.id !== n.id);
    const existing = h('select', {}, targets.map(x => h('option', { value: x.id }, x.title || 'Untitled')));
    const go = h('button', { class: 'btn btn--gold', on: { click: async () => {
      try {
        if (isNew) {
          const pos = freeSpot(n.x + COLX, n.y + outgoing(n.id).length * ROWY);
          const d = await createNode({ ...pos, parent: n.id, choice: choice.value || 'Continue', title: name.value || 'Untitled scene' });
          renderGraph(); selectNode(d.node.id); focusNode(d.node.id);
        } else {
          if (!existing.value) return toast('There is no other scene to link to yet.', true);
          const p = await linkNodes(n.id, +existing.value, choice.value);
          selectNode(n.id, { path: p.id }); renderGraph();
        }
      } catch (e) {}
    } } }, isNew ? 'Weave new scene' : 'Link thread');
    return h('div', { class: 'branch-add' },
      h('div', { class: 'seg' },
        h('button', { class: isNew ? 'is-active' : '', on: { click: () => { S.branchKind = 'new'; renderPanel(); } } }, 'New scene'),
        h('button', { class: !isNew ? 'is-active' : '', on: { click: () => { S.branchKind = 'existing'; renderPanel(); } } }, 'Existing scene')),
      h('div', { class: 'stack' }, choice, isNew ? name : existing, go));
  }

  /* ------------------------------------------------------------------ reader */
  const coerce = (raw, type) => type === 'int' ? parseInt(raw, 10) || 0
    : type === 'bool' ? ['true', '1', 'yes'].includes(String(raw).trim().toLowerCase()) : String(raw ?? '');
  const defaultVars = () => Object.fromEntries(S.vars.map(v => [v.name, coerce(v.default, v.type)]));

  function startRead(nodeId) {
    const start = nodeId ?? S.story.start;
    S.read = start && S.nodes.has(start) ? { current: start, vars: defaultVars(), hist: [] } : null;
  }
  function passes(p, vars) {
    return p.conditions.every(c => {
      if (!c.req) return true;
      const v = varById(c.variable); if (!v) return true;
      const cur = vars[v.name] ?? coerce(v.default, v.type), want = coerce(c.value, v.type);
      return { eq: cur === want, neq: cur !== want, gt: cur > want, gte: cur >= want, lt: cur < want, lte: cur <= want }[c.req];
    });
  }
  function applyMods(p, vars) {
    const out = { ...vars };
    p.conditions.forEach(c => {
      if (!c.mod) return;
      const v = varById(c.variable); if (!v) return;
      const cur = out[v.name] ?? coerce(v.default, v.type), amt = coerce(c.value, v.type);
      out[v.name] = c.mod === 'set' ? amt : c.mod === 'add' ? cur + amt : c.mod === 'subtract' ? cur - amt : !cur;
    });
    return out;
  }
  function choose(pid) {
    const p = S.paths.get(pid); if (!p || !S.read) return;
    S.read.hist.push({ node: S.read.current, vars: S.read.vars, path: pid });
    S.read.vars = applyMods(p, S.read.vars); S.read.current = p.target;
    renderGraph(); renderPanel(); focusNode(p.target);
  }
  function back() {
    const e = S.read && S.read.hist.pop(); if (!e) return;
    S.read.current = e.node; S.read.vars = e.vars; renderGraph(); renderPanel(); focusNode(e.node);
  }
  function restart(id) { startRead(id); renderGraph(); renderPanel(); if (S.read) focusNode(S.read.current); }

  function readerView() {
    if (!S.read) return h('div', { class: 'reader' }, h('h2', { class: 'reader__title' }, S.story.title),
      h('p', { class: 'reader__empty' }, 'This story has no opening scene yet. Come back soon.'));
    const n = S.nodes.get(S.read.current), paths = outgoing(n.id), avail = paths.filter(p => passes(p, S.read.vars));
    const vars = S.vars.length ? S.vars.map(v => h('span', { class: 'chip chip--gold' }, `${v.name}: ${typeof S.read.vars[v.name] === 'boolean' ? (S.read.vars[v.name] ? 'yes' : 'no') : S.read.vars[v.name]}`)) : [];
    const paras = n.text.split(/\n\s*\n/).map(t => t.trim()).filter(Boolean);
    const finished = paths.length === 0;
    return h('div', { class: 'reader', key: n.id },
      h('div', { class: 'reader__bar' },
        h('button', { class: 'btn btn--sm', disabled: !S.read.hist.length, on: { click: back } }, '← Back'),
        h('div', { class: 'reader__vars' }, vars),
        S.canEdit ? h('button', { class: 'btn btn--sm btn--ghost', on: { click: () => { S.showMap = !S.showMap; renderGraph(); renderPanel(); } } }, S.showMap ? 'Hide map' : 'Reveal full map') : null),
      h('div', { class: 'reader__kicker' }, S.story.title),
      h('h2', { class: 'reader__title' }, n.title),
      h('div', { class: 'reader__orn' }, '✦ ✦ ✦'),
      n.image ? h('img', { class: 'reader__image', src: n.image, alt: '' }) : null,
      n.audio ? h('audio', { controls: true, src: n.audio }) : null,
      h('div', { class: 'reader__text' }, paras.length ? paras.map(t => h('p', {}, t)) : h('p', { class: 'reader__empty' }, 'This scene has not been written yet.')),
      avail.length ? h('div', { class: 'choices' }, avail.map(p => h('button', { class: 'choice-btn', on: { click: () => choose(p.id) } }, p.text || 'Continue'))) : null,
      !avail.length && !finished ? h('div', { class: 'the-end' }, h('h3', {}, 'The threads are tangled'), h('p', {}, 'No choice is open to you right now.'),
        h('button', { class: 'btn', on: { click: back } }, 'Step back')) : null,
      finished ? h('div', { class: 'the-end' }, h('h3', {}, 'The End'), h('p', {}, `You reached an ending in ${S.read.hist.length + 1} scenes.`),
        h('div', { class: 'panel__row', style: 'justify-content:center' },
          h('button', { class: 'btn btn--gold', on: { click: () => restart() } }, 'Read again'),
          S.read.hist.length ? h('button', { class: 'btn', on: { click: back } }, 'Undo last choice') : null)) : null);
  }

  /* ------------------------------------------------------------------ mode switch */
  function setMode(mode) {
    if (mode === 'edit' && !S.canEdit) return;
    flushSaves(); S.mode = mode;
    root.classList.toggle('mode-edit', mode === 'edit'); root.classList.toggle('mode-read', mode === 'read');
    root.classList.toggle('can-jump', mode === 'read' && S.canEdit);
    document.querySelectorAll('#mode-switch button').forEach(b => b.classList.toggle('is-active', b.dataset.mode === mode));
    if (mode === 'read') { S.selNode = null; S.selPath = null; startRead(); }
    renderGraph(); renderPanel();
    setTimeout(() => (mode === 'read' && S.read ? focusNode(S.read.current) : fitView()), 480);
  }
  document.querySelectorAll('#mode-switch button').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
  if (!S.canEdit) $('mode-switch').classList.add('is-locked');

  /* ------------------------------------------------------------------ pointer interaction */
  let gesture = null;
  const ignoreBg = '.node,.label,.dock,.empty-state__card,.thread-hit';

  stage.addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.target.closest('.dock,.empty-state__card')) return;
    const handle = e.target.closest('.node__handle');
    const nodeEl = e.target.closest('.node');
    if (handle && S.mode === 'edit') {
      const id = +nodeEl.dataset.id; e.preventDefault();
      gesture = { type: 'connect', id, sx: e.clientX, sy: e.clientY, moved: false }; stage.setPointerCapture(e.pointerId);
    } else if (nodeEl) {
      const id = +nodeEl.dataset.id, n = S.nodes.get(id);
      if (S.mode === 'edit') { gesture = { type: 'drag', id, sx: e.clientX, sy: e.clientY, ox: n.x, oy: n.y, moved: false }; stage.setPointerCapture(e.pointerId); }
      else if (S.canEdit) restart(id);
    } else if (!e.target.closest(ignoreBg)) {
      gesture = { type: 'pan', sx: e.clientX, sy: e.clientY, ox: S.view.x, oy: S.view.y, moved: false };
      stage.setPointerCapture(e.pointerId); stage.classList.add('is-panning');
    }
  });

  stage.addEventListener('pointermove', e => {
    if (!gesture) return;
    const dx = e.clientX - gesture.sx, dy = e.clientY - gesture.sy;
    if (!gesture.moved && Math.hypot(dx, dy) > 4) gesture.moved = true;
    if (!gesture.moved) return;
    if (gesture.type === 'pan') { S.view.x = gesture.ox + dx; S.view.y = gesture.oy + dy; applyView(); }
    else if (gesture.type === 'drag') {
      const n = S.nodes.get(gesture.id), el = nodeEls.get(gesture.id);
      n.x = Math.round((gesture.ox + dx / S.view.k) / 10) * 10; n.y = Math.round((gesture.oy + dy / S.view.k) / 10) * 10;
      el.classList.add('is-dragging'); el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; renderThreads();
    } else if (gesture.type === 'connect') {
      const a = S.nodes.get(gesture.id), p = toWorld(e.clientX, e.clientY), x1 = a.x + NW, y1 = a.y + NH / 2, c = Math.max(60, Math.abs(p.x - x1) / 2);
      ghost.setAttribute('d', `M${x1} ${y1} C${x1 + c} ${y1} ${p.x - c} ${p.y} ${p.x} ${p.y}`);
      const over = document.elementFromPoint(e.clientX, e.clientY)?.closest('.node');
      nodeEls.forEach(el => el.classList.toggle('is-target', el === over && +el.dataset.id !== gesture.id));
    }
  });

  stage.addEventListener('pointerup', async e => {
    const g = gesture; gesture = null; stage.classList.remove('is-panning');
    if (!g) return;
    if (g.type === 'pan') { if (!g.moved && S.mode === 'edit' && S.selNode) deselect(); return; }
    if (g.type === 'drag') {
      nodeEls.get(g.id)?.classList.remove('is-dragging');
      if (g.moved) savePositions([g.id]); else if (S.mode === 'edit') selectNode(g.id);
      return;
    }
    if (g.type === 'connect') {
      ghost.setAttribute('d', ''); nodeEls.forEach(el => el.classList.remove('is-target'));
      if (!g.moved) { selectNode(g.id); setTimeout(() => panel.querySelector('.branch-add input')?.focus(), 60); return; }
      const over = document.elementFromPoint(e.clientX, e.clientY)?.closest('.node');
      try {
        if (over && +over.dataset.id !== g.id) {
          const p = await linkNodes(g.id, +over.dataset.id, 'Continue');
          renderGraph(); selectNode(g.id, { path: p.id, scrollToPath: true }); toast('Threads joined');
        } else if (!over) {
          const w = toWorld(e.clientX, e.clientY), pos = freeSpot(w.x - NW / 2, w.y - NH / 2);
          const d = await createNode({ ...pos, parent: g.id, choice: 'Continue' });
          renderGraph(); selectNode(d.node.id);
        }
      } catch (err) {}
    }
  });
  stage.addEventListener('pointercancel', () => { gesture = null; stage.classList.remove('is-panning'); });

  stage.addEventListener('wheel', e => {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoomAt(Math.exp(-e.deltaY * 0.0016), e.clientX - r.left, e.clientY - r.top);
  }, { passive: false });

  $('zoom-in').onclick = () => { const r = stage.getBoundingClientRect(); zoomAt(1.2, r.width / 2, r.height / 2); };
  $('zoom-out').onclick = () => { const r = stage.getBoundingClientRect(); zoomAt(1 / 1.2, r.width / 2, r.height / 2); };
  $('zoom-fit').onclick = () => fitView();

  async function addLooseScene(first) {
    const r = stage.getBoundingClientRect(), c = toWorld(r.left + r.width / 2, r.top + r.height / 2);
    const pos = first ? { x: 0, y: 0 } : freeSpot(c.x - NW / 2, c.y - NH / 2);
    try {
      const d = await createNode({ ...pos, title: first ? 'Chapter one' : 'Untitled scene' });
      renderGraph(); selectNode(d.node.id);
      if (first) setTimeout(() => fitView(), 50);
    } catch (e) {}
  }
  $('tool-add').onclick = () => addLooseScene(false);
  $('empty-create').onclick = () => { if (S.canEdit) addLooseScene(true); else toast('The author has not written anything yet.'); };
  $('tool-tidy').onclick = async () => {
    autoLayout(); renderGraph(); fitView(); await savePositions([...S.nodes.keys()]); toast('Tidied the tapestry');
  };

  window.addEventListener('keydown', e => {
    if (e.key === 'Escape' && S.mode === 'edit' && S.selNode && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) deselect();
  });
  window.addEventListener('resize', () => applyView());

  /* ------------------------------------------------------------------ go */
  const prefs = boot.prefs || {};
  root.style.setProperty('--reader-size', prefs.readerSize || '1.32rem');
  root.style.setProperty('--reader-font', prefs.readerFont || 'var(--font-display)');
  root.style.setProperty('--editor-size', prefs.editorSize || '1.25rem');
  root.classList.toggle('reduce-motion', !!prefs.reduceMotion);
  if (!S.canEdit) { root.classList.replace('mode-edit', 'mode-read'); }
  const allAtOrigin = [...S.nodes.values()].every(n => n.x === 0 && n.y === 0);
  if (S.nodes.size > 1 && allAtOrigin) { autoLayout(); if (S.canEdit) savePositions([...S.nodes.keys()]); }
  if (S.mode === 'read') startRead();
  renderGraph(); renderPanel();
  requestAnimationFrame(() => (S.mode === 'read' && S.read ? (fitView(false), setTimeout(() => focusNode(S.read.current), 150)) : fitView(false)));
  if (S.canEdit && prefs.defaultMode === 'read') setMode('read');
})();
