// v18: Kuralların tamamı sunucuda (knx_rules.py) çalışır.
// Bu dosya sadece sonucu ekranda gösterir; böylece ekran, PDF ve
// .knxproj aynı hesaplardan beslenir.

const ICON = { error: "🔴", warn: "🟠", ok: "🟢" };

export function renderHealth(el, result) {
  const s = (result && result.summary) || {
    errors: 0, warnings: 0, status: "ok"
  };
  const issues = (result && result.issues) || [];

  const head = s.status === "ok"
    ? `${ICON.ok} Proje uygun`
    : `${ICON[s.status]} ${s.errors} hata · ${s.warnings} uyarı`;

  const list = issues.map(i => `
    <div class="issue ${i.level}">
      <span>${ICON[i.level] || ""}</span>
      <div>${escapeHtml(i.message)}</div>
    </div>
  `).join("");

  const lines = ((result && result.lines) || [])
    .filter(l => l.device_count || l.psu_count)
    .map(l => `
    <div class="line-row">
      <b>Hat ${l.line}</b> · ${escapeHtml(l.floor)}<br>
      ${l.device_count} bus cihazı · ${l.bus_ma} mA
      (+%30 = ${l.required_ma} mA) ·
      PS: ${l.psu_count ? l.psu_ma + " mA" : "yok"}
      ${l.recommended_psu ? `· öneri ${l.recommended_psu} mA` : "· hattı böl"}
    </div>
  `).join("");

  el.innerHTML = `
    <div class="health ${s.status}">${head}</div>
    ${lines}
    ${list}
  `;
}

export function escapeHtml(v) {
  return String(v ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;"
  }[c]));
}

export function connectionTargetFor(deviceType) {
  if (deviceType === "dim") return "dimmer";
  if (deviceType === "curtain") return "curtain_actuator";
  if (deviceType === "light" || deviceType === "valve") return "relay";
  return null;
}
