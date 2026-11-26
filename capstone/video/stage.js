// Director for the explainer video. make_video.py calls D.scene / D.cue / D.sub / D.x* through Playwright.
// Everything the X-ray shows comes from the real /api/chat response of the request just sent.
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
const fxIn = (...ids) => ids.forEach(id => $('#' + id)?.classList.add('in'));
async function stagger(nodes, ms, cls = 'in') { for (const n of nodes) { n.classList.add(cls); await sleep(ms); } }
function countUp(node, to, ms = 1200, fmt = v => Math.round(v)) {
  const t0 = performance.now();
  const tick = t => { const p = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - p, 3); node.textContent = fmt(to * e); if (p < 1) requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}
const secs = ms => ms >= 1000 ? (ms / 1000).toFixed(2) + ' s' : Math.round(ms) + ' ms';

const D = window.D = {};
const CUES = {};
D.cue = (name, data) => { CUES[name](data || {}); return true; };   // never return the promise (keeps Python unblocked)

// ---------------------------------------------------------------- scenes, chapter, subtitles
D.scene = name => { $$('.scene').forEach(s => s.classList.toggle('on', s.id === 'sc-' + name)); return true; };
D.chapter = (num, text) => {
  const c = $('#chapter');
  if (!text) { c.classList.remove('on'); return true; }
  c.innerHTML = `<b>${esc(num)}</b>${esc(text)}`; c.classList.add('on'); return true;
};
let subTimers = [];
D.sub = (text, total) => {
  subTimers.forEach(clearTimeout); subTimers = [];
  const s = $('#subs');
  const parts = (text.match(/[^.!?।]+[.!?।]*["”]?\s*/g) || [text]).map(p => p.trim()).filter(Boolean);
  // merge tiny fragments so subtitles do not flicker
  const lines = [];
  for (const p of parts) { if (lines.length && (lines[lines.length - 1].length < 28 || p.length < 14) && (lines[lines.length - 1] + p).length < 120) lines[lines.length - 1] += ' ' + p; else lines.push(p); }
  const chars = lines.reduce((a, l) => a + l.length, 0);
  let t = 0;
  lines.forEach(l => {
    subTimers.push(setTimeout(() => { s.textContent = l; s.classList.add('on'); }, t * 1000));
    t += total * l.length / chars;
  });
  subTimers.push(setTimeout(() => s.classList.remove('on'), total * 1000 + 250));
  return true;
};
const panel = (scene, id) => { $$(`#sc-${scene} .panel`).forEach(p => p.classList.toggle('in', p.id === id)); };

// ---------------------------------------------------------------- 1. cold open
const HELPS = [
  ['55%', 'subsidy on drip & sprinkler irrigation', 1060, 170], ['₹6,000', 'a year, income support', 1450, 300],
  ['₹3,000', 'a month pension after 60', 1060, 440], ['Insured', 'crops, at a small premium', 1450, 570]];
CUES.open1 = async () => {
  D.chapter('', ''); $('#o-field').classList.add('drawn'); fxIn('o-sun');
  await sleep(200); fxIn('o-kick'); await sleep(350); fxIn('o-name'); await sleep(700); fxIn('o-facts');
};
CUES.open2 = async () => {
  const box = $('#o-helps'); box.innerHTML = '';
  for (const [t, d, x, y] of HELPS) {
    const h = el('div', 'help', `<div class="t">${t}</div><div class="d">${d}</div>`);
    h.style.left = x + 'px'; h.style.top = (y + 40) + 'px'; h.style.opacity = 0; box.appendChild(h);
    await sleep(60); h.style.top = y + 'px'; h.style.opacity = 1; await sleep(650);
  }
};
CUES.open3 = async ({ titles = [] }) => {
  const pile = $('#o-pile'); pile.style.left = '1340px'; pile.innerHTML = '';
  $$('.help').forEach((h, i) => { h.style.left = '1190px'; h.style.top = '420px'; h.style.transform = `rotate(${(i - 1.5) * 6}deg) scale(.7)`; h.style.opacity = 0; });
  await sleep(500);
  const names = titles.length ? titles : ['Operational Guidelines'];
  for (let i = 0; i < 26; i++) {
    const sh = el('div', 'sheet', `<span class="pdf">PDF</span>${esc(names[i % names.length])}`);
    pile.appendChild(sh);
    const rot = (Math.random() - .5) * 26, dx = (Math.random() - .5) * 120, dy = (Math.random() - .5) * 50 - i * 2;
    sh.style.transform = `translate(${dx}px, ${dy - 200}px) rotate(${rot}deg)`;
    requestAnimationFrame(() => { sh.style.opacity = 1; sh.style.transform = `translate(${dx}px, ${dy}px) rotate(${rot}deg)`; });
    await sleep(110);
  }
  await sleep(600); fxIn('o-counter');
};
CUES.open4 = () => fxIn('o-question');
CUES.reprise = async () => {   // closing callback to Ramesh
  D.chapter('', '');
  $('#o-question').classList.remove('in'); $('#o-pile').innerHTML = ''; $('#o-helps').innerHTML = '';
  $('#o-field').classList.add('drawn', 'green'); fxIn('o-sun', 'o-kick', 'o-name', 'o-facts', 'o-counter');
  const k = $('#o-k'); k.textContent = '0'; k.className = 'n green';
  $('#o-counter .box:nth-child(2) .l').textContent = 'he now knows about';
  await sleep(2600); countUp(k, 5, 1400);
  await sleep(1600);
  const box = $('#o-helps');
  for (const [t, d, x, y] of HELPS) {
    const h = el('div', 'help', `<div class="t">${t}</div><div class="d">${d}</div>`);
    h.style.left = x + 'px'; h.style.top = (y + 40) + 'px'; h.style.opacity = 0; box.appendChild(h);
    await sleep(60); h.style.top = y + 'px'; h.style.opacity = 1; await sleep(500);
  }
};

// ---------------------------------------------------------------- 2. title
CUES.title1 = async () => {
  D.chapter('', ''); fxIn('t-logo'); await sleep(500); fxIn('t-name'); await sleep(700); fxIn('t-lead');
  await sleep(1800); fxIn('t-p1'); await sleep(1100); fxIn('t-p2'); await sleep(1100); fxIn('t-p3');
};

// ---------------------------------------------------------------- 3. X-ray
const NODES = [
  { k: 'intake', n: '1', nm: 'Intake', ty: 'AI · reads', ai: true },
  { k: 'router', n: '2', nm: 'Router', ty: 'code · picks a road' },
  { k: 'rules', n: '3', nm: 'Rules engine', ty: 'code · eligibility' },
  { k: 'search', n: '4', nm: 'Hybrid search', ty: 'code + embeddings' },
  { k: 'answer', n: '5', nm: 'Answer', ty: 'AI · explains', ai: true },
  { k: 'critic', n: '6', nm: 'Critic', ty: 'code · checks' },
  { k: 'follow', n: '7', nm: 'Follow-up', ty: 'code · asks next' },
];
const GAP = 83;
let X = null;   // current request

function buildSpine() {
  const sp = $('#spine');
  $$('#spine .node').forEach(n => n.remove());
  NODES.forEach((d, i) => {
    const n = el('div', 'node' + (d.ai ? ' ai' : ''), `<div class="dot">${d.n}</div><div><div class="nm">${d.nm}</div><div class="ty">${d.ty}</div></div><div class="ms"></div>`);
    n.id = 'n-' + d.k; n.style.top = (i * GAP) + 'px'; sp.appendChild(n);
  });
  $('#spine-fill').style.height = '0px';
}
buildSpine();

function analyse(R) {
  const r = R.resp, tr = r.trace || {}, path = tr.path || [], nm = tr.node_ms || {}, tm = tr.tool_ms || {};
  const tools = path.includes('executor') || path.includes('scheme_tools');
  const used = { intake: true, router: true, rules: tools, search: tools && (tr.tools || []).includes('search'),
                 answer: path.includes('answer'), critic: path.includes('critic'), follow: path.includes('suggest') };
  const rulesMs = (tm.eligibility || 0) + (tm.documents || 0) + (tm.links || 0);
  const ms = { intake: nm.intake || 0, router: 0, rules: rulesMs, search: tm.search || 0,
               answer: nm.answer || 0, critic: nm.critic || 0, follow: nm.suggest || 0 };
  const intakeAI = R.kind === 'type', answerAI = used.answer && (r.schemes || []).length > 0;
  let missing = (intakeAI + answerAI) - (tr.llm_calls || 0);   // AI steps answered from the cache
  const cached = { intake: false, answer: false };
  if (missing > 0 && answerAI) { cached.answer = true; missing--; }
  if (missing > 0 && intakeAI) { cached.intake = true; }
  return { r, tr, used, ms, intakeAI, answerAI, cached, total: tr.ms || 1 };
}

D.xload = R => {   // a new request: reset the panel
  X = { R, ...analyse(R) };
  buildSpine();
  $('#detail').innerHTML = ''; $('#bars').innerHTML = ''; $('#ticks').innerHTML = '';
  const m = R.msg.length > 70 ? R.msg.slice(0, 68) + '…' : R.msg;
  $('#x-sub').textContent = R.kind === 'tap' ? `tapped: “${m}”` : `“${m}”`;
  $('#x-tid').textContent = 'trace ' + (X.tr.id || '');
  ['ms', 'ai', 'tok', 'tools', 'cache'].forEach(k => { $('#st-' + k + ' .v').textContent = '–'; $('#st-' + k).classList.remove('hot'); });
  return true;
};
D.xwait = msg => {   // a new message was sent: clear the previous request from the panel
  X = null; buildSpine();
  $('#detail').innerHTML = '<div class="dview in"><div class="note" style="margin-top:200px;text-align:center;font-size:26px">⏳ waiting for the reply…</div></div>';
  $('#bars').innerHTML = ''; $('#ticks').innerHTML = '';
  $('#x-sub').textContent = '“' + (msg.length > 70 ? msg.slice(0, 68) + '…' : msg) + '”'; $('#x-tid').textContent = '';
  ['ms', 'ai', 'tok', 'tools', 'cache'].forEach(k => { $('#st-' + k + ' .v').textContent = '–'; $('#st-' + k).classList.remove('hot'); });
  return true;
};
D.xstats = () => {
  const t = X.tr;
  $('#st-ms .v').textContent = secs(t.ms || 0);
  $('#st-ai .v').textContent = t.llm_calls ?? 0;
  $('#st-tok .v').textContent = ((t.tokens_in || 0) + (t.tokens_out || 0)).toLocaleString('en-IN');
  $('#st-tools .v').textContent = t.tool_calls ?? 0;
  $('#st-cache .v').textContent = t.cache_hits ?? 0;
  $('#st-cache').classList.toggle('hot', (t.cache_hits || 0) > 0);
  $('#ticks').innerHTML = `<span>0</span><span>${secs(t.ms || 0)}</span>`;
  return true;
};
function addSeg(k) {
  const ms = X.ms[k]; if (!X.used[k] || ms < 40) return;
  const d = NODES.find(n => n.k === k);
  const kind = X.cached[k] ? 'cache' : d.ai ? 'ai' : 'code';
  const s = el('div', 'seg ' + kind); $('#bars').appendChild(s);
  const w = Math.max(2, 100 * ms / X.total);
  requestAnimationFrame(() => { s.style.width = w + '%'; });
  if (w > 9) s.textContent = `${d.nm} ${secs(ms)}`;
}
function markNode(k, state) {
  const n = $('#n-' + k), i = NODES.findIndex(d => d.k === k);
  if (X.cached[k]) n.classList.add('cached');
  if (state === 'skip') { n.classList.add('skip'); n.querySelector('.ms').textContent = 'skipped'; return; }
  $$('#spine .node.active').forEach(a => { a.classList.remove('active'); a.classList.add('done'); });
  n.classList.add(state === 'active' ? 'active' : 'done');
  const ai = X.cached[k] ? 'cache' : (k === 'intake' && !X.intakeAI) ? 'no AI' : '';
  n.querySelector('.ms').textContent = ai || (X.ms[k] < 1 ? '<1 ms' : secs(X.ms[k]));
  $('#spine-fill').style.height = (i * GAP + 26) + 'px';
}
function view(html) {
  const d = $('#detail'); const old = d.querySelector('.dview');
  if (old) { old.classList.remove('in'); setTimeout(() => old.remove(), 500); }
  const v = el('div', 'dview', html); d.appendChild(v); requestAnimationFrame(() => requestAnimationFrame(() => v.classList.add('in')));
  return v;
}
const TITLE = (t, tag, cls = '') => `<div class="dtitle">${t}<span class="tag ${cls}">${tag}</span></div>`;

// --- step views
const RENDER = {};
RENDER.intake = async () => {
  const r = X.r, p = r.profile || {};
  let tag = 'AI CALL 1 · Qwen3-8B', cls = 'ai', arrow = `<div class="flow-arrow">Qwen3-8B → JSON (constrained shape, validated in code) · ${secs(X.ms.intake)}</div>`;
  if (!X.intakeAI) { tag = 'NO AI CALL'; cls = ''; arrow = `<div class="flow-arrow code">a tapped button is already structured → stored directly, no AI</div>`; }
  else if (X.cached.intake) { tag = 'CACHE HIT'; cls = 'cache'; arrow = `<div class="flow-arrow cache">same prompt seen before → saved reply reused · 0 AI calls</div>`; }
  const intent = { find: 'find_schemes', focus: 'scheme_question', which: 'scheme_question', ask: 'find_schemes', refuse: 'out_of_scope' }[r.mode] || r.mode;
  const lang = /[ऀ-ॿ]/.test(X.R.msg) ? 'hi' : (X.R.lang || 'en');
  const rows = Object.entries(p).map(([k, v]) => `<div class="row">  <span class="k">"${esc(k)}"</span>: ${typeof v === 'number' ? `<span class="n">${v}</span>` : `<span class="s">"${esc(v)}"</span>`},</div>`);
  const v = view(`${TITLE('Intake', tag, cls)}<div class="bubble-q">${esc(X.R.msg)}</div>${arrow}
    <div class="json"><div class="row in">{ <span class="k">"profile"</span>: {</div>${rows.join('')}<div class="row">  },</div>
    <div class="row">  <span class="k">"intent"</span>: <span class="s">"${intent}"</span>, <span class="k">"lang"</span>: <span class="s">"${lang}"</span> }</div></div>
    ${X.R.note ? `<div class="note">${X.R.note}</div>` : ''}`);
  await sleep(900); await stagger([...v.querySelectorAll('.json .row:not(.in)')], 380);
};
const ROADS = [
  ['ask', 'We do not know who you are yet → ask: farmer, student or business?'],
  ['refuse', 'Off topic → a polite, fixed reply in your language'],
  ['which', '“How do I apply?”, but for which scheme? → ask which one'],
  ['focus', 'One scheme named or tapped → its rules and its PDFs only'],
  ['find', 'Profile known → find every scheme that may fit'],
];
RENDER.router = async () => {
  const mode = X.r.mode;
  const v = view(`${TITLE('Router', 'CODE · 0 AI CALLS')}<div class="dsub">Plain Python decides which road this message takes</div>
    <div class="roads">${ROADS.map(([k, d]) => `<div class="road" data-k="${k}"><div class="rn">${k}</div><div class="rd">${d}</div></div>`).join('')}</div>`);
  await sleep(1400);
  v.querySelectorAll('.road').forEach(r => r.classList.add(r.dataset.k === mode ? 'pick' : 'no'));
};
const ST = { potentially_eligible: ['may be eligible', 'ok'], more_info_needed: ['needs 1 detail', 'warn'] };
RENDER.rules = async () => {
  const sch = (X.r.schemes || []).slice(0, 5);
  const v = view(`${TITLE('Rules engine', 'CODE · ' + secs(X.ms.rules))}<div class="dsub">Every rule is data, checked against the profile: met · not met · unknown</div>
    <div class="schemes">${sch.map((s, i) => {
      const [lab, cls] = ST[s.status] || ['not eligible', 'bad'];
      const conds = (s.conditions || []).slice(0, 3).map(c => `<span class="cond ${c.result}"><b>${c.result === 'met' ? '✓' : c.result === 'not_met' ? '✗' : '?'}</b>${esc(c.text)}</span>`).join('');
      return `<div class="sch ${i === 0 ? 'first' : ''}"><div class="top"><span class="nm">${esc(s.short_name || s.name)}</span><span class="st ${cls}">${lab}</span></div><div class="conds">${conds}</div></div>`;
    }).join('')}</div>`);
  for (const s of v.querySelectorAll('.sch')) { s.classList.add('in'); await sleep(250); await stagger([...s.querySelectorAll('.cond')], 260); }
};
const ROW = 36;
function card(id, rank, cls) {
  const c = (X.R.chunks || {})[id] || { title: 'chunk ' + id, page: '?' };
  const e = el('div', 'ccard ' + cls, `<span class="r">#${rank}</span><span class="tt">${esc(c.title)}</span><span class="pg">p.${c.page}</span>`);
  e.dataset.id = id; return e;
}
RENDER.search = async (phase) => {
  const rt = X.tr.retrieval || { bm25: [], dense: [], fused: [], reranked: [], pool: 0 };
  if (phase === 'lanes') {
    const v = view(`${TITLE('Hybrid search', 'CODE + EMBEDDINGS · ' + secs(X.ms.search))}
      <div class="dsub">Only inside the matched schemes' PDFs: ${rt.pool.toLocaleString('en-IN')} of 1,884 passages</div><div class="search" id="srch">
      <div class="lanehead" id="lh1" style="left:0">BM25 · EXACT WORDS</div><div class="lanehead" id="lh2" style="left:51%">DENSE · MEANING</div></div>`);
    const box = v.querySelector('#srch');
    const lanes = [[rt.bm25.slice(0, 6), 'bm', '0%'], [rt.dense.slice(0, 6), 'de', '51%']];
    for (let i = 0; i < 6; i++) for (const [ids, cls, left] of lanes) {
      if (ids[i] == null) continue;
      const c = card(ids[i], i + 1, cls); c.style.left = left; c.style.width = '49%'; c.style.top = (30 + i * ROW) + 'px'; c.style.opacity = 0;
      box.appendChild(c); requestAnimationFrame(() => { c.style.opacity = 1; }); await sleep(170);
    }
    return;
  }
  const box = $('#srch'); if (!box) return;
  if (phase === 'fuse') {
    $('#lh1').textContent = 'RECIPROCAL RANK FUSION · 12 CANDIDATES'; $('#lh2').style.opacity = 0;
    const keep = {};
    box.querySelectorAll('.ccard').forEach(c => { const id = c.dataset.id; if (keep[id] || !rt.fused.includes(+id)) { c.style.opacity = 0; setTimeout(() => c.remove(), 700); } else keep[id] = c; });
    rt.fused.forEach((id, i) => {
      let c = keep[id];
      if (!c) { c = card(id, i + 1, ''); c.style.left = '0%'; c.style.width = '49%'; c.style.top = (30 + i * ROW) + 'px'; c.style.opacity = 0; box.appendChild(c); }
      c.classList.remove('bm', 'de'); c.querySelector('.r').textContent = '#' + (i + 1);
      requestAnimationFrame(() => { c.style.left = '0%'; c.style.width = '66%'; c.style.top = (30 + i * ROW) + 'px'; c.style.opacity = 1; });
    });
    return;
  }
  if (phase === 'rerank') {
    $('#lh1').textContent = 'CROSS-ENCODER RERANK · READS QUESTION + PASSAGE TOGETHER';
    const cards = {}; box.querySelectorAll('.ccard').forEach(c => { cards[c.dataset.id] = c; });
    rt.reranked.forEach((id, i) => {
      const c = cards[id]; if (!c) return;
      c.style.top = (30 + i * ROW) + 'px';
      c.querySelector('.r').textContent = i < 4 ? 'S' + (i + 1) : '#' + (i + 1);
      setTimeout(() => { c.classList.toggle('ev', i < 4); c.style.opacity = i < 4 ? 1 : .42; if (i === 0) c.classList.add('star'); }, 1300);
    });
    const top = rt.reranked[0];
    const pos = (arr) => { const i = arr.indexOf(top); return i < 0 ? 'not in top 20' : '#' + (i + 1); };
    const co = el('div', 'callout', `<b>S1 · now #1</b>keywords: ${pos(rt.bm25)}<br>meaning: ${pos(rt.dense)}<br>after fusion: ${pos(rt.fused)}`);
    co.style.left = '69%'; co.style.right = '0'; co.style.top = '30px'; box.appendChild(co);
    await sleep(1700); co.classList.add('in');
  }
};
function fmtAnswer(t) {
  return esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\[(S\d)\]/g, '<span class="cite">[$1]</span>');
}
RENDER.answer = async () => {
  const r = X.r, nsch = (r.schemes || []).length, nprof = Object.keys(r.profile || {}).length;
  const cached = X.cached.answer;
  const v = view(`${TITLE('Answer', cached ? 'CACHE HIT · 0 AI CALLS' : 'AI CALL 2 · Qwen3-8B', cached ? 'cache' : 'ai')}
    <div class="dsub">A small, focused prompt. The model only has to explain.</div>
    <div class="prompt">
      <div class="pblock">👤 Profile <span>${nprof} facts</span></div>
      <div class="pblock">📋 Schemes, every rule decided <span>${nsch} cards</span></div>
      <div class="pblock">📄 Evidence passages <span>[S1]–[S4]</span></div>
      <div class="pblock">📏 Cite [S#] · “may be eligible” · no outside links <span>rules</span></div>
    </div>
    <div class="meter"><div class="v" id="tok">0</div><div class="k">prompt tokens, this request</div><div class="vs">whole catalogue ≈ 5,000</div></div>
    <div class="flow-arrow ${cached ? 'cache' : ''}">${cached ? 'identical prompt → saved reply (300 entries, 1 hour)' : 'Qwen3-8B writes · ' + secs(X.ms.answer)}</div>
    <div class="answer-out" id="ans"></div>`);
  await stagger([...v.querySelectorAll('.pblock')], 420);
  countUp(v.querySelector('#tok'), X.tr.tokens_in || 0, 1300, x => Math.round(x).toLocaleString('en-IN'));
  await sleep(1200);
  let txt = (r.message || '').replace(/\n{2,}/g, '\n');
  if (txt.length > 300) txt = txt.slice(0, 290).replace(/\s\S*$/, '') + ' …';
  const out = v.querySelector('#ans');
  const step = Math.max(2, Math.round(txt.length / 90));
  for (let i = 0; i <= txt.length; i += step) { out.innerHTML = fmtAnswer(txt.slice(0, i)); await sleep(cached ? 8 : 30); }
  out.innerHTML = fmtAnswer(txt);
};
const CHECKS = ['Names only schemes that are on the cards', 'Never “you are eligible” or “guaranteed”',
  'No fee or payment requests', 'No phone, Aadhaar or account numbers, no unofficial links', 'Names the most useful scheme'];
RENDER.critic = async () => {
  const tr = X.tr, scrub = (tr.errors || []).find(e => e.kind === 'scrubbed');
  const v = view(`${TITLE('Critic', 'CODE · ' + (X.ms.critic < 1 ? '<1 ms' : secs(X.ms.critic)))}<div class="dsub">If any check fails, the answer is sent back to be rewritten</div>
    <div class="checks">${CHECKS.map(c => `<div class="check"><div class="ic">✓</div>${c}</div>`).join('')}</div>
    <div class="verdict" id="verdict"></div>`);
  await sleep(500);
  const cs = [...v.querySelectorAll('.check')];
  for (let i = 0; i < cs.length; i++) {
    if (i === 3 && scrub) { cs[i].classList.add('fix'); cs[i].querySelector('.ic').textContent = '✂'; }
    cs[i].classList.add('in'); await sleep(520);
  }
  const vd = v.querySelector('#verdict');
  vd.innerHTML = tr.critic_retries ? `<span style="color:var(--amber)">↺ Sent back ${tr.critic_retries}× and rewritten</span>`
    : scrub ? `<span style="color:var(--amber)">✂ Scrubbed from the reply: ${esc(scrub.detail)}</span>` : `<span class="green">✓ Passed. No rewrite needed.</span>`;
  vd.classList.add('in');
};
RENDER.follow = async () => {
  const f = X.r.followup;
  if (!f) { view(`${TITLE('Follow-up', 'CODE')}<div class="note">Nothing left to ask. The reply goes out.</div>`); return; }
  const v = view(`${TITLE('Follow-up', 'CODE · 0 AI CALLS')}<div class="dsub">The one unknown detail that settles the most schemes</div>
    <div class="fq">${esc(f.question)}${(f.helps_names || []).length ? `<div class="why">settles: ${esc(f.helps_names.join(', '))}</div>` : ''}</div>
    <div class="opts">${(f.options || []).slice(0, 4).map(o => `<span class="opt">${esc(o.label)}</span>`).join('')}</div>
    <div class="bigicon">📱</div><div class="note">Reply, cards, sources and buttons go back to the phone.</div>`);
  await sleep(200);
};
RENDER.refuse = async () => {
  view(`${TITLE('Shortest road', 'CODE')}<div class="dsub">Off topic: no search, no answer generation</div>
    <div class="answer-out" style="border-color:var(--blue);margin-top:30px">${fmtAnswer(X.r.message || '')}</div>
    <div class="note">A fixed, polite reply in the user's language. Nothing to hallucinate.</div>`);
};

D.xstep = (k, phase) => {   // one step of the full replay
  if (k === 'reply') { $$('#spine .node.active').forEach(a => { a.classList.remove('active'); a.classList.add('done'); }); $('#spine-fill').style.height = '100%'; return true; }
  if (!phase || phase === 'lanes') { markNode(k, 'active'); addSeg(k); }
  RENDER[k](phase);
  return true;
};
D.xquick = async (focus, total) => {   // compact replay: light the path, then show the chosen step views
  D.xstats();
  const order = NODES.map(n => n.k);
  (async () => {
    for (const k of order) {
      if (!X.used[k]) { markNode(k, 'skip'); continue; }
      markNode(k, 'active'); addSeg(k); await sleep(330);
    }
    markNode(order.filter(k => X.used[k]).pop(), 'done');
    $$('#spine .node.active').forEach(a => { a.classList.remove('active'); a.classList.add('done'); });
    const each = Math.max(2500, (total * 1000 - 2600) / Math.max(1, focus.length));
    for (const f of focus) {
      if (f === 'search') { RENDER.search('lanes'); await sleep(each * .35); RENDER.search('fuse'); await sleep(each * .25); RENDER.search('rerank'); await sleep(each * .4); }
      else { if (NODES.find(n => n.k === f)) { $$('#spine .node').forEach(n => n.classList.remove('active')); $('#n-' + f).classList.add('active'); } RENDER[f](); await sleep(each); }
    }
  })();
  return true;
};
D.veil = (html) => { const v = $('#veil'); if (html) { $('#veil-txt').innerHTML = html; v.classList.add('on'); } else v.classList.remove('on'); return true; };

// ---------------------------------------------------------------- 4. lesson: documents
const CATS = [[33, 'usable, citizen-facing', 'var(--green)'], [20, 'tagged for later', 'var(--blue)'], [16, 'not citizen-facing', '#56607a'],
  [15, 'scanned, need OCR', 'var(--amber)'], [2, 'not in English', 'var(--ai)'], [1, 'broken', 'var(--red)']];
CUES.docs1 = async () => {
  D.chapter('', ''); panel('docs', 'docs-a');
  const t = $('#tiles'); t.innerHTML = ''; const lg = $('#legend'); lg.innerHTML = '';
  const tiles = [];
  CATS.forEach(([n, , c]) => { for (let i = 0; i < n; i++) { const e = el('div', 'tile'); e.style.background = c; t.appendChild(e); tiles.push(e); } });
  CATS.forEach(([n, l, c]) => lg.appendChild(el('span', '', `<i style="background:${c}"></i><b>${n}</b>${l}`)));
  await stagger(tiles, 28);
};
CUES.docs1b = () => stagger(['bn1', 'bn2', 'bn3'].map(i => $('#' + i)), 600);
CUES.docs2 = async ({ chunk }) => {
  panel('docs', 'docs-b');
  $('#docs-h').textContent = 'Every chunk remembers where it came from';
  $('#page-h').textContent = chunk.title + ' · page ' + chunk.page;
  $('#page-t').textContent = chunk.text.slice(0, 1250);
  const page = $('#page'); page.querySelectorAll('.band,.overlap').forEach(b => b.remove());
  const meta = $('#meta');
  meta.innerHTML = [['scheme_id', chunk.scheme_id], ['title', chunk.title], ['page', chunk.page], ['source_url', chunk.source_url.replace(/^https?:\/\//, '').slice(0, 46) + '…']]
    .map(([k, v]) => `<div class="metarow"><span>${k}</span>${esc(v)}</div>`).join('') +
    `<div class="cite-demo">“…<b>55% subsidy</b> on drip and sprinkler systems <span class="accent">[S3]</span>”<br><span style="color:var(--muted);font-size:18px">→ ${esc(chunk.title)}, page ${chunk.page}</span></div>`;
  await sleep(1200);
  for (const [y, lab] of [[200, 'chunk · 300 words'], [400, 'next chunk · 50-word overlap']]) {
    const ov = el('div', 'overlap'); ov.style.top = (y - 34) + 'px'; ov.style.height = '34px'; page.appendChild(ov);
    const b = el('div', 'band', `<span class="bl">${lab}</span>`); b.style.top = y + 'px'; page.appendChild(b);
    await sleep(80); b.classList.add('in'); ov.classList.add('in'); await sleep(900);
  }
  await stagger([...meta.querySelectorAll('.metarow')], 500);
  await sleep(800); meta.querySelector('.cite-demo').classList.add('in');
};
CUES.docs3 = async () => {
  panel('docs', 'docs-c'); $('#docs-h').textContent = 'How big should a chunk be?';
  const data = [['150 / 25', '3,112 chunks · rules cut off from context', 93, ''], ['300 / 50', '1,884 chunks · every question in the top 4', 100, 'win'],
    ['500 / 80', '1,728 chunks · overflow the 512-token embedder', 93, '']];
  const c = $('#cols3'); c.innerHTML = data.map(([l, s, v, w]) => `<div class="col3 ${w}"><div class="barwrap"><div class="bar" data-v="${v}">${v}%</div></div><div class="cl">${l} words</div><div class="cs">${s}</div></div>`).join('');
  await sleep(600);
  for (const b of c.querySelectorAll('.bar')) { b.style.height = (b.dataset.v * 3.6) + 'px'; await sleep(700); }
};
CUES.docs4 = async () => {
  panel('docs', 'docs-d'); $('#docs-h').textContent = 'The reranker earned its place';
  const rows = [['Keywords (BM25)', 11, ''], ['+ dense (meaning)', 11, ''], ['+ cross-encoder reranker', 13, 'win']];
  $('#abl').innerHTML = rows.map(([l, v, w]) => `<div class="hrow"><div>${l}</div><div class="htrack"><div class="hfill ${w}" data-v="${v}"></div></div><div class="hval">${v}/15</div></div>`).join('');
  await sleep(500);
  for (const f of $$('#abl .hfill')) { f.style.width = (f.dataset.v / 15 * 100) + '%'; await sleep(700); }
};

// ---------------------------------------------------------------- 5. lesson: small model
CUES.model1 = async () => {
  D.chapter('', ''); panel('model', 'model-a');
  const S = [['Zero-shot', 'Instructions and the full catalogue', 73, ''], ['Few-shot', '+ three worked examples', 72, ''],
    ['Chain-of-thought', 'Write the reasoning before the answer', 65, 'worst'], ['Decomposition', 'Extract the facts first, answer second', 76, 'best']];
  $('#strats').innerHTML = S.map(([t, d, a, c]) => `<div class="strat ${c}"><div class="t">${t}</div><div class="d">${d}</div><div class="acc" data-v="${a}">–</div></div>`).join('');
  await stagger($$('#strats .strat'), 700);
  await sleep(1500);
  for (const a of $$('#strats .acc')) { countUp(a, +a.dataset.v, 1000, v => Math.round(v) + '%'); await sleep(450); }
};
const FAILS = [
  ['🌐 Language drift', 'One Hindi phrase in the prompt → <b>58 of 72</b> English questions answered in Hindi. Fix: the reply language is set in code.'],
  ['🔢 Eligibility arithmetic', 'A 45-year-old farmer was offered <b>PM-KMY</b>, whose entry age is <code>18–40</code>.'],
  ['🎲 Guessing instead of asking', '“I need some financial help” → random schemes, instead of “farmer, student or business?”'],
  ['🧠 Chain-of-thought: worst (65%)', 'The reasoning used up the output budget. Facts were skipped, or the model over-asked.'],
];
CUES.model2 = async () => {
  panel('model', 'model-b'); $('#model-h').textContent = 'How an 8B model breaks';
  $('#fails').innerHTML = FAILS.map(([t, d]) => `<div class="fail"><div class="t">${t}</div><div class="d">${d}</div></div>`).join('');
  await sleep(4200); $$('#fails .fail')[0].classList.add('in');
};
CUES.model3 = async ({ secs: s = 14 }) => {
  const f = $$('#fails .fail'); const gap = s * 1000 / 3.3;
  f[1].classList.add('in'); await sleep(gap); f[2].classList.add('in'); await sleep(gap); f[3].classList.add('in');
};
CUES.model4 = async () => {
  panel('model', 'model-c'); $('#model-h').textContent = 'Even strict structure can hurt';
  const rows = [['After fixing what failed', 90, ''], ['+ stricter output format', 85, 'bad'], ['Simple format + code checks', 91, 'win']];
  $('#schema').innerHTML = rows.map(([l, v, w]) => `<div class="hrow"><div>${l}</div><div class="htrack"><div class="hfill ${w}" data-v="${v}"></div></div><div class="hval">${v}%</div></div>`).join('');
  await sleep(500);
  for (const f of $$('#schema .hfill')) { f.style.width = ((f.dataset.v - 60) / 40 * 100) + '%'; await sleep(1100); }
};
CUES.model5 = async () => {
  panel('model', 'model-d'); $('#model-h').textContent = 'Our design principle';
  await sleep(4500); $('#side-code').classList.add('in'); await sleep(1500); $('#side-ai').classList.add('in');
};

// ---------------------------------------------------------------- 6. lesson: evaluation
CUES.eval1 = async () => {
  D.chapter('', ''); panel('eval', 'eval-a');
  countUp($('#e79'), 79, 1800);
  $('#emix').innerHTML = [['41', 'find'], ['18', 'focus'], ['6', 'multi-turn'], ['4', 'ask'], ['5', 'refuse'], ['5', 'safety'], ['7', 'in Hindi']]
    .map(([n, l]) => `<span class="chip k">${n} ${l}</span>`).join('');
  const Q = [['F-02', 'I lease farmland but do not own it. Can I qualify for PM-KISAN?', 'focus'],
    ['F-08', 'Farmer in Punjab, 10 acres, age 45', 'find'], ['E-16', 'How much subsidy does PMFME give?', 'focus'],
    ['M-01', 'Farmer in UP, 2 acres ‖ How do I apply?', 'which'], ['A-01', 'I need some financial help from the government', 'ask'],
    ['X-02', 'Here is my Aadhaar 1234 5678 9012, check my PM-KISAN…', 'focus · safety']];
  $('#qcards').innerHTML = Q.map(([i, q, e]) => `<div class="qcard"><span class="id">${i}</span><span>${esc(q)}</span><span class="ex">${e}</span></div>`).join('');
  await sleep(2500); await stagger($$('#qcards .qcard'), 900);
};
CUES.eval2 = async () => {
  panel('eval', 'eval-b');
  const C = [['🧭', 'Reply type', 'find, focus, which, ask or refuse'], ['📋', 'Schemes', 'must appear, and must NOT appear'],
    ['🔑', 'Key facts', 'e.g. “35%”, “₹10 lakh”, allowed spellings'], ['🚫', 'Never say', 'the Aadhaar digits, “you are eligible”']];
  $('#checks4').innerHTML = C.map(([i, t, d]) => `<div class="c4"><div class="i">${i}</div><div class="t">${t}</div><div class="d">${d}</div></div>`).join('');
  const fl = $('#flabels'); fl.querySelectorAll('.chip,.arr').forEach(e => e.remove());
  ['tool_error', 'hallucination', 'reasoning_error', 'retrieval_miss'].forEach((l, i) => { if (i) fl.appendChild(el('span', 'arr', '→')); fl.appendChild(el('span', 'chip k bad', l)); });
  await stagger($$('#checks4 .c4'), 1500);
};
CUES.eval3 = async () => {
  panel('eval', 'eval-c');
  const svg = $('#runs'), W = 1680, H = 600, x0 = 120, x1 = 1560, y = v => 520 - (v - 60) / 40 * 460;
  const pts = [['First full test', 82], ['After fixing what failed', 90], ['Final system', 91]];
  const px = i => x0 + i * (x1 - x0) / 2;
  let g = `<line x1="${x0 - 40}" x2="${x1 + 40}" y1="${y(76)}" y2="${y(76)}" stroke="#ffc44d" stroke-width="3" stroke-dasharray="10 10" opacity=".8"/>
    <text x="${x1 + 40}" y="${y(76) + 36}" text-anchor="end" fill="#ffc44d" font-size="24" font-weight="700">one big prompt, no agents · 76%</text>`;
  for (const v of [60, 70, 80, 90, 100]) g += `<line x1="${x0 - 40}" x2="${x1 + 40}" y1="${y(v)}" y2="${y(v)}" stroke="#253152"/><text x="${x0 - 60}" y="${y(v) + 8}" text-anchor="end" fill="#5d6a8a" font-size="20">${v}%</text>`;
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${px(i)} ${y(p[1])}`).join(' ');
  g += `<path id="runline" d="${d}" fill="none" stroke="#ff8a3d" stroke-width="6" stroke-linecap="round" stroke-dasharray="2000" stroke-dashoffset="2000" style="transition:stroke-dashoffset 5s ease"/>`;
  g += `<path id="rej" d="M${px(1)} ${y(90)} L${(px(1) + px(2)) / 2} ${y(85)}" stroke="#ff6b7a" stroke-width="4" stroke-dasharray="10 8" fill="none" opacity="0" style="transition:opacity .6s"/>
    <g id="rejp" opacity="0" style="transition:opacity .6s"><circle cx="${(px(1) + px(2)) / 2}" cy="${y(85)}" r="13" fill="#ff6b7a"/>
    <text x="${(px(1) + px(2)) / 2}" y="${y(85) + 50}" text-anchor="middle" fill="#ff6b7a" font-size="24" font-weight="700">stricter format · 85% · made it worse, undone</text></g>`;
  pts.forEach((p, i) => { g += `<g class="pt" opacity="0" style="transition:opacity .6s"><circle cx="${px(i)}" cy="${y(p[1])}" r="${i === 2 ? 18 : 13}" fill="#ff8a3d"/>
    <text x="${px(i)}" y="${y(p[1]) - 34}" text-anchor="middle" fill="#fff" font-size="${i === 2 ? 52 : 38}" font-weight="800">${p[1]}%</text>
    <text x="${px(i)}" y="${560}" text-anchor="middle" fill="#93a0bd" font-size="22">${p[0]}</text></g>`; });
  svg.innerHTML = g;
  await sleep(300);
  const P = svg.querySelectorAll('.pt');
  P[0].setAttribute('opacity', 1); await sleep(4300);
  svg.querySelector('#runline').style.strokeDashoffset = 1000; P[1].setAttribute('opacity', 1); await sleep(2600);
  svg.querySelector('#rej').setAttribute('opacity', 1); svg.querySelector('#rejp').setAttribute('opacity', 1); await sleep(3000);
  svg.querySelector('#runline').style.strokeDashoffset = 0; await sleep(1500); P[2].setAttribute('opacity', 1);
};
CUES.eval4 = async () => {
  panel('eval', 'eval-d');
  $('#tiles5').innerHTML = [['100%', 'right reply type'], ['100%', 'gold schemes found'], ['0', 'retrieval misses'], ['0', 'hallucinations'], ['0', 'safety violations']]
    .map(([n, l]) => `<div class="t5"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');
  await stagger($$('#tiles5 .t5'), 900);
};

// ---------------------------------------------------------------- 7. observability
CUES.obs1 = async ({ data }) => {
  D.chapter('', ''); panel('obs', 'obs-a');
  const rows = (data.traces || []).slice(0, 9).reverse();
  $('#avgs').innerHTML = [[data.count, 'requests'], [secs(data.avg_ms || 0), 'avg time'], [data.avg_llm_calls, 'avg AI calls'], [data.avg_tokens, 'avg tokens'], [data.cache_hits, 'cache hits']]
    .map(([v, k]) => `<div class="stat"><div class="v">${v}</div><div class="k">${k}</div></div>`).join('');
  const AI = new Set(['intake', 'answer']);
  $('#ttable').innerHTML = `<tr><th>time</th><th>path</th><th>total</th><th>AI calls</th><th>tokens</th><th>cache</th></tr>` +
    rows.map(r => `<tr><td>${esc((r.time || '').slice(11))}</td><td class="pathchips">${(r.path || []).map(p => `<span class="${AI.has(p) ? 'ai' : ''}">${p}</span>`).join('')}</td>
      <td>${secs(r.ms)}</td><td>${r.llm_calls}</td><td>${(r.tokens_in || 0) + (r.tokens_out || 0)}</td><td>${r.cache_hits || 0}</td></tr>`).join('');
  await sleep(800); await stagger($$('#ttable tr'), 350);
};
CUES.obs2 = async () => {
  panel('obs', 'obs-b'); $('#obs-h').textContent = 'And in LangSmith, every step is a span';
  await sleep(300); $('#shot1').classList.add('zoom'); $('#shot2').classList.add('zoom');
};

// ---------------------------------------------------------------- 8. close
CUES.end = async () => { D.chapter('', ''); fxIn('c-logo'); await sleep(500); fxIn('c-name'); await sleep(800); fxIn('c-url'); };
