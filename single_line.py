"""
KNXdoit - Tek hat şeması (PDF)

Her pano için: ana besleme -> ana şalter -> kaçak akım -> bara;
baradan her besleme hattı: sigorta -> cihaz (aktüatör / PS / 24V PS / gateway)
-> kanal çıkışları -> yük (oda / yük / kablo). KNX bus cihazları yeşil işaretli.

Sigorta değerleri ÖNERİDİR; elektrikçi yük ve kesite göre belirler.
"""

from reportlab.graphics.shapes import Drawing, Line, Rect, String, Circle
from reportlab.lib import colors

# kategori -> (önerilen sigorta, 230V besleme alır mı)
BREAKER = {
    "power_supply": "C6",
    "psu24": "C6",
    "relay": "C16",
    "dimmer": "B10",
    "curtain_actuator": "C10",
    "heating": "C6",
    "fancoil": "C10",
    "rgbw": "C10",
    "dali": "C6",
    "ac_gateway": "C6",
    "vrf_gateway": "C6",
    "analog": "C6",
    "gateway_other": "C6",
    "visu": "C6",
    "meter": "C16",
}
# bara bağlantısı olmayan (bus'tan / 24V'tan beslenen) pano cihazları
BUS_ONLY = {"router", "line_coupler", "interface", "input", "logic"}

COL_W = 97
PER_ROW = 8
FONT = "DejaVu"
FONT_B = "DejaVu-Bold"
C_POWER = colors.HexColor("#1f2937")
C_BUS = colors.HexColor("#16a34a")
C_24 = colors.HexColor("#0e7490")
C_CTL = colors.HexColor("#0284c7")
C_MUTED = colors.HexColor("#6b7280")


def _fit(text, size, width):
    """Metni genişliğe sığacak şekilde kısalt."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    text = str(text or "")
    if stringWidth(text, FONT, size) <= width:
        return text
    while text and stringWidth(text + "…", FONT, size) > width:
        text = text[:-1]
    return text + "…"


def _wrap(text, size, width, max_lines=2):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words, lines, cur = str(text or "").split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if stringWidth(t, FONT_B, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _fit(lines[-1] + " …", size, width)
    return lines


def build_feeders(editor, res):
    """Pano başına besleme hatları listesi."""
    cables = res.get("cables", []) or []
    panels_out = []
    for f in editor.get("floors", []) or []:
        panels = f.get("panels", []) or []
        for pi, p in enumerate(panels):
            feeders, bus_devices = [], []
            for pr in p.get("products", []) or []:
                cat = pr.get("category")
                if cat in BUS_ONLY:
                    bus_devices.append(pr.get("name"))
                    continue
                outs = []
                if cat == "psu24":
                    outs = [
                        {"out": "24V", "load": c["load"], "to": c["to"], "cable": c["cable"], "color": C_24}
                        for c in cables
                        if c.get("line") == "24V DC besleme" and c["from"].endswith(pr.get("name", "")) and c.get("floor") == f.get("name")
                        and c["from"].startswith(p.get("name", ""))
                    ]
                elif cat == "power_supply":
                    outs = [{"out": "BUS", "load": "KNX bus hattı", "to": "", "cable": "J-Y(St)Y 2×2×0.8", "color": C_BUS}]
                else:
                    outs = [
                        {"out": c["out"], "load": c["load"], "to": c["to"], "cable": c["cable"],
                         "color": C_CTL if c.get("line") == "Kontrol (gateway)" else C_POWER}
                        for c in cables if c.get("prod_id") == pr.get("id")
                    ]
                ch = int(pr.get("channels") or 0)
                used = len({o["out"] for o in outs})
                feeders.append({
                    "breaker": BREAKER.get(cat, "C10"),
                    "name": pr.get("name", ""),
                    "bus": cat not in ("psu24",),
                    "outs": outs,
                    "spare": max(0, ch - used) if cat not in ("power_supply", "psu24") else 0,
                })
            if pi == 0:
                # odadaki panellerin dahili röleleri: yerel besleme
                drs = {}
                for c in cables:
                    if c.get("builtin") and c.get("floor") == f.get("name"):
                        src = c["from"].split(" / ")[-2] if " / " in c["from"] else c["from"]
                        drs.setdefault(src, []).append(
                            {"out": c["out"], "load": c["load"], "to": c["to"], "cable": c["cable"], "color": C_POWER})
                for src, outs in drs.items():
                    feeders.append({"breaker": "B10", "name": src.replace(" dahili röle", "") + " (oda) dahili röle, maks. 1 A",
                                    "bus": True, "outs": outs, "spare": 0, "remote": True})
                # doğrudan beslenen klima / VRF
                for c in cables:
                    if c.get("direct") and c.get("floor") == f.get("name"):
                        feeders.append({"breaker": "C16", "name": f"{c['to']} / {c['load']}",
                                        "bus": False, "outs": [{"out": "L", "load": c["load"], "to": c["to"],
                                                                "cable": c["cable"], "color": C_POWER}],
                                        "spare": 0, "direct": True})
            if feeders or bus_devices:
                panels_out.append({"floor": f.get("name", ""), "panel": p.get("name", "Pano"),
                                   "feeders": feeders, "bus_devices": bus_devices})
    return panels_out


def _mcb(d, x, y, label):
    """Sigorta sembolü: y üst uç. 26pt yükseklik."""
    d.add(Line(x, y, x, y - 6, strokeColor=C_POWER, strokeWidth=1))
    d.add(Line(x, y - 6, x + 7, y - 18, strokeColor=C_POWER, strokeWidth=1.2))   # anahtar
    d.add(Circle(x, y - 6, 1.4, fillColor=C_POWER, strokeColor=C_POWER))
    d.add(Rect(x - 3, y - 15, 6, 4, fillColor=colors.white, strokeColor=C_POWER, strokeWidth=0.8))
    d.add(Line(x, y - 20, x, y - 26, strokeColor=C_POWER, strokeWidth=1))
    d.add(Circle(x, y - 20, 1.4, fillColor=C_POWER, strokeColor=C_POWER))
    d.add(String(x + 9, y - 13, label, fontName=FONT_B, fontSize=7, fillColor=C_POWER))


def draw_row(feeders, first=True, last=True, head=""):
    """Bir sıra (en fazla PER_ROW besleme) için Drawing."""
    W = COL_W * PER_ROW + 10
    out_h = max([len(f["outs"]) + (1 if f["spare"] else 0) for f in feeders] + [1]) * 17
    top_pad = 46 if first else 20
    H = top_pad + 26 + 10 + 38 + 8 + out_h + 6
    d = Drawing(W, H)
    bar_y = H - top_pad
    x0 = 10
    # bara
    xs = [x0 + COL_W * i + COL_W / 2 for i in range(len(feeders))]
    bx1 = (xs[-1] if xs else x0) + 20
    if first:
        d.add(Rect(x0 - 8, H - 30, 300, 22, fillColor=colors.HexColor("#f3f4f6"), strokeColor=C_POWER, strokeWidth=0.6))
        d.add(String(x0 - 2, H - 22, head or "Ana besleme 230V L/N/PE → Ana şalter → Kaçak akım rölesi 30 mA",
                     fontName=FONT_B, fontSize=7.5, fillColor=C_POWER))
        d.add(Line(x0, H - 30, x0, bar_y, strokeColor=C_POWER, strokeWidth=1.5))
    else:
        d.add(String(x0, bar_y + 4, "(bara devam)", fontName=FONT, fontSize=6.5, fillColor=C_MUTED))
    d.add(Line(x0, bar_y, bx1, bar_y, strokeColor=C_POWER, strokeWidth=3))
    d.add(String(bx1 + 4, bar_y - 3, "L/N", fontName=FONT_B, fontSize=7, fillColor=C_POWER))

    for f, x in zip(feeders, xs):
        _mcb(d, x, bar_y, f["breaker"])
        by = bar_y - 26 - 10
        d.add(Line(x, bar_y - 26, x, by, strokeColor=C_POWER, strokeWidth=1))
        bw, bh = COL_W - 8, 38
        bx = x - bw / 2
        fill = colors.HexColor("#fff7ed") if f.get("direct") else (
            colors.HexColor("#ecfeff") if f.get("remote") else colors.HexColor("#eff6ff"))
        d.add(Rect(bx, by - bh, bw, bh, rx=3, ry=3, fillColor=fill, strokeColor=C_POWER, strokeWidth=0.8))
        if f["bus"]:
            d.add(Rect(bx, by - bh, bw, 8, fillColor=C_BUS, strokeColor=C_BUS, strokeWidth=0))
            d.add(String(bx + bw / 2, by - bh + 2, "KNX bus", fontName=FONT_B, fontSize=5.5,
                         fillColor=colors.white, textAnchor="middle"))
        for li, ln in enumerate(_wrap(f["name"], 6.8, bw - 8, 3 if not f["bus"] else 2)):
            d.add(String(bx + 4, by - 10 - li * 8.5, ln, fontName=FONT_B, fontSize=6.8, fillColor=C_POWER))
        # çıkışlar
        oy = by - bh - 6
        rows = list(f["outs"])
        if not rows and not f["spare"]:
            d.add(String(x - bw / 2 + 2, oy - 8, "(çıkış bağlanmadı)", fontName=FONT, fontSize=6, fillColor=C_MUTED))
        for o in rows:
            d.add(Line(bx + 6, oy, bx + 6, oy - 12, strokeColor=o["color"], strokeWidth=1))
            d.add(Line(bx + 6, oy - 12, bx + 12, oy - 12, strokeColor=o["color"], strokeWidth=1))
            d.add(String(bx + 14, oy - 7, _fit(f"{o['out']} → {o['load']}", 6.2, bw - 12),
                         fontName=FONT_B, fontSize=6.2, fillColor=o["color"]))
            sub = " · ".join(x for x in [o.get("to"), o.get("cable")] if x)
            d.add(String(bx + 14, oy - 14, _fit(sub, 5.6, bw - 12),
                         fontName=FONT, fontSize=5.6, fillColor=C_MUTED))
            oy -= 17
        if f["spare"]:
            d.add(String(bx + 14, oy - 7, f"+{f['spare']} boş kanal (yedek)", fontName=FONT, fontSize=6, fillColor=C_MUTED))
    return d


def single_line_story(editor, res, h2, normal):
    from reportlab.platypus import Paragraph, Spacer, PageBreak, KeepTogether
    from xml.sax.saxutils import escape
    story = []
    for pnl in build_feeders(editor, res):
        feeders = pnl["feeders"]
        story += [PageBreak(), Paragraph(
            f"Tek Hat Şeması — {escape(pnl['floor'])} / {escape(pnl['panel'])}", h2)]
        story.append(Paragraph(
            '<font color="#1f2937"><b>━</b></font> 230V enerji &nbsp; '
            '<font color="#16a34a"><b>▬</b></font> KNX bus cihazı &nbsp; '
            '<font color="#0e7490"><b>━</b></font> 24V DC &nbsp; '
            '<font color="#0284c7"><b>━</b></font> gateway kontrol &nbsp; '
            '<font color="#c2410c">■</font> doğrudan besleme (klima/VRF) &nbsp; '
            '<font color="#0e7490">■</font> oda paneli dahili rölesi', normal))
        story.append(Spacer(1, 4))
        if not feeders:
            story.append(Paragraph("Bu panoda 230V besleme alan cihaz yok.", normal))
        for i in range(0, len(feeders), PER_ROW):
            story.append(draw_row(feeders[i:i + PER_ROW], first=(i == 0),
                                  last=(i + PER_ROW >= len(feeders))))
            story.append(Spacer(1, 6))
        bus_txt = " → ".join(
            [f["name"] for f in feeders if f["bus"] and not f.get("remote")] + pnl["bus_devices"])
        if bus_txt:
            story.append(Paragraph(f'<font color="#16a34a"><b>KNX bus (pano içi):</b></font> {escape(bus_txt)}', normal))
        story.append(Paragraph(
            "Sigorta değerleri ve kesitler <b>öneridir</b>; elektrikçi bağlanan yüke, kablo boyuna ve "
            "yönetmeliğe göre belirler. Aktüatör kanal sayısı kadar ayrı sigorta / grup sigortası "
            "kullanılabilir. Oda panellerinin dahili röleleri bulunduğu odadaki linyeden beslenir.", normal))
    return story
