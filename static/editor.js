// KNXdoit v19 - Proje editörü
// v1'in sürükle-bırak çizim mantığı + v18 kural motoru.
// Kablolar piksel olarak değil, BAĞLANTI olarak saklanır (kanal -> yük,
// düğüm -> düğüm); ekrandaki çizgi her seferinde bu bağlantıdan çizilir.

import { renderHealth, escapeHtml } from "./rules.js";
import { downloadFile } from "./pdf.js";
import { drawPanel } from "./canvas.js";

const $ = id => document.getElementById(id);
const esc = escapeHtml;
const uid = () => Math.random().toString(36).slice(2, 10);

// Katalog sunucudan gelir (/api/catalog, kaynak: catalog.py)
let ROOM_DEVICES = [], PANEL_PRODUCTS = [], CATEGORY_LABEL = {};
let COMPAT = {}, COMPAT_NOTE = {};
let DEV = {}, DEV_BY_ID = {};
let ENERGY = new Set(), BUS = new Set(), OUTPUT_CATS = new Set();

async function loadCatalog() {
  const c = await (await fetch("/api/catalog")).json();
  ROOM_DEVICES = c.devices;
  PANEL_PRODUCTS = c.products;
  CATEGORY_LABEL = c.categoryLabel;
  COMPAT = c.compat;
  COMPAT_NOTE = c.compatNote;
  DEV_BY_ID = Object.fromEntries(ROOM_DEVICES.map(d => [d.id, d]));
  DEV = {};
  ROOM_DEVICES.forEach(d => { if (!DEV[d.type]) DEV[d.type] = d; });
  ENERGY = new Set(ROOM_DEVICES.filter(d => d.kind !== "bus").map(d => d.type));
  BUS = new Set(ROOM_DEVICES.filter(d => d.kind === "bus").map(d => d.type));
  OUTPUT_CATS = new Set(Object.values(COMPAT).flat().map(o => o.category));
}

function devInfo(d) { return DEV[d.type] || { icon: "•", label: d.type, kind: "load" }; }

const COLOR_ENERGY = "#8B4513";
const COLOR_BUS = "#16a34a";
const COLOR_CONTROL = "#0284c7";   // gateway -> klima / VRF / DALI kontrol hattı
const GATEWAY_CATS = new Set(["ac_gateway", "vrf_gateway", "dali"]);

const HINTS = {
  select: "Odaları, panoları ve kollektörleri başlığından tutup sürükleyin.",
  room: "Boş alanda sürükleyerek oda çizin.",
  panel: "Boş alanda sürükleyerek pano çizin.",
  collector: "Boş alanda sürükleyerek kollektör dolabı çizin.",
  energy: "Önce panodaki boş kanala, sonra odadaki yüke (lamba, perde, vana…) tıklayın.",
  bus: "KNX bus: panonun BUS noktasına veya bir KNX cihazına, sonra bağlanacak KNX cihazına tıklayın.",
  rename: "İsmini değiştirmek istediğiniz oda, pano veya kollektörün başlığına tıklayın.",
  delete: "Silmek için kabloya, cihaza, ürün adına veya başlığa tıklayın. (Ctrl+Z ile geri alınır)"
};

// --------------------------------
// DURUM
// --------------------------------

function newFloor(name) {
  return { id: uid(), name, rooms: [], panels: [], collectors: [] };
}

let state = { floors: [newFloor("Zemin Kat")], links: [], bus: [] };
let cur = 0;
let tool = "select";
let pick = null;          // enerji: {prod, ch} · bus: "node"
let undoStack = [];
let selRoom = null;       // seçili oda id (cihazlar buraya eklenir)
let selPanel = null;      // seçili pano id (ürünler buraya eklenir)
let zoom = 1;
let view = "plan";
let dirty = false;
let projectId = JSON.parse($("projectId").textContent);

const floor = () => state.floors[cur];

function snapshot() {
  undoStack.push(JSON.stringify({ state, cur }));
  if (undoStack.length > 50) undoStack.shift();
}

function undo() {
  if (!undoStack.length) return toast("Geri alınacak işlem yok.");
  const prev = JSON.parse(undoStack.pop());
  state = prev.state;
  cur = Math.min(prev.cur, state.floors.length - 1);
  pick = null;
  changed();
}

function changed() {
  dirty = true;
  $("dirty").textContent = "● Kaydedilmedi";
  render();
  scheduleCheck();
}

// --------------------------------
// YARDIMCILAR
// --------------------------------

function toast(msg, kind = "info") {
  const t = $("toast");
  t.textContent = msg;
  t.className = `ed-toast ${kind}`;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), kind === "error" ? 5000 : 2600);
}

let modalOk = null;
function openModal(title, html, onOk) {
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = html;
  modalOk = onOk;
  $("modal").classList.remove("hidden");
  const first = $("modalBody").querySelector("input,select");
  if (first) setTimeout(() => first.focus(), 30);
}
function closeModal() {
  $("modal").classList.add("hidden");
  $("modalOk").style.display = "";
  modalOk = null;
}
$("modalCancel").onclick = closeModal;
$("modalOk").onclick = () => { const f = modalOk; if (!f || f() !== false) closeModal(); };
$("modalBody").addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target.tagName === "INPUT") $("modalOk").click();
});

// Dahili röleli paneller (Akubela): "dr_<cihazId>_<örnek>" sahte ürün
function relayCount(dev) { return Number((DEV[dev.type] || {}).relays || 0); }
const relayProdId = (devId, k) => `dr_${devId}_${k}`;

function findProduct(prodId) {
  if (String(prodId).startsWith("dr_")) {
    const m = String(prodId).match(/^dr_(.+)_(\d+)$/);
    if (!m) return null;
    const d = findDevice(m[1]);
    const k = Number(m[2]);
    if (!d || k >= d.dev.count || !relayCount(d.dev)) return null;
    return {
      floor: d.floor, panel: { name: d.room.name, products: [] },
      prod: { id: prodId, name: `${d.dev.label} ${k + 1} dahili röle`, category: "relay", channels: relayCount(d.dev) }
    };
  }
  for (const f of state.floors)
    for (const p of f.panels)
      for (const pr of p.products)
        if (pr.id === prodId) return { floor: f, panel: p, prod: pr };
  return null;
}
function findDevice(devId) {
  for (const f of state.floors)
    for (const r of f.rooms)
      for (const d of r.devices)
        if (d.id === devId) return { floor: f, room: r, dev: d };
  return null;
}
function findCollector(colId) {
  for (const f of state.floors)
    for (const c of f.collectors)
      if (c.id === colId) return { floor: f, col: c };
  return null;
}

function sameTarget(a, b) {
  return a.kind === b.kind && (
    a.kind === "dev" ? a.dev === b.dev && a.k === b.k
                     : a.col === b.col && a.v === b.v
  );
}

// kanal doluluğu: prodId -> ci -> {link, role}
function occupancy() {
  const occ = {};
  for (const l of state.links) {
    occ[l.prod] = occ[l.prod] || {};
    occ[l.prod][l.ch] = { link: l, role: "main" };
    if (l.span === 2) occ[l.prod][l.ch + 1] = { link: l, role: "down" };
  }
  return occ;
}

function targetType(to) {
  if (to.kind === "valve") return "valve";
  const d = findDevice(to.dev);
  return d ? d.dev.type : null;
}

function targetName(to) {
  if (to.kind === "valve") {
    const c = findCollector(to.col);
    return c ? `${c.col.name} / Vana ${to.v + 1}` : "?";
  }
  const d = findDevice(to.dev);
  return d ? `${d.room.name} / ${d.dev.label} ${to.k + 1}` : "?";
}

// --------------------------------
// KURAL: enerji kablosu bağlanabilir mi? (sunucudaki kontrolle aynı)
// --------------------------------

function checkEnergy(prod, ch, to) {
  const ttype = targetType(to);
  if (!ENERGY.has(ttype)) {
    return { ok: false, msg: "Bu bir KNX cihazı; aktüatör kanalına bağlanmaz. Bus Kablosu aracını kullanın." };
  }
  if (!OUTPUT_CATS.has(prod.category)) {
    return { ok: false, msg: `${prod.name} ürününün yük / kontrol çıkışı yok.` };
  }
  if (state.links.some(l => sameTarget(l.to, to))) {
    return { ok: false, msg: `${targetName(to)} zaten bir kanala bağlı. Bir yük tek çıkıştan beslenir.` };
  }
  const occ = occupancy()[prod.id] || {};
  if (occ[ch]) return { ok: false, msg: `Kanal ${ch + 1} dolu.` };

  const opts = COMPAT[ttype] || [];
  const opt = opts.find(o => o.category === prod.category);
  if (!opt) {
    const want = opts.length ? CATEGORY_LABEL[opts[0].category] : "uygun";
    const label = (DEV[ttype] || {}).label || ttype;
    return { ok: false, msg: `${label} için ${want} kanalı gerekli. ${COMPAT_NOTE[ttype] || ""}`.trim() };
  }
  if (opt.span === 2 && (ch + 1 >= prod.channels || occ[ch + 1])) {
    return { ok: false, msg: `Bu bağlantı 2 kanal kaplar; yanındaki kanal (${ch + 2}) da boş olmalı.` };
  }
  return { ok: true, span: opt.span, warn: opt.warn || null };
}

// --------------------------------
// KURAL: bus kablosu
// --------------------------------

function nodeOk(node) {
  const [kind, id] = node.split(":");
  if (kind === "panel") return { ok: true };
  if (kind === "dev") {
    const d = findDevice(id);
    if (d && BUS.has(d.dev.type)) return { ok: true };
    return { ok: false, msg: `${d ? d.dev.label : "Bu cihaz"} KNX bus cihazı değil; bus kablosu bağlanmaz. Enerji Kablosu aracıyla aktüatör / gateway kanalına bağlayın.` };
  }
  return { ok: false, msg: "Kollektör dolabına KNX bus girmez." };
}

function busConnected(a, b) {
  const adj = {};
  for (const e of state.bus) {
    if (e.floor !== floor().id) continue;
    (adj[e.a] = adj[e.a] || []).push(e.b);
    (adj[e.b] = adj[e.b] || []).push(e.a);
  }
  const seen = new Set([a]);
  const q = [a];
  while (q.length) {
    const n = q.shift();
    if (n === b) return true;
    for (const m of adj[n] || []) if (!seen.has(m)) { seen.add(m); q.push(m); }
  }
  return false;
}

function nodeName(node) {
  const [kind, id, k] = node.split(":");
  if (kind === "panel") {
    const p = floor().panels.find(p => p.id === id);
    return p ? p.name : "Pano";
  }
  const d = findDevice(id);
  return d ? `${d.room.name} / ${d.dev.label} ${Number(k) + 1}` : "?";
}

// --------------------------------
// TEMİZLİK: silinen öğelere kalan kabloları kaldır
// --------------------------------

function prune() {
  state.links = state.links.filter(l => {
    const p = findProduct(l.prod);
    if (!p || l.ch + (l.span || 1) > p.prod.channels) return false;
    if (l.to.kind === "dev") {
      const d = findDevice(l.to.dev);
      return d && l.to.k < d.dev.count;
    }
    const c = findCollector(l.to.col);
    return c && l.to.v < c.col.valves;
  });
  const alive = node => {
    const [kind, id, k] = node.split(":");
    if (kind === "panel") return state.floors.some(f => f.panels.some(p => p.id === id));
    const d = findDevice(id);
    return d && Number(k) < d.dev.count;
  };
  state.bus = state.bus.filter(e => alive(e.a) && alive(e.b));
}

// --------------------------------
// ÇİZİM (DOM)
// --------------------------------

const cv = $("cv");
const wc = $("wc");
const stage = $("stage");
const ctx = wc.getContext("2d");

function render() {
  renderTabs();
  const f = floor();
  const occ = occupancy();
  cv.innerHTML =
    f.rooms.map(roomHtml).join("") +
    f.panels.map(p => panelHtml(p, occ)).join("") +
    f.collectors.map(collectorHtml).join("") +
    (f.rooms.length + f.panels.length + f.collectors.length === 0
      ? `<div class="ed-empty">Başlamak için soldan <b>▭ Oda Çiz</b> veya <b>▪ Pano Çiz</b> seçip boş alanda sürükleyin.</div>`
      : "");
  fixSelection();
  markPick();
  markSelection();
  drawWires();
  renderTargets();
  renderStats();
  if (view === "din") renderDin();
  $("cableCount").textContent =
    `${state.links.filter(l => l.floor === f.id).length} enerji · ` +
    `${state.bus.filter(e => e.floor === f.id).length} bus kablosu (bu kat)`;
}

function renderTabs() {
  $("floorTabs").innerHTML = state.floors.map((f, i) =>
    `<button class="ed-tab ${i === cur ? "active" : ""}" data-floor="${i}">${esc(f.name)}</button>`
  ).join("");
}

function roomHtml(r) {
  const total = r.devices.reduce((a, d) => a + d.count, 0);
  const chips = r.devices.flatMap(d =>
    Array.from({ length: d.count }, (_, k) => {
      const info = devInfo(d);
      const cls = info.kind === "bus" ? "knx" : info.kind === "control" ? "ctl" : "energy";
      const kindTxt = info.kind === "bus" ? "KNX cihazı" : info.kind === "control" ? "Gateway ile kontrol" : "230V yük";
      return `<button class="dchip ${cls}" id="dv-${d.id}-${k}" data-dev="${d.id}" data-k="${k}"
        title="${esc(d.label)} ${k + 1} · ${kindTxt}">
        <span class="ic">${info.icon}</span><span class="n">${k + 1}</span></button>`;
    })
  ).join("");
  const occ = occupancy();
  const relays = r.devices.filter(d => relayCount(d)).flatMap(d =>
    Array.from({ length: d.count }, (_, k) => {
      const pid = relayProdId(d.id, k);
      const o = occ[pid] || {};
      const btns = Array.from({ length: relayCount(d) }, (_, ci) => {
        const slot = o[ci];
        const t = slot ? targetType(slot.link.to) : null;
        return `<button class="chbtn mini ${slot ? "used c-" + t : ""}" id="ch-${pid}-${ci}" data-prod="${pid}" data-ch="${ci}"
          title="${esc(d.label)} ${k + 1} · dahili röle R${ci + 1}${slot ? ": " + esc(targetName(slot.link.to)) : " (boş)"}">${slot ? (DEV[t] || {}).icon || "•" : "R"}<span>${ci + 1}</span></button>`;
      }).join("");
      return `<div class="relayrow"><span>${esc(d.label)} ${k + 1} · dahili röle</span>${btns}</div>`;
    })
  ).join("");
  return `<div class="rbox" data-room="${r.id}" style="left:${r.x}px;top:${r.y}px;width:${r.w}px;min-height:${r.h}px">
    <div class="rhdr" data-drag="room:${r.id}"><span>${esc(r.name)}</span><small>${total} cihaz</small></div>
    <div class="chips">${chips}</div>${relays}
    <button class="addbtn" data-add-dev="${r.id}">+ Cihaz Ekle</button>
  </div>`;
}

function panelHtml(p, occ) {
  const prods = p.products.map(pr => {
    const isPs = pr.category === "power_supply";
    const o = occ[pr.id] || {};
    const chs = OUTPUT_CATS.has(pr.category)
      ? `<div class="chgrid" style="grid-template-columns:repeat(${Math.min(8, pr.channels)},1fr)">` +
        Array.from({ length: pr.channels }, (_, ci) => {
          const slot = o[ci];
          if (slot && slot.role === "down") {
            return `<button class="chbtn blocked" id="ch-${pr.id}-${ci}" data-prod="${pr.id}" data-ch="${ci}"
              title="Kanal ${ci + 1}: ${esc(targetName(slot.link.to))} (Aşağı)">🔒<span>${ci + 1}</span></button>`;
          }
          if (slot) {
            const t = targetType(slot.link.to);
            return `<button class="chbtn used c-${t}" id="ch-${pr.id}-${ci}" data-prod="${pr.id}" data-ch="${ci}"
              title="Kanal ${ci + 1}: ${esc(targetName(slot.link.to))}">${(DEV[t] || {}).icon || "•"}<span>${ci + 1}</span></button>`;
          }
          return `<button class="chbtn" id="ch-${pr.id}-${ci}" data-prod="${pr.id}" data-ch="${ci}"
            title="Kanal ${ci + 1}: boş">−<span>${ci + 1}</span></button>`;
        }).join("") + `</div>`
      : "";
    return `<div class="prod">
      <div class="ptitle" data-prod-title="${pr.id}" title="${esc(CATEGORY_LABEL[pr.category] || "")}">${esc(pr.name)}</div>
      <div class="klemens ${isPs ? "ps" : ""}" id="kl-${pr.id}">
        <span>${isPs ? "KNX çıkış" : "KNX"}</span><i class="minus">−</i><i class="plus">+</i><em>30V DC</em>
      </div>
      ${chs}
    </div>`;
  }).join("");
  return `<div class="pbox" data-panel="${p.id}" style="left:${p.x}px;top:${p.y}px">
    <div class="phdr" data-drag="panel:${p.id}">
      <span>${esc(p.name)}</span>
      <button class="busport" id="bp-${p.id}" data-node="panel:${p.id}" title="KNX bus çıkışı">BUS ●</button>
    </div>
    ${prods || `<div class="pempty">Ürün yok</div>`}
    <button class="addbtn" data-add-prod="${p.id}">+ Ürün Ekle</button>
  </div>`;
}

function collectorHtml(c) {
  const vanas = Array.from({ length: c.valves }, (_, v) =>
    `<button class="vana" id="va-${c.id}-${v}" data-col="${c.id}" data-v="${v}" title="Vana ${v + 1}">
      <b>VANA</b><i></i><span>${v + 1}</span></button>`
  ).join("");
  return `<div class="cbox" style="left:${c.x}px;top:${c.y}px;width:${c.w}px;min-height:${c.h}px">
    <div class="chdr" data-drag="collector:${c.id}"><span>🔥 ${esc(c.name)}</span><small>${c.valves} vana</small></div>
    <div class="vanas">${vanas}</div>
    <div class="cnote">⚡ Sadece enerji kablosu (230V) · KNX bus girmez</div>
  </div>`;
}

function markPick() {
  document.querySelectorAll(".picked").forEach(e => e.classList.remove("picked"));
  if (!pick) return;
  const el = tool === "energy"
    ? $(`ch-${pick.prod}-${pick.ch}`)
    : document.querySelector(`[data-node="${pick}"]`) || nodeEl(pick);
  if (el) el.classList.add("picked");
}

// --------------------------------
// ÇİZİM (KABLOLAR)
// --------------------------------

function center(el) {
  const s = stage.getBoundingClientRect();
  const r = el.getBoundingClientRect();
  return {
    x: (r.left - s.left + r.width / 2) / zoom,
    y: (r.top - s.top + r.height / 2) / zoom
  };
}

function nodeEl(node) {
  const [kind, id, k] = node.split(":");
  return kind === "panel" ? $(`bp-${id}`) : $(`dv-${id}-${k}`);
}

function targetEl(to) {
  return to.kind === "dev" ? $(`dv-${to.dev}-${to.k}`) : $(`va-${to.col}-${to.v}`);
}

function curve(a, b, color, width, dash) {
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.setLineDash(dash || []);
  const mx = (a.x + b.x) / 2;
  ctx.moveTo(a.x, a.y);
  ctx.bezierCurveTo(mx, a.y, mx, b.y, b.x, b.y);
  ctx.stroke();
  ctx.setLineDash([]);
}

let wireGeom = [];   // silme aracı için: {type, id, a, b}

function drawWires() {
  ctx.clearRect(0, 0, wc.width, wc.height);
  wireGeom = [];
  const f = floor();

  // Pano içi bus zinciri: PS -> modüller (klemensler)
  for (const p of f.panels) {
    const ps = p.products.find(x => x.category === "power_supply");
    if (!ps) continue;
    const chain = [ps, ...p.products.filter(x => x.category !== "power_supply")];
    for (let i = 1; i < chain.length; i++) {
      const a = $(`kl-${chain[i - 1].id}`), b = $(`kl-${chain[i].id}`);
      if (!a || !b) continue;
      const ca = center(a), cb = center(b);
      ctx.beginPath();
      ctx.strokeStyle = COLOR_BUS;
      ctx.lineWidth = 2;
      const x = Math.max(ca.x, cb.x) + 70;
      ctx.moveTo(ca.x + 40, ca.y); ctx.lineTo(x, ca.y); ctx.lineTo(x, cb.y); ctx.lineTo(cb.x + 40, cb.y);
      ctx.stroke();
    }
  }

  for (const l of state.links) {
    if (l.floor !== f.id) continue;
    const a = $(`ch-${l.prod}-${l.ch}`), b = targetEl(l.to);
    if (!a || !b) continue;
    const ca = center(a), cb = center(b);
    const pf = findProduct(l.prod);
    const isCtl = pf && GATEWAY_CATS.has(pf.prod.category);
    curve(ca, cb, isCtl ? COLOR_CONTROL : COLOR_ENERGY, 2.5, isCtl ? [8, 5] : null);
    wireGeom.push({ type: "link", id: l.id, a: ca, b: cb });
    if (l.span === 2) {
      const a2 = $(`ch-${l.prod}-${l.ch + 1}`);
      if (a2) {
        const c2 = center(a2);
        curve(c2, { x: cb.x + 6, y: cb.y + 6 }, COLOR_ENERGY, 2.5, [6, 4]);
        wireGeom.push({ type: "link", id: l.id, a: c2, b: cb });
      }
    }
  }

  for (const e of state.bus) {
    if (e.floor !== f.id) continue;
    const a = nodeEl(e.a), b = nodeEl(e.b);
    if (!a || !b) continue;
    const ca = center(a), cb = center(b);
    curve(ca, cb, COLOR_BUS, 3.5);
    wireGeom.push({ type: "bus", id: e.id, a: ca, b: cb });
  }

  if (rubber) {
    ctx.strokeStyle = rubber.color;
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 3]);
    ctx.strokeRect(rubber.x, rubber.y, rubber.w, rubber.h);
    ctx.setLineDash([]);
  }
}

// noktanın kablo eğrisine uzaklığı (eğriyi örnekleyerek)
function nearestWire(pt) {
  let best = null, bestD = 10;
  for (const w of wireGeom) {
    const mx = (w.a.x + w.b.x) / 2;
    for (let i = 0; i <= 40; i++) {
      const t = i / 40, u = 1 - t;
      const x = u * u * u * w.a.x + 3 * u * u * t * mx + 3 * u * t * t * mx + t * t * t * w.b.x;
      const y = u * u * u * w.a.y + 3 * u * u * t * w.a.y + 3 * u * t * t * w.b.y + t * t * t * w.b.y;
      const d = Math.hypot(pt.x - x, pt.y - y);
      if (d < bestD) { bestD = d; best = w; }
    }
  }
  return best;
}

// --------------------------------
// ARAÇLAR
// --------------------------------

function setTool(t) {
  tool = t;
  pick = null;
  document.querySelectorAll("#tools button").forEach(b =>
    b.classList.toggle("active", b.dataset.tool === t));
  $("hint").textContent = HINTS[t] || "";
  stage.dataset.tool = t;
  markPick();
}

$("tools").addEventListener("click", e => {
  const b = e.target.closest("button[data-tool]");
  if (b) setTool(b.dataset.tool);
});

// --------------------------------
// FARE: çizim (rubber band) ve sürükleme
// --------------------------------

let rubber = null;
let dragging = null;

function stagePoint(e) {
  const s = stage.getBoundingClientRect();
  return { x: (e.clientX - s.left) / zoom, y: (e.clientY - s.top) / zoom };
}

cv.addEventListener("mousedown", e => {
  if (e.button !== 0) return;
  const handle = e.target.closest("[data-drag]");

  if (handle && !e.target.closest("button") &&
      !["room", "panel", "collector"].includes(tool) && tool !== "rename" && tool !== "delete") {
    const [kind, id] = handle.dataset.drag.split(":");
    const obj = floor()[kind === "room" ? "rooms" : kind === "panel" ? "panels" : "collectors"]
      .find(o => o.id === id);
    if (!obj) return;
    if (kind === "room" && selRoom !== id) { selRoom = id; markSelection(); renderTargets(); }
    if (kind === "panel" && selPanel !== id) { selPanel = id; markSelection(); renderTargets(); }
    const p = stagePoint(e);
    dragging = { obj, el: handle.parentElement, dx: p.x - obj.x, dy: p.y - obj.y, moved: false, snap: JSON.stringify({ state, cur }) };
    e.preventDefault();
    return;
  }

  if (["room", "panel", "collector"].includes(tool) &&
      (e.target === cv || e.target.classList.contains("ed-empty"))) {
    const p = stagePoint(e);
    rubber = {
      sx: p.x, sy: p.y, x: p.x, y: p.y, w: 0, h: 0,
      color: tool === "room" ? "#185FA5" : tool === "collector" ? "#dc2626" : "#5F5E5A"
    };
    e.preventDefault();
  }
});

window.addEventListener("mousemove", e => {
  if (dragging) {
    const p = stagePoint(e);
    const x = Math.max(0, Math.round(p.x - dragging.dx));
    const y = Math.max(0, Math.round(p.y - dragging.dy));
    if (!dragging.moved) {
      undoStack.push(dragging.snap);
      dragging.moved = true;
    }
    dragging.obj.x = x;
    dragging.obj.y = y;
    dragging.el.style.left = x + "px";
    dragging.el.style.top = y + "px";
    drawWires();
  } else if (rubber) {
    const p = stagePoint(e);
    rubber.x = Math.min(rubber.sx, p.x);
    rubber.y = Math.min(rubber.sy, p.y);
    rubber.w = Math.abs(p.x - rubber.sx);
    rubber.h = Math.abs(p.y - rubber.sy);
    drawWires();
  }
});

window.addEventListener("mouseup", () => {
  if (dragging) {
    if (dragging.moved) { dirty = true; $("dirty").textContent = "● Kaydedilmedi"; }
    dragging = null;
    return;
  }
  if (!rubber) return;
  const r = rubber;
  rubber = null;
  drawWires();
  if (r.w < 20 || r.h < 20) return;
  createShape(tool, r);
});

function createShape(kind, r) {
  const f = floor();
  if (kind === "room") {
    openModal("Oda Ekle",
      `<label>Oda adı<input id="mName" value="Oda ${f.rooms.length + 1}"></label>`,
      () => {
        snapshot();
        const id = uid();
        f.rooms.push({ id, name: $("mName").value.trim() || "Oda", x: r.x, y: r.y,
          w: Math.max(r.w, 170), h: Math.max(r.h, 100), devices: [] });
        selRoom = id;
        setTool("select");
        changed();
        toast("Oda eklendi. Soldaki listeden bu odaya cihaz ekleyebilirsiniz.");
      });
  } else if (kind === "panel") {
    openModal("Pano Ekle",
      `<label>Pano adı<input id="mName" value="${esc(f.name)} Panosu"></label>`,
      () => {
        snapshot();
        const id = uid();
        f.panels.push({ id, name: $("mName").value.trim() || "Pano", x: r.x, y: r.y, products: [] });
        selPanel = id;
        setTool("select");
        changed();
        toast("Pano eklendi. Soldaki listeden ürün ekleyebilirsiniz.");
      });
  } else if (kind === "collector") {
    openModal("Kollektör Dolabı Ekle",
      `<label>Ad<input id="mName" value="Kollektör Dolabı"></label>
       <label>Vana sayısı<input id="mCount" type="number" min="1" max="32" value="6"></label>`,
      () => {
        const n = Math.min(32, Math.max(1, Number($("mCount").value) || 1));
        snapshot();
        f.collectors.push({ id: uid(), name: $("mName").value.trim() || "Kollektör", x: r.x, y: r.y,
          w: Math.max(r.w, 170), h: Math.max(r.h, 100), valves: n });
        changed();
      });
  }
}

// --------------------------------
// TIKLAMA: cihaz/ürün ekleme, kablo, silme, isim
// --------------------------------

cv.addEventListener("click", e => {
  const t = e.target;

  const addDev = t.closest("[data-add-dev]");
  if (addDev) { selRoom = addDev.dataset.addDev; markSelection(); renderTargets(); return showDeviceModal(addDev.dataset.addDev); }
  const addProd = t.closest("[data-add-prod]");
  if (addProd) { selPanel = addProd.dataset.addProd; markSelection(); renderTargets(); return showProductModal(addProd.dataset.addProd); }

  // Seçim: odaya / panoya tıklanınca sol paneldeki hedef o olur
  if (tool === "select" || tool === "energy" || tool === "bus") {
    const rb = t.closest("[data-room]"), pb = t.closest("[data-panel]");
    if (rb && rb.dataset.room !== selRoom) { selRoom = rb.dataset.room; markSelection(); renderTargets(); }
    if (pb && pb.dataset.panel !== selPanel) { selPanel = pb.dataset.panel; markSelection(); renderTargets(); }
  }

  const ch = t.closest("[data-ch]");
  const chip = t.closest("[data-dev]");
  const vana = t.closest("[data-col]");
  const port = t.closest("[data-node]");
  const ptitle = t.closest("[data-prod-title]");
  const hdr = t.closest("[data-drag]");

  if (tool === "delete") return onDelete(e, { ch, chip, vana, ptitle, hdr });
  if (tool === "rename") { if (hdr && !port) onRename(hdr); return; }

  if (tool === "energy") {
    if (ch) return pickChannel(ch.dataset.prod, Number(ch.dataset.ch));
    if (chip || vana) {
      if (!pick) return toast("Önce panodaki boş bir kanala tıklayın.");
      const to = chip
        ? { kind: "dev", dev: chip.dataset.dev, k: Number(chip.dataset.k) }
        : { kind: "valve", col: vana.dataset.col, v: Number(vana.dataset.v) };
      return connectEnergy(to);
    }
    if (port) return toast("Bu, KNX bus çıkışı. Enerji kablosu aktüatör kanalından çekilir.", "error");
    return;
  }

  if (tool === "bus") {
    let node = null;
    if (port) node = port.dataset.node;
    else if (chip) node = `dev:${chip.dataset.dev}:${chip.dataset.k}`;
    else if (vana) return toast("Kollektör dolabına KNX bus girmez.", "error");
    else if (ch) return toast("Aktüatör kanalları 230V çıkışıdır. Bus için panonun BUS noktasını kullanın.", "error");
    if (node) return pickBus(node);
    return;
  }

  if (ch && tool === "select") {
    toast("Kablo çekmek için soldan 🟫 Enerji Kablosu aracını seçin.");
  }
});

function pickChannel(prodId, ci) {
  const found = findProduct(prodId);
  if (!found) return;
  const occ = occupancy()[prodId] || {};
  if (occ[ci]) {
    return toast(`Kanal ${ci + 1} dolu: ${targetName(occ[ci].link.to)}. Silmek için 🗑 Sil aracıyla kabloya tıklayın.`);
  }
  if (!OUTPUT_CATS.has(found.prod.category)) return;
  pick = (pick && pick.prod === prodId && pick.ch === ci) ? null : { prod: prodId, ch: ci };
  markPick();
  $("hint").textContent = pick ? "Şimdi odadaki yüke veya kollektördeki vanaya tıklayın. (Esc: vazgeç)" : HINTS.energy;
}

function connectEnergy(to) {
  const found = findProduct(pick.prod);
  if (!found) return;
  const res = checkEnergy(found.prod, pick.ch, to);
  if (!res.ok) return toast(res.msg, "error");
  snapshot();
  state.links.push({
    id: uid(), floor: floor().id, prod: pick.prod, ch: pick.ch, span: res.span, to
  });
  pick = null;
  $("hint").textContent = HINTS.energy;
  changed();
  const isDr = String(found.prod.id).startsWith("dr_");
  const chTag = isDr ? "R" : "K";
  const msg = `Bağlandı: ${found.prod.name} ${chTag}${state.links.at(-1).ch + 1} → ${targetName(to)}`;
  if (isDr) {
    toast((res.warn ? res.warn + " " : "") + msg +
      " · Dikkat: dahili röle maks. 1 A (≈230 W rezistif; LED sürücülerde ani akım nedeniyle daha az).", "warn");
  } else {
    toast(res.warn || msg, res.warn ? "warn" : "info");
  }
}

function pickBus(node) {
  const ok = nodeOk(node);
  if (!ok.ok) return toast(ok.msg, "error");
  if (!pick) {
    pick = node;
    markPick();
    $("hint").textContent = "Şimdi bağlanacak KNX cihazına (veya panonun BUS noktasına) tıklayın. (Esc: vazgeç)";
    return;
  }
  if (pick === node) { pick = null; markPick(); $("hint").textContent = HINTS.bus; return; }
  const a = pick, b = node;
  if (a.startsWith("panel:") && b.startsWith("panel:")) {
    return toast("İki pano arasındaki bus bağlantısı line coupler / IP router ile yapılır; bu araçla değil.", "error");
  }
  if (busConnected(a, b)) {
    return toast(`${nodeName(a)} ile ${nodeName(b)} zaten bus ile bağlı. Bu kablo ring oluşturur; KNX'te ring yasaktır.`, "error");
  }
  snapshot();
  state.bus.push({ id: uid(), floor: floor().id, a, b });
  pick = b;   // zincirleme devam etmek kolay olsun
  changed();
  toast(`Bus: ${nodeName(a)} → ${nodeName(b)}. Zincire devam etmek için sıradaki cihaza tıklayın.`);
}

function onDelete(e, { ch, chip, vana, ptitle, hdr }) {
  const f = floor();

  // önce kablo (kanal üzerine tıklanırsa o kanalın kablosu)
  if (ch) {
    const slot = (occupancy()[ch.dataset.prod] || {})[Number(ch.dataset.ch)];
    if (slot) {
      snapshot();
      state.links = state.links.filter(l => l !== slot.link);
      changed();
      return toast("Kablo silindi.");
    }
    return;
  }
  if (e.target === cv) {
    const w = nearestWire(stagePoint(e));
    if (!w) return;
    snapshot();
    if (w.type === "link") state.links = state.links.filter(l => l.id !== w.id);
    else state.bus = state.bus.filter(b => b.id !== w.id);
    changed();
    return toast("Kablo silindi.");
  }
  if (chip) {
    const found = findDevice(chip.dataset.dev);
    if (!found) return;
    const k = Number(chip.dataset.k);
    snapshot();
    removeDeviceInstance(found.room, found.dev, k);
    changed();
    return toast(`${found.dev.label} ${k + 1} silindi.`);
  }
  if (vana) return toast("Vana sayısını değiştirmek için kollektörü silip yeniden ekleyin.");
  if (ptitle) {
    const found = findProduct(ptitle.dataset.prodTitle);
    if (!found) return;
    snapshot();
    found.panel.products = found.panel.products.filter(p => p.id !== found.prod.id);
    prune();
    changed();
    return toast(`${found.prod.name} panodan çıkarıldı.`);
  }
  if (hdr) {
    const [kind, id] = hdr.dataset.drag.split(":");
    const key = kind === "room" ? "rooms" : kind === "panel" ? "panels" : "collectors";
    const obj = f[key].find(o => o.id === id);
    openModal("Silinsin mi?",
      `<p><b>${esc(obj.name)}</b> ve ona bağlı tüm kablolar silinecek. Ctrl+Z ile geri alabilirsiniz.</p>`,
      () => {
        snapshot();
        f[key] = f[key].filter(o => o.id !== id);
        prune();
        changed();
      });
  }
}

function removeDeviceInstance(room, dev, k) {
  // bu örneğin dahili rölelerine bağlı kablolar silinir, sonrakiler kayar
  state.links = state.links
    .filter(l => l.prod !== relayProdId(dev.id, k))
    .map(l => {
      const m = String(l.prod).match(/^dr_(.+)_(\d+)$/);
      return (m && m[1] === dev.id && Number(m[2]) > k)
        ? { ...l, prod: relayProdId(dev.id, Number(m[2]) - 1) } : l;
    });
  // k'ye bağlı kabloları sil, sonrakileri bir kaydır
  state.links = state.links
    .filter(l => !(l.to.kind === "dev" && l.to.dev === dev.id && l.to.k === k))
    .map(l => (l.to.kind === "dev" && l.to.dev === dev.id && l.to.k > k)
      ? { ...l, to: { ...l.to, k: l.to.k - 1 } } : l);
  const node = n => n.startsWith(`dev:${dev.id}:`) ? Number(n.split(":")[2]) : null;
  state.bus = state.bus
    .filter(b => node(b.a) !== k && node(b.b) !== k)
    .map(b => {
      const fix = n => { const i = node(n); return i !== null && i > k ? `dev:${dev.id}:${i - 1}` : n; };
      return { ...b, a: fix(b.a), b: fix(b.b) };
    });
  dev.count -= 1;
  if (dev.count <= 0) room.devices = room.devices.filter(d => d !== dev);
}

function onRename(hdr) {
  const [kind, id] = hdr.dataset.drag.split(":");
  const key = kind === "room" ? "rooms" : kind === "panel" ? "panels" : "collectors";
  const obj = floor()[key].find(o => o.id === id);
  if (!obj) return;
  openModal("İsim Değiştir", `<label>Yeni isim<input id="mName" value="${esc(obj.name)}"></label>`, () => {
    const n = $("mName").value.trim();
    if (!n) return false;
    snapshot();
    obj.name = n;
    changed();
  });
}

// --------------------------------
// CİHAZ / ÜRÜN EKLEME
// --------------------------------

function addDevice(room, catId, qty, label) {
  const c = DEV_BY_ID[catId];
  const name = label || c.label;
  const ex = room.devices.find(d => d.type === c.type && d.label === name);
  if (ex) ex.count += qty;
  else room.devices.push({
    id: uid(), type: c.type, label: name, count: qty,
    ...(c.buttons ? { buttons: c.buttons } : {}),
    ...(c.inputs ? { inputs: c.inputs } : {})
  });
}

function deviceGroupsHtml(btnClass, attr, chosen) {
  const groups = {};
  ROOM_DEVICES.forEach(d => (groups[d.group] = groups[d.group] || []).push(d));
  // Kendi markamız (Akubela) listenin başında
  const order = Object.entries(groups).sort(([a], [b]) => (b === "Akubela") - (a === "Akubela"));
  return order.map(([g, list]) => `
    <div class="ed-group">${esc(g)}</div>
    ${list.map(d => `<button type="button" class="${btnClass} ${d.id === chosen ? "on" : ""}" ${attr}="${d.id}"
        title="${esc([d.desc, d.sku ? "Stok kodu: " + d.sku : "", d.relays ? d.relays + " dahili röle çıkışı" + (d.relayAmps ? " (maks. " + d.relayAmps + " A)" : "") : "", d.supply ? d.supply + (d.poe ? " veya PoE" : "") + " besleme gerekir" : ""].filter(Boolean).join(" · "))}">
        <span class="ic">${d.icon}</span><span class="nm">${esc(d.label)}</span>
        <small class="${d.kind === "bus" ? "k" : d.kind === "control" ? "c" : "e"}">${d.kind === "bus" ? "KNX" : d.kind === "control" ? "Gateway" : "230V"}</small>
      </button>`).join("")}`).join("");
}

function showDeviceModal(roomId) {
  const room = floor().rooms.find(r => r.id === roomId);
  if (!room) return;
  let chosen = ROOM_DEVICES[0].id;
  openModal(`${room.name}: Cihaz Ekle`, `
    <div class="devlist">${deviceGroupsHtml("ed-item devpick", "data-cat", chosen)}</div>
    <label>Adet<input id="mCount" type="number" min="1" max="50" value="1"></label>
    <label>İsim<input id="mLabel" value="${esc(DEV_BY_ID[chosen].label)}"></label>`,
    () => {
      const cnt = Math.min(50, Math.max(1, Number($("mCount").value) || 1));
      snapshot();
      addDevice(room, chosen, cnt, $("mLabel").value.trim());
      changed();
    });
  $("modalBody").querySelectorAll(".devpick").forEach(b => b.onclick = () => {
    $("modalBody").querySelectorAll(".devpick").forEach(x => x.classList.remove("on"));
    b.classList.add("on");
    const prevDefault = DEV_BY_ID[chosen].label;
    chosen = b.dataset.cat;
    if ($("mLabel").value === prevDefault) $("mLabel").value = DEV_BY_ID[chosen].label;
  });
}

function showProductModal(panelId) {
  const panel = floor().panels.find(p => p.id === panelId);
  if (!panel) return;
  const groups = {};
  PANEL_PRODUCTS.forEach(p => (groups[p.category] = groups[p.category] || []).push(p));
  openModal(`${panel.name}: Ürün Ekle`, Object.entries(groups).map(([cat, list]) => `
    <div class="pgroup"><div class="pcat">${CATEGORY_LABEL[cat] || cat}</div>
    ${list.map(p => `<button type="button" class="prodbtn" data-pid="${p.id}">
        <span>${esc(p.name)}</span><small>${p.moduleWidth}M · ${p.channels} kanal${p.psuMa ? ` · ${p.psuMa} mA` : ""}</small>
      </button>`).join("")}
    </div>`).join(""), null);
  $("modalOk").style.display = "none";
  $("modalBody").querySelectorAll(".prodbtn").forEach(b => b.onclick = () => {
    const cat = PANEL_PRODUCTS.find(p => p.id === b.dataset.pid);
    snapshot();
    panel.products.push({ ...cat, pid: cat.id, id: uid() });
    closeModal();
    changed();
    toast(`${cat.name} eklendi.`);
  });
}

// --------------------------------
// SEÇİM, SOL PANEL, SAYAÇLAR
// --------------------------------

function fixSelection() {
  const f = floor();
  if (!f.rooms.some(r => r.id === selRoom)) selRoom = f.rooms.length ? f.rooms[f.rooms.length - 1].id : null;
  if (!f.panels.some(p => p.id === selPanel)) selPanel = f.panels.length ? f.panels[0].id : null;
}

function markSelection() {
  document.querySelectorAll(".rbox.selected,.pbox.selected").forEach(e => e.classList.remove("selected"));
  if (selRoom) document.querySelector(`.rbox[data-room="${selRoom}"]`)?.classList.add("selected");
  if (selPanel) document.querySelector(`.pbox[data-panel="${selPanel}"]`)?.classList.add("selected");
}

function renderTargets() {
  const f = floor();
  $("roomSelect").innerHTML = f.rooms.length
    ? f.rooms.map(r => `<option value="${r.id}" ${r.id === selRoom ? "selected" : ""}>${esc(r.name)}</option>`).join("")
    : `<option value="">Önce oda çizin</option>`;
  const panelOpts = f.panels.length
    ? f.panels.map(p => `<option value="${p.id}" ${p.id === selPanel ? "selected" : ""}>${esc(p.name)}</option>`).join("")
    : `<option value="">Yeni pano otomatik açılır</option>`;
  $("panelSelect").innerHTML = panelOpts;
  $("dinPanel").innerHTML = f.panels.length ? panelOpts : `<option value="">Pano yok</option>`;
}

$("roomSelect").onchange = e => { selRoom = e.target.value || null; markSelection(); };
$("panelSelect").onchange = e => { selPanel = e.target.value || null; markSelection(); if (view === "din") renderDin(); };
$("dinPanel").onchange = e => { selPanel = e.target.value || null; renderTargets(); renderDin(); };

function renderStats() {
  let rooms = 0, products = 0;
  for (const f of state.floors) {
    rooms += f.rooms.length;
    for (const p of f.panels) products += p.products.length;
    for (const r of f.rooms) for (const d of r.devices) products += d.count;
    for (const c of f.collectors) products += c.valves;
  }
  $("roomCount").textContent = rooms;
  $("productCount").textContent = products;
}

function buildSideLists() {
  $("deviceList").innerHTML = deviceGroupsHtml("ed-item", "data-side-dev", null);

  const groups = {};
  PANEL_PRODUCTS.forEach(p => (groups[p.category] = groups[p.category] || []).push(p));
  $("productList").innerHTML = Object.entries(groups).map(([cat, list]) => `
    <div class="ed-group">${CATEGORY_LABEL[cat] || cat}</div>
    ${list.map(p => `<button class="ed-item" data-side-prod="${p.id}">
        <span class="nm">${esc(p.name.replace(/^KNX /, ""))}</span>
        <small>${p.moduleWidth}M · ${p.psuMa ? p.psuMa + " mA" : p.channels + "K"}</small>
      </button>`).join("")}`).join("");
}

$("deviceList").addEventListener("click", e => {
  const b = e.target.closest("[data-side-dev]");
  if (!b) return;
  const room = floor().rooms.find(r => r.id === selRoom);
  if (!room) {
    setTool("room");
    return toast("Önce bir oda çizin: boş alanda sürükleyin.", "warn");
  }
  const catId = b.dataset.sideDev;
  const qty = Math.min(50, Math.max(1, Number($("devQty").value) || 1));
  const label = DEV_BY_ID[catId].label;
  snapshot();
  addDevice(room, catId, qty);
  changed();
  toast(`${room.name}: ${qty} adet ${label} eklendi.`);
});

$("productList").addEventListener("click", e => {
  const b = e.target.closest("[data-side-prod]");
  if (!b) return;
  const f = floor();
  snapshot();
  let panel = f.panels.find(p => p.id === selPanel);
  if (!panel) {
    // Pano yoksa otomatik aç: odaların sağına yerleştir
    const right = f.rooms.reduce((m, r) => Math.max(m, r.x + r.w), 0);
    panel = { id: uid(), name: `${f.name} Panosu`, x: Math.max(700, right + 80), y: 40, products: [] };
    f.panels.push(panel);
    selPanel = panel.id;
  }
  const cat = PANEL_PRODUCTS.find(p => p.id === b.dataset.sideProd);
  panel.products.push({ ...cat, pid: cat.id, id: uid() });
  changed();
  toast(`${panel.name}: ${cat.name} eklendi.`);
});

// --------------------------------
// GÖRÜNÜM: Plan / DIN, yakınlaştırma, sağ panel
// --------------------------------

function renderDin() {
  const f = floor();
  const panel = f.panels.find(p => p.id === selPanel);
  const letters = { light: "L", dim: "D", curtain: "M", valve: "V", onoff: "O", thermostat: "T", switch: "K", sensor: "S" };
  drawPanel($("panelCanvas"), {
    name: f.name,
    title: panel ? `${panel.name} (DIN ray)` : `${f.name}: pano yok`,
    panelProducts: panel ? panel.products : [],
    rooms: f.rooms.map(r => ({
      name: r.name,
      devices: r.devices.map(d => ({ ...d, letter: letters[d.type] || d.label }))
    }))
  });
}

document.querySelectorAll("[data-view]").forEach(b => b.onclick = () => {
  view = b.dataset.view;
  document.querySelectorAll("[data-view]").forEach(x => x.classList.toggle("active", x === b));
  $("planView").classList.toggle("hidden", view !== "plan");
  $("dinView").classList.toggle("hidden", view !== "din");
  if (view === "din") renderDin(); else drawWires();
});

function applyZoom(z) {
  zoom = Math.min(1.5, Math.max(0.5, Math.round(z * 10) / 10));
  stage.style.transform = `scale(${zoom})`;
  $("sizer").style.width = 2400 * zoom + "px";
  $("sizer").style.height = 1600 * zoom + "px";
  $("zoomRange").value = Math.round(zoom * 100);
  $("zoomReset").textContent = Math.round(zoom * 100) + "%";
  $("panelCanvas").style.width = 980 * zoom + "px";
}
$("zoomRange").oninput = e => applyZoom(Number(e.target.value) / 100);
$("zoomOut").onclick = () => applyZoom(zoom - 0.1);
$("zoomIn").onclick = () => applyZoom(zoom + 0.1);
$("zoomReset").onclick = () => applyZoom(1);

function setRight(show) {
  $("rightPanel").classList.toggle("hidden", !show);
  $("toggleRight").textContent = show ? "Adresler ⟩" : "⟨ Adresler";
  try { localStorage.setItem("knx.right", show ? "1" : "0"); } catch (e) { /* yok say */ }
}
$("toggleRight").onclick = () => setRight($("rightPanel").classList.contains("hidden"));

// --------------------------------
// KATLAR
// --------------------------------

$("floorTabs").addEventListener("click", e => {
  const b = e.target.closest("[data-floor]");
  if (!b) return;
  cur = Number(b.dataset.floor);
  pick = null;
  render();
});

$("addFloor").onclick = () => openModal("Kat Ekle",
  `<label>Kat adı<input id="mName" value="${state.floors.length}. Kat"></label>`,
  () => {
    snapshot();
    state.floors.push(newFloor($("mName").value.trim() || `${state.floors.length}. Kat`));
    cur = state.floors.length - 1;
    changed();
  });

// --------------------------------
// KLAVYE
// --------------------------------

document.addEventListener("keydown", e => {
  const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName);
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !typing) {
    e.preventDefault();
    undo();
  } else if (e.key === "Escape") {
    if (!$("modal").classList.contains("hidden")) return closeModal();
    pick = null;
    markPick();
    $("hint").textContent = HINTS[tool] || "";
  }
});
$("undoBtn").onclick = undo;

// --------------------------------
// SUNUCU: kural kontrolü, kaydet, PDF, knxproj
// --------------------------------

function payload() {
  return {
    project_name: $("projectName").value.trim() || "KNXdoit Projesi",
    ets_version: $("etsVersion").value,
    editor: state
  };
}

let checkTimer = null, checkSeq = 0;
function scheduleCheck() {
  clearTimeout(checkTimer);
  checkTimer = setTimeout(runCheck, 350);
}

async function runCheck() {
  const seq = ++checkSeq;
  try {
    const res = await fetch("/api/check", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload())
    });
    if (res.status === 401 || res.redirected) return toast("Oturum kapanmış; tekrar giriş yapın.", "error");
    const data = await res.json();
    if (seq !== checkSeq) return;
    renderHealth($("ruleWarnings"), data);
    $("gaCount").textContent = (data.group_addresses || []).length;

    let lastMain = null;
    $("gaList").innerHTML = (data.group_addresses || []).slice(0, 300).map(g => {
      const head = g.main !== lastMain ? `<div class="ga-group">${g.main} · ${esc(g.main_name)}</div>` : "";
      lastMain = g.main;
      return head + `<div class="ga-item"><span class="ga-addr">${g.address}</span>
        <div class="ga-name">${esc(g.room)} ${esc(g.device)} ${esc(g.function)}</div>
        <div class="ga-dpt">${g.dpt}</div></div>`;
    }).join("") || `<div class="empty-mini">Grup adresi yok</div>`;

    $("paList").innerHTML = (data.physical_addresses || []).map(p =>
      `<div class="ga-item"><span class="ga-addr pa">${p.address}</span>
        <div class="ga-name">${esc(p.name)}</div>
        <div class="ga-dpt">${esc(p.location)} · ${p.ma} mA</div></div>`
    ).join("") || `<div class="empty-mini">Bus cihazı yok</div>`;
  } catch (err) {
    $("ruleWarnings").textContent = "Kural kontrolü yapılamadı.";
  }
}

$("projectName").addEventListener("input", () => { dirty = true; $("dirty").textContent = "● Kaydedilmedi"; scheduleCheck(); });
$("etsVersion").addEventListener("change", () => { dirty = true; scheduleCheck(); });

$("saveBtn").onclick = async () => {
  const body = { ...payload(), project_id: projectId };
  const res = await fetch("/api/save", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.ok) return toast(data.error || "Proje kaydedilemedi.", "error");
  if (!projectId) {
    projectId = data.id;
    history.replaceState(null, "", `/project/${projectId}`);
  }
  dirty = false;
  $("dirty").textContent = "✓ Kaydedildi";
  toast("Proje kaydedildi.");
};

$("pdfBtn").onclick = () => downloadFile("/api/pdf", payload(),
  `${payload().project_name}_elektrikci.pdf`).catch(() => toast("PDF oluşturulamadı.", "error"));
$("knxBtn").onclick = () => downloadFile("/api/generate", payload(),
  `${payload().project_name}.knxproj`).catch(() => toast(".knxproj oluşturulamadı.", "error"));

window.addEventListener("beforeunload", e => {
  if (dirty) { e.preventDefault(); e.returnValue = ""; }
});

// --------------------------------
// BAŞLANGIÇ: kayıtlı projeyi yükle
// --------------------------------

function fromV18(saved) {
  // v18'de kaydedilmiş (çizimsiz) projeyi editöre taşı
  return {
    floors: (saved.floors || []).map(f => {
      const fl = newFloor(f.name || "Kat");
      (f.rooms || []).forEach((r, i) => fl.rooms.push({
        id: uid(), name: r.name || "Oda", x: 30 + (i % 3) * 250, y: 30 + Math.floor(i / 3) * 190,
        w: 220, h: 120,
        devices: (r.devices || []).map(d => ({ id: uid(), type: d.type, label: d.label || d.type, count: d.count || 1 }))
      }));
      if ((f.panelProducts || []).length) fl.panels.push({
        id: uid(), name: `${fl.name} Panosu`, x: 820, y: 30,
        products: f.panelProducts.map(p => ({ ...p, pid: p.id, id: uid() }))
      });
      return fl;
    }),
    links: [], bus: []
  };
}

(async function init() {
  try {
    await loadCatalog();
  } catch (e) {
    toast("Ürün kataloğu yüklenemedi; sayfayı yenileyin.", "error");
    return;
  }
  const saved = JSON.parse($("savedData").textContent);
  if (saved) {
    if (saved.project_name) $("projectName").value = saved.project_name;
    if (saved.ets_version) $("etsVersion").value = saved.ets_version;
    if (saved.editor && Array.isArray(saved.editor.floors) && saved.editor.floors.length) {
      state = { floors: saved.editor.floors, links: saved.editor.links || [], bus: saved.editor.bus || [] };
    } else if (Array.isArray(saved.floors) && saved.floors.length) {
      state = fromV18(saved);
      toast("Bu proje eski sürümde kaydedilmiş; kabloları çekip tekrar kaydedin.", "warn");
    }
    $("dirty").textContent = "✓ Kaydedildi";
  }
  prune();
  buildSideLists();
  applyZoom(1);
  let showRight = true;
  try { showRight = localStorage.getItem("knx.right") !== "0"; } catch (e) { /* yok say */ }
  setRight(showRight);
  setTool("select");
  render();
  runCheck();
  window.addEventListener("resize", drawWires);
})();
