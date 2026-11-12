import {
  ROOM_DEVICES,
  PANEL_PRODUCTS
} from "./devices.js";

import {
  createInitialState,
  currentFloor
} from "./panel.js";

import { drawPanel } from "./canvas.js";
import { renderHealth, escapeHtml } from "./rules.js";
import { downloadFile } from "./pdf.js";

let state = createInitialState();

const $ = id => document.getElementById(id);
const modal = $("modal");

let modalOkHandler = null;

function openModal(title, bodyHtml, onOk) {
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = bodyHtml;
  modalOkHandler = onOk;
  modal.classList.remove("hidden");
}

$("modalCancel").onclick = () => {
  modal.classList.add("hidden");
};

$("modalOk").onclick = () => {
  if (modalOkHandler) modalOkHandler();
  modal.classList.add("hidden");
};

function setStatus(txt) {
  $("status").textContent = txt;
}

function render() {
  renderFloors();
  renderRoomSelect();
  renderMenus();
  renderRooms();
  renderCollectors();
  renderStats();
  renderCheck();

  $("floorTitle").textContent =
    currentFloor(state).name + " Odaları";

  $("panelTitle").textContent =
    currentFloor(state).name + " KNX Panosu";

  drawPanel(
    $("panelCanvas"),
    currentFloor(state)
  );

  applyZoom();
}

function renderFloors() {
  $("floorTabs").innerHTML = state.floors.map(
    (f, i) => `
      <button
        class="tab ${i === state.currentFloor ? "active" : ""}"
        data-i="${i}">
        ${escapeHtml(f.name)}
      </button>
    `
  ).join("");

  document.querySelectorAll(".tab").forEach(b => {
    b.onclick = () => {
      state.currentFloor = Number(b.dataset.i);
      render();
    };
  });
}

function renderRoomSelect() {
  const f = currentFloor(state);

  $("roomSelect").innerHTML = f.rooms.map(
    (r, i) => `
      <option value="${i}">${escapeHtml(r.name)}</option>
    `
  ).join("");
}

function renderMenus() {
  $("roomDevices").innerHTML = ROOM_DEVICES.map(
    d => `
      <button class="device-btn" data-device="${d.id}">
        <span>${d.label}</span>
        <small>${d.energy ? "Enerji" : "KNX Bus"}</small>
      </button>
    `
  ).join("");

  document.querySelectorAll("[data-device]").forEach(
    btn => {
      btn.onclick = () => addDevice(btn.dataset.device);
    }
  );

  $("panelProducts").innerHTML = PANEL_PRODUCTS.map(
    p => `
      <button class="device-btn" data-product="${p.id}">
        <span>${p.name}</span>
        <small>${p.moduleWidth}M · ${p.channels}K</small>
      </button>
    `
  ).join("");

  document.querySelectorAll("[data-product]").forEach(
    btn => addProductClick(btn)
  );
}

function addProductClick(btn) {
  btn.onclick = () => {
    const p = PANEL_PRODUCTS.find(
      x => x.id === btn.dataset.product
    );

    currentFloor(state).panelProducts.push({
      ...p,
      instanceId: Date.now() + Math.random()
    });

    setStatus(`${p.name} panoya eklendi.`);
    render();
  };
}

function addDevice(id) {
  const f = currentFloor(state);

  if (!f.rooms.length) {
    setStatus("Önce oda eklemelisin.");
    return;
  }

  const room = f.rooms[
    Number($("roomSelect").value || 0)
  ];

  const def = ROOM_DEVICES.find(
    d => d.id === id
  );

  openModal(
    def.label + " Ekle",
    `
      <label>
        Adet
        <input
          id="deviceCount"
          type="number"
          min="1"
          max="99"
          value="1">
      </label>

      <label>
        İsim / Not
        <input id="deviceNote" value="${def.label}">
      </label>
    `,
    () => {
      const count = Math.max(
        1,
        Number($("deviceCount").value || 1)
      );

      room.devices.push({
        ...def,
        count,
        label: $("deviceNote").value || def.label
      });

      setStatus(
        `${room.name} odasına ${count} adet ${def.label} eklendi.`
      );

      render();
    }
  );
}

$("addFloor").onclick = () => {
  openModal(
    "Kat Ekle",
    `
      <label>
        Kat Adı
        <input
          id="floorName"
          value="${state.floors.length}. Kat">
      </label>
    `,
    () => {
      const name = $("floorName").value ||
        `${state.floors.length}. Kat`;

      state.floors.push({
        name,
        rooms: [],
        collectors: [],
        panelProducts: []
      });

      state.currentFloor = state.floors.length - 1;
      render();
    }
  );
};

$("addRoom").onclick = () => {
  openModal(
    "Oda Ekle",
    `
      <label>
        Oda Adı
        <input id="roomName" value="Salon">
      </label>
    `,
    () => {
      currentFloor(state).rooms.push({
        name: $("roomName").value || "Oda",
        devices: []
      });

      render();
    }
  );
};

$("addCollector").onclick = () => {
  openModal(
    "Kollektör Ekle",
    `
      <label>
        Kollektör Adı
        <input
          id="collectorName"
          value="${escapeHtml(currentFloor(state).name)} Kollektörü">
      </label>

      <label>
        Vana Sayısı
        <input
          id="valveCount"
          type="number"
          min="1"
          max="32"
          value="6">
      </label>

      <label>
        Bağlı Oda
        <select id="collectorRoom">
          ${currentFloor(state).rooms.map(
            (r, i) => `
              <option value="${i}">${escapeHtml(r.name)}</option>
            `
          ).join("")}
        </select>
      </label>
    `,
    () => {
      const f = currentFloor(state);

      const count = Math.max(
        1,
        Number($("valveCount").value || 1)
      );

      const room = f.rooms[
        Number($("collectorRoom").value || 0)
      ];

      f.collectors.push({
        name: $("collectorName").value || "Kollektör",
        valves: count,
        room: room ? room.name : ""
      });

      if (room) {
        room.devices.push({
          id: "valve",
          label: "Vana",
          type: "valve",
          energy: true,
          icon: "V",
          count
        });
      }

      setStatus(`${count} vanalı kollektör eklendi.`);
      render();
    }
  );
};

function renderRooms() {
  const f = currentFloor(state);

  $("roomsCanvas").innerHTML = f.rooms.map(
    r => `
      <div class="room-card">
        <h5 title="${escapeHtml(r.name)}">${escapeHtml(r.name)}</h5>
        <div class="chips">
          ${r.devices.flatMap(
            d => Array.from(
              { length: d.count },
              () => `
                <span
                  class="chip c-${d.type}"
                  title="${escapeHtml(d.label)}">
                  ${d.icon || d.label[0]}
                </span>
              `
            )
          ).join("")}
        </div>
      </div>
    `
  ).join("") || `
    <div class="empty-mini">Oda ekleyin</div>
  `;
}

function renderCollectors() {
  const f = currentFloor(state);

  $("collectorsCanvas").innerHTML = f.collectors.map(
    c => `
      <div class="collector-card">
        <h5 title="${escapeHtml(c.name)}">${escapeHtml(c.name)}</h5>
        <div>${c.valves} vana</div>
        <small>${escapeHtml(c.room || "")}</small>
      </div>
    `
  ).join("") || `
    <div class="empty-mini">Kollektör ekleyin</div>
  `;
}

function renderStats() {
  const rooms = state.floors.reduce(
    (a, f) => a + f.rooms.length,
    0
  );

  const products = state.floors.reduce(
    (a, f) =>
      a +
      f.panelProducts.length +
      f.rooms.reduce(
        (b, r) =>
          b + r.devices.reduce(
            (c, d) => c + d.count,
            0
          ),
        0
      ),
    0
  );

  $("roomCount").textContent = rooms;
  $("productCount").textContent = products;
}

function collectData() {
  return {
    project_name:
      $("projectName").value || "KNXdoit Projesi",
    ets_version: $("etsVersion").value,
    floors: state.floors
  };
}

let checkSeq = 0;

async function renderCheck() {
  const seq = ++checkSeq;
  try {
    const res = await fetch("/api/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(collectData())
    });

    const data = await res.json();
    if (seq !== checkSeq) return;   // eski cevabi yok say

    const gas = data.group_addresses || [];
    const pas = data.physical_addresses || [];

    $("gaCount").textContent = gas.length;

    renderHealth($("ruleWarnings"), data);

    let lastMain = null;
    const gaHtml = gas.slice(0, 200).map(g => {
      const head = g.main !== lastMain
        ? `<div class="ga-group">${g.main} · ${escapeHtml(g.main_name)}</div>`
        : "";
      lastMain = g.main;
      return head + `
        <div class="ga-item">
          <span class="ga-addr">${g.address}</span>
          <div class="ga-name">
            ${escapeHtml(g.room)} ${escapeHtml(g.device)} ${escapeHtml(g.function)}
          </div>
          <div class="ga-dpt">${g.dpt}</div>
        </div>
      `;
    }).join("");

    const paHtml = pas.map(p => `
      <div class="ga-item">
        <span class="ga-addr pa">${p.address}</span>
        <div class="ga-name">${escapeHtml(p.name)}</div>
        <div class="ga-dpt">${escapeHtml(p.location)} · ${p.ma} mA</div>
      </div>
    `).join("");

    $("paList").innerHTML = paHtml ||
      `<div class="empty-mini">Bus cihazı yok</div>`;
    $("gaList").innerHTML = gaHtml ||
      `<div class="empty-mini">Grup adresi yok</div>`;
  } catch (e) {
    setStatus("Kural kontrolü yapılamadı.");
  }
}

function applyZoom() {
  const z = state.zoom / 100;

  $("zoomContent").style.transform =
    `scale(${z})`;

  $("zoomContent").style.height =
    `${820 * z}px`;

  $("zoomReset").textContent =
    `${state.zoom}%`;
}

$("zoomRange").oninput = e => {
  state.zoom = Number(e.target.value);
  applyZoom();
};

$("zoomOut").onclick = () => {
  state.zoom = Math.max(50, state.zoom - 10);
  $("zoomRange").value = state.zoom;
  applyZoom();
};

$("zoomIn").onclick = () => {
  state.zoom = Math.min(150, state.zoom + 10);
  $("zoomRange").value = state.zoom;
  applyZoom();
};

$("zoomReset").onclick = () => {
  state.zoom = 100;
  $("zoomRange").value = 100;
  applyZoom();
};

$("clearBtn").onclick = () => {
  currentFloor(state).panelProducts = [];
  setStatus("Pano temizlendi.");
  render();
};

$("saveBtn").onclick = async () => {
  const res = await fetch("/api/save", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(collectData())
  });

  if (res.ok) {
    setStatus("Proje kaydedildi.");
  } else {
    setStatus("Proje kaydedilemedi.");
  }
};

$("pdfBtn").onclick = () => {
  downloadFile(
    "/api/pdf",
    collectData(),
    `${$("projectName").value || "KNXdoit"}_elektrikci.pdf`
  );
};

$("knxBtn").onclick = () => {
  downloadFile(
    "/api/generate",
    collectData(),
    `${$("projectName").value || "KNXdoit"}.knxproj`
  );
};

$("projectName").oninput = renderCheck;
$("etsVersion").onchange = renderCheck;

render();
