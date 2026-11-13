"""
KNXdoit v19 - Elle çekilen kabloların kontrolü ve Kablo Çekim Listesi

Editörün kaydettiği yapı (state):
  floors[]: {id, name,
             rooms[]: {id, name, x, y, w, h, devices[]: {id, type, label, count}},
             panels[]: {id, name, x, y, products[]: {id, pid, name, category,
                                                     channels, busMa, psuMa}},
             collectors[]: {id, name, x, y, w, h, valves}}
  links[]: enerji kablosu  {id, floor, prod, ch, span,
                            to: {kind: "dev", dev, k} | {kind: "valve", col, v}}
  bus[]:   KNX bus kablosu {id, floor, a, b}
           düğüm: "panel:<panelId>" veya "dev:<deviceId>:<k>"

Kablo kesitleri ÖRNEKTİR; kesit ve sigortayı elektrikçi belirler.
"""

from knx_rules import _issue, _int
from catalog import (
    COMPAT, COMPAT_NOTE, CATEGORY_LABEL, DEVICE_BY_TYPE,
    LOAD_TYPES as ENERGY_TYPES, BUS_TYPES, CONTROL_TYPES,
    GATEWAY_CATEGORIES,
)

CABLE_ENERGY = "3×1.5"
CABLE_CURTAIN = "4×1.5"
CABLE_BUS = "2×2×0.8 J-Y(St)Y"

TYPE_LABEL = {t: d["label"] for t, d in DEVICE_BY_TYPE.items()}
TYPE_LABEL["switch"] = "Tuş Paneli"


# --------------------------------
# EDİTÖR -> KURAL MOTORU VERİSİ
# --------------------------------

def editor_to_rules_data(editor, project_name, ets_version):
    """Editör durumunu knx_rules.check_project'in beklediği yapıya çevirir.

    Kollektör vanaları, kollektör adında bir 'oda' olarak eklenir; böylece
    röle kanal hesabına ve grup adreslerine girer.
    """
    floors = []
    for f in editor.get("floors", []) or []:
        rooms = [
            {
                "name": r.get("name", "Oda"),
                "devices": [
                    {
                        "type": d.get("type"),
                        "label": d.get("label") or TYPE_LABEL.get(
                            d.get("type"), "Cihaz"
                        ),
                        "count": max(1, _int(d.get("count", 1), 1)),
                        "buttons": d.get("buttons"),
                        "inputs": d.get("inputs"),
                    }
                    for d in r.get("devices", []) or []
                ],
            }
            for r in f.get("rooms", []) or []
        ]
        for c in f.get("collectors", []) or []:
            valves = max(0, _int(c.get("valves"), 0))
            if valves:
                rooms.append({
                    "name": c.get("name", "Kollektör"),
                    "devices": [{
                        "type": "valve", "label": "Termoelektrik Vana",
                        "count": valves
                    }],
                })

        products = [
            p
            for panel in f.get("panels", []) or []
            for p in panel.get("products", []) or []
        ]

        floors.append({
            "name": f.get("name", "Kat"),
            "rooms": rooms,
            "collectors": [],
            "panelProducts": products,
        })

    return {
        "project_name": project_name,
        "ets_version": ets_version,
        "floors": floors,
    }


# --------------------------------
# DİZİNLER
# --------------------------------

def _index(editor):
    idx = {"floor": {}, "room_of_dev": {}, "dev": {}, "prod": {},
           "panel_of_prod": {}, "panel": {}, "col": {}}
    for f in editor.get("floors", []) or []:
        idx["floor"][f.get("id")] = f
        for r in f.get("rooms", []) or []:
            for d in r.get("devices", []) or []:
                idx["dev"][d.get("id")] = d
                idx["room_of_dev"][d.get("id")] = r
        for p in f.get("panels", []) or []:
            idx["panel"][p.get("id")] = p
            for pr in p.get("products", []) or []:
                idx["prod"][pr.get("id")] = pr
                idx["panel_of_prod"][pr.get("id")] = p
        for c in f.get("collectors", []) or []:
            idx["col"][c.get("id")] = c
    return idx


def _target_info(idx, to):
    """(tip, oda/kollektör adı, yük adı, anahtar) ya da None."""
    to = to or {}
    if to.get("kind") == "dev":
        d = idx["dev"].get(to.get("dev"))
        k = _int(to.get("k"), -1)
        if not d or k < 0 or k >= max(1, _int(d.get("count", 1), 1)):
            return None
        room = idx["room_of_dev"][d.get("id")]
        label = d.get("label") or TYPE_LABEL.get(d.get("type"), "Cihaz")
        return (
            d.get("type"), room.get("name", "Oda"),
            f"{label} {k + 1}", ("dev", d.get("id"), k)
        )
    if to.get("kind") == "valve":
        c = idx["col"].get(to.get("col"))
        v = _int(to.get("v"), -1)
        if not c or v < 0 or v >= _int(c.get("valves"), 0):
            return None
        return (
            "valve", c.get("name", "Kollektör"),
            f"Vana {v + 1}", ("valve", c.get("id"), v)
        )
    return None


def _node_info(idx, node):
    """Bus düğümü -> (görünen ad, geçerli mi)."""
    parts = str(node or "").split(":")
    if parts[0] == "panel" and len(parts) == 2:
        p = idx["panel"].get(parts[1])
        return (p.get("name", "Pano"), True) if p else (None, False)
    if parts[0] == "dev" and len(parts) == 3:
        d = idx["dev"].get(parts[1])
        k = _int(parts[2], -1)
        if not d or k < 0 or k >= max(1, _int(d.get("count", 1), 1)):
            return (None, False)
        room = idx["room_of_dev"][d.get("id")]
        label = d.get("label") or TYPE_LABEL.get(d.get("type"), "Cihaz")
        name = f"{room.get('name', 'Oda')} / {label} {k + 1}"
        return (name, d.get("type") in BUS_TYPES)
    return (None, False)


# --------------------------------
# KONTROL + KABLO LİSTESİ
# --------------------------------

def check_wiring(editor):
    issues = []
    cables = []
    idx = _index(editor)

    used_channels = {}
    used_targets = {}
    alt_used = {}   # tip -> {"warn", "loads"}: alternatif kanala bağlananlar

    # ---------- Enerji kabloları ----------
    for link in editor.get("links", []) or []:
        prod = idx["prod"].get(link.get("prod"))
        target = _target_info(idx, link.get("to"))
        if not prod or not target:
            continue   # silinmiş öğeye kalan bağlantı: yok say

        ttype, place, load, tkey = target
        ch = _int(link.get("ch"), -1)
        span = 2 if _int(link.get("span"), 1) == 2 else 1
        channels = _int(prod.get("channels"), 0)
        cat = prod.get("category")
        panel = idx["panel_of_prod"][prod.get("id")]

        if ch < 0 or ch + span > channels:
            issues.append(_issue(
                "error", "CHANNEL_RANGE",
                f"{prod.get('name')}: kanal {ch + 1} bu üründe yok."
            ))
            continue

        opts = COMPAT.get(ttype, [])
        match = next(
            (o for o in opts if o[0] == cat and o[1] == span), None
        )
        if ttype not in ENERGY_TYPES:
            issues.append(_issue(
                "error", "NOT_A_LOAD",
                f"{place} / {load}: KNX cihazıdır, aktüatör kanalına "
                f"bağlanmaz; KNX bus ile bağlanır."
            ))
        elif match is None:
            want = CATEGORY_LABEL.get(opts[0][0], opts[0][0]) if opts else "?"
            extra = COMPAT_NOTE.get(ttype, "")
            issues.append(_issue(
                "error", "WRONG_ACTUATOR",
                f"{place} / {load}: {prod.get('name')} ürününe "
                f"bağlanmış; {want} kanalına bağlanmalı. {extra}".strip()
            ))
        elif match[2]:
            alt_used.setdefault(ttype, {"warn": match[2], "loads": []})
            alt_used[ttype]["loads"].append(f"{place} / {load}")

        for c in range(ch, ch + span):
            key = (prod.get("id"), c)
            if key in used_channels:
                issues.append(_issue(
                    "error", "CHANNEL_DOUBLE",
                    f"{prod.get('name')} kanal {c + 1}: birden fazla "
                    f"yüke bağlı ({used_channels[key]} ve {load})."
                ))
            used_channels[key] = load

        if tkey in used_targets:
            issues.append(_issue(
                "error", "LOAD_DOUBLE",
                f"{place} / {load}: birden fazla kanala bağlı. "
                f"Bir yük tek çıkıştan beslenir."
            ))
        used_targets[tkey] = True

        two_way = ttype in ("curtain", "valve_motor")
        pair = "Yukarı/Aşağı" if ttype == "curtain" else "Aç/Kapa"
        if span == 2:
            out = f"K{ch + 1}+K{ch + 2} ({pair})"
        elif two_way:
            out = f"K{ch + 1} ({pair})"
        else:
            out = f"K{ch + 1}"
        is_control = cat in GATEWAY_CATEGORIES and ttype in CONTROL_TYPES
        dev_def = DEVICE_BY_TYPE.get(ttype, {})

        floor = idx["floor"].get(link.get("floor"), {})
        cables.append({
            "_sort": (
                floor.get("name", ""), panel.get("name", ""),
                prod.get("name", ""), ch
            ),
            "kind": "energy",
            "floor": floor.get("name", ""),
            "from": f"{panel.get('name', 'Pano')} / "
                    f"{prod.get('name')} / {out}",
            "to": place,
            "load": load,
            "cable": (
                "Üretici haberleşme kablosu" if is_control
                else dev_def.get("cable", CABLE_ENERGY)
            ),
            "line": "Kontrol (gateway)" if is_control else (
                "DALI hattı" if cat == "dali" else "Enerji (230V)"
            ),
            "note": (
                "Gateway → iç ünite haberleşme; enerji ayrıca panodan"
                if is_control else
                f"Ayrı faz damarları ({pair}) + nötr + toprak"
                if two_way else
                "Kanal çıkışı = anahtarlı faz; nötr ve toprak panodan"
            ),
        })

    # Alternatif kanal kullanımı: tip başına TEK uyarı
    for ttype, info in alt_used.items():
        shown = ", ".join(info["loads"][:4])
        more = f" ve {len(info['loads']) - 4} tane daha" if len(info["loads"]) > 4 else ""
        iss = _issue("warn", "ALT_ACTUATOR", f"{shown}{more}: {info['warn']}")
        iss["type"] = ttype
        issues.append(iss)

    # Klima / VRF iç ünite: enerji panodan DOĞRUDAN (sigorta) gelir
    for f in editor.get("floors", []) or []:
        for r in f.get("rooms", []) or []:
            for d in r.get("devices", []) or []:
                if d.get("type") not in CONTROL_TYPES:
                    continue
                dev_def = DEVICE_BY_TYPE[d.get("type")]
                label = d.get("label") or dev_def["label"]
                for k in range(max(1, _int(d.get("count", 1), 1))):
                    cables.append({
                        "_sort": (f.get("name", ""), "~", r.get("name", ""), label, k),
                        "kind": "energy",
                        "floor": f.get("name", ""),
                        "from": "Pano / Ayrı sigorta (doğrudan besleme)",
                        "to": r.get("name", "Oda"),
                        "load": f"{label} {k + 1}",
                        "cable": dev_def.get("cable", CABLE_ENERGY),
                        "line": "Enerji (doğrudan)",
                        "note": "Aktüatör kanalından geçmez; kontrol KNX gateway ile",
                    })

    # Bağlanmamış yükler
    missing = []
    for f in editor.get("floors", []) or []:
        for r in f.get("rooms", []) or []:
            for d in r.get("devices", []) or []:
                if d.get("type") not in ENERGY_TYPES:
                    continue
                label = d.get("label") or TYPE_LABEL.get(d.get("type"))
                for k in range(max(1, _int(d.get("count", 1), 1))):
                    if ("dev", d.get("id"), k) not in used_targets:
                        missing.append(f"{r.get('name')} / {label} {k + 1}")
        for c in f.get("collectors", []) or []:
            for v in range(_int(c.get("valves"), 0)):
                if ("valve", c.get("id"), v) not in used_targets:
                    missing.append(f"{c.get('name')} / Vana {v + 1}")
    if missing:
        shown = ", ".join(missing[:5])
        more = f" ve {len(missing) - 5} tane daha" if len(missing) > 5 else ""
        issues.append(_issue(
            "warn", "LOAD_UNCONNECTED",
            f"{len(missing)} yük henüz bir aktüatör / gateway kanalına bağlanmadı: "
            f"{shown}{more}."
        ))

    # ---------- KNX bus ----------
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    bus_rows = []
    for e in editor.get("bus", []) or []:
        a, b = e.get("a"), e.get("b")
        a_name, a_ok = _node_info(idx, a)
        b_name, b_ok = _node_info(idx, b)
        if a_name is None or b_name is None:
            continue   # silinmiş öğe
        if not a_ok or not b_ok:
            bad = a_name if not a_ok else b_name
            issues.append(_issue(
                "error", "BUS_INVALID",
                f"{bad}: KNX cihazı değil, bus kablosu bağlanmaz."
            ))
            continue
        ra, rb = find(a), find(b)
        if ra == rb:
            issues.append(_issue(
                "error", "BUS_RING",
                f"{a_name} ↔ {b_name}: bu kablo ring oluşturuyor. "
                f"KNX bus'ta ring yasaktır."
            ))
            continue
        parent[ra] = rb
        floor = idx["floor"].get(e.get("floor"), {})
        bus_rows.append({
            "kind": "bus",
            "floor": floor.get("name", ""),
            "from": a_name,
            "to": b_name,
            "load": "—",
            "cable": CABLE_BUS,
            "line": "KNX Bus (yeşil)",
            "note": "Kırmızı (+), siyah (−); 230V'tan ayrı güzergâh",
        })

    # Panoya ulaşamayan bus cihazları
    unreached = []
    for f in editor.get("floors", []) or []:
        panel_roots = {
            find(f"panel:{p.get('id')}") for p in f.get("panels", []) or []
        }
        for r in f.get("rooms", []) or []:
            for d in r.get("devices", []) or []:
                if d.get("type") not in BUS_TYPES:
                    continue
                label = d.get("label") or TYPE_LABEL.get(d.get("type"))
                for k in range(max(1, _int(d.get("count", 1), 1))):
                    node = f"dev:{d.get('id')}:{k}"
                    if find(node) not in panel_roots:
                        unreached.append(f"{r.get('name')} / {label} {k + 1}")
    if unreached:
        shown = ", ".join(unreached[:5])
        more = (
            f" ve {len(unreached) - 5} tane daha"
            if len(unreached) > 5 else ""
        )
        issues.append(_issue(
            "warn", "BUS_UNCONNECTED",
            f"{len(unreached)} KNX cihazı bus ile panoya bağlı değil: "
            f"{shown}{more}."
        ))

    cables.sort(key=lambda c: c.pop("_sort"))
    return issues, cables + bus_rows


# --------------------------------
# TEK GİRİŞ NOKTASI
# --------------------------------

def analyze(data):
    """Ekran, PDF ve .knxproj için tek hesap.

    data: {"project_name", "ets_version", "editor": {...}}  (v19 editör)
       ya da v18 yapısı {"floors": [...]} (geriye uyumluluk)
    Döner: (kural motoru verisi, sonuç)
    """
    from knx_rules import check_project

    editor = data.get("editor")
    if isinstance(editor, dict):
        rules_data = editor_to_rules_data(
            editor,
            data.get("project_name", "KNXdoit Projesi"),
            data.get("ets_version", "ETS6"),
        )
        res = check_project(rules_data)
        w_issues, cables = check_wiring(editor)
        # Kablo gerçekten çekildiyse proje düzeyindeki aynı uyarıyı tekrarlama
        wired_alt = {i.get("type") for i in w_issues if i["code"] == "ALT_ACTUATOR"}
        res["issues"] = [
            i for i in res["issues"]
            if not (i["code"] == "ALT_CHANNEL" and i.get("type") in wired_alt)
        ]
        res["issues"].extend(w_issues)
        res["cables"] = cables
    else:
        rules_data = data
        res = check_project(rules_data)
        res["cables"] = []

    errors = sum(1 for i in res["issues"] if i["level"] == "error")
    warns = sum(1 for i in res["issues"] if i["level"] == "warn")
    res["summary"] = {
        "errors": errors,
        "warnings": warns,
        "status": "error" if errors else ("warn" if warns else "ok"),
    }
    return rules_data, res
