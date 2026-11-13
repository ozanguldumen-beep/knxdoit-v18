"""
KNXdoit - KNX kural motoru (katalog: catalog.py)

Tek kaynak: hem ekrandaki saglik paneli, hem PDF, hem .knxproj
ayni hesaplari bu dosyadan alir.

Varsayimlar (RULES.md ile ayni):
- 1 Alan (Area 1). Her kat = 1 hat (Line). Zemin Kat -> 1.1.x, 1. Kat -> 1.2.x
- Grup adresi: Ana grup = fonksiyon, Orta grup = kat, Alt grup = sirali
- mA degerleri varsayilandir; gercek degerler urun datasheet'inden alinmalidir
"""

# --------------------------------
# SABITLER
# --------------------------------

MAX_DEVICES_PER_LINE = 64
WARN_DEVICES_PER_LINE = 50          # yedek kapasite icin uyari esigi
MAX_LINES_PER_AREA = 15
PSU_RESERVE = 1.30                  # %30 rezerv
PSU_SIZES = [160, 320, 640, 1280]   # standart KNX PS akimlari (mA)

GA_MAIN_MAX = 31
GA_MIDDLE_MAX = 7
GA_SUB_MAX = 255

from catalog import (  # noqa: E402  (tek kaynak)
    DEFAULT_BUS_MA, CATEGORY_LABEL, COMPAT, COMPAT_NOTE, GA_GROUPS,
    DEVICE_BY_TYPE, LOAD_TYPES, BUS_TYPES, OUTPUT_CATEGORIES,
    device_objects, device_bus_ma,
)

# Geriye uyumluluk adları
ENERGY_TYPES = LOAD_TYPES
LOAD_OUTPUT_CATEGORIES = OUTPUT_CATEGORIES
ACTUATOR_FOR = {t: opts[0][0] for t, opts in COMPAT.items()}


# --------------------------------
# YARDIMCILAR
# --------------------------------

def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def ga_to_int(main, middle, sub):
    return (main << 11) | (middle << 8) | sub


def recommend_psu(required_ma):
    for size in PSU_SIZES:
        if size >= required_ma:
            return size
    return None   # 1280 mA da yetmiyor -> hatti bolmek gerekir


def _floors(data):
    return data.get("floors", []) or []


def _room_devices(floor):
    for room in floor.get("rooms", []) or []:
        for dev in room.get("devices", []) or []:
            yield room, dev


# --------------------------------
# GRUP ADRESLERI
# --------------------------------

def build_gas(data):
    """Fonksiyon bazli grup adresleri. Sinir asimlarini da dondurur."""
    gas = []
    issues = []
    counters = {}          # (main, middle) -> son alt grup
    overflowed = set()

    floors = _floors(data)

    for fi, floor in enumerate(floors):
        middle = fi
        floor_name = floor.get("name", "Kat")

        if middle > GA_MIDDLE_MAX:
            issues.append(_issue(
                "error", "GA_MIDDLE",
                f"{floor_name}: Grup adresinde orta grup en fazla "
                f"{GA_MIDDLE_MAX} olabilir. 8'den fazla kat bu yapıda "
                f"adreslenemez; bu kat için grup adresi üretilmedi."
            ))
            continue

        for room, dev in _room_devices(floor):
            dtype = dev.get("type")
            base = DEVICE_BY_TYPE.get(dtype, DEVICE_BY_TYPE["light"])
            main = base["ga"]
            main_name = GA_GROUPS[main]
            objects = device_objects(dev)
            count = max(1, _int(dev.get("count", 1), 1))

            for n in range(1, count + 1):
                label = dev.get("label", "Cihaz")
                if count > 1:
                    label = f"{label} {n}"

                for code, dpt, func in objects:
                    key = (main, middle)
                    sub = counters.get(key, 0) + 1

                    if sub > GA_SUB_MAX:
                        if key not in overflowed:
                            overflowed.add(key)
                            issues.append(_issue(
                                "error", "GA_SUB",
                                f"{floor_name} / {main_name}: alt grup "
                                f"{GA_SUB_MAX} sınırı aşıldı. Fazla "
                                f"nesneler adreslenmedi."
                            ))
                        continue

                    counters[key] = sub
                    gas.append({
                        "address": f"{main}/{middle}/{sub}",
                        "int": ga_to_int(main, middle, sub),
                        "main": main,
                        "main_name": main_name,
                        "middle": middle,
                        "sub": sub,
                        "floor": floor_name,
                        "room": room.get("name", "Oda"),
                        "device": label,
                        "function": func,
                        "dpt": dpt,
                    })

    gas.sort(key=lambda g: g["int"])
    return gas, issues


# --------------------------------
# FIZIKSEL ADRESLER (kat = hat)
# --------------------------------

def bus_devices_of_floor(floor):
    """Bir hattaki bus cihazlari (PS haric, lambalar haric)."""
    items = []

    for p in floor.get("panelProducts", []) or []:
        cat = p.get("category")
        if cat == "power_supply":
            continue
        ma = _int(p.get("busMa"), DEFAULT_BUS_MA.get(cat, 10))
        items.append({
            "name": p.get("name", "Ürün"),
            "category": cat,
            "location": "Pano",
            "ma": ma,
        })

    for room, dev in _room_devices(floor):
        dtype = dev.get("type")
        if dtype not in BUS_TYPES:
            continue   # 230V yükler ve gateway ile kontrol edilenler bus cihazı değil
        count = max(1, _int(dev.get("count", 1), 1))
        for n in range(1, count + 1):
            label = dev.get("label", "Cihaz")
            items.append({
                "name": f"{label} {n}" if count > 1 else label,
                "category": dtype,
                "location": room.get("name", "Oda"),
                "ma": device_bus_ma(dev),
            })

    return items


def build_physical(data):
    """Her kat bir hat: 1.<hat>.<cihaz>. Coupler/router x.y.0 alir."""
    rows = []

    for fi, floor in enumerate(_floors(data)):
        line = fi + 1
        if line > MAX_LINES_PER_AREA:
            continue

        dev_no = 1
        coupler_used = False

        for item in bus_devices_of_floor(floor):
            is_coupler = item["category"] in ("router", "line_coupler")

            if is_coupler and not coupler_used:
                addr = f"1.{line}.0"
                coupler_used = True
            else:
                addr = f"1.{line}.{dev_no}"
                dev_no += 1

            rows.append({
                "address": addr,
                "line": line,
                "floor": floor.get("name", "Kat"),
                **item,
            })

    return rows


# --------------------------------
# KURAL KONTROLU
# --------------------------------

def _issue(level, code, message):
    return {"level": level, "code": code, "message": message}


def _channels(floor, category):
    return sum(
        max(0, _int(p.get("channels"), 0))
        for p in floor.get("panelProducts", []) or []
        if p.get("category") == category
    )


def _needed(floor, dtype):
    return sum(
        max(1, _int(d.get("count", 1), 1))
        for _, d in _room_devices(floor)
        if d.get("type") == dtype
    )


def check_floor(floor, line_no):
    issues = []
    name = floor.get("name", "Kat")
    products = floor.get("panelProducts", []) or []
    bus = bus_devices_of_floor(floor)

    # --- Power Supply ---
    psus = [p for p in products if p.get("category") == "power_supply"]
    psu_ma = sum(_int(p.get("psuMa"), 640) for p in psus)
    bus_ma = sum(b["ma"] for b in bus)
    required = round(bus_ma * PSU_RESERVE)
    recommended = recommend_psu(required)

    line = {
        "line": f"1.{line_no}",
        "floor": name,
        "device_count": len(bus),
        "bus_ma": bus_ma,
        "required_ma": required,
        "psu_ma": psu_ma,
        "psu_count": len(psus),
        "recommended_psu": recommended,
    }

    if bus and not psus:
        issues.append(_issue(
            "error", "PSU_MISSING",
            f"{name} (hat 1.{line_no}): KNX Power Supply yok. "
            f"Önerilen: {recommended or 'hattı bölün'} mA."
        ))
    elif len(psus) > 1:
        issues.append(_issue(
            "warn", "PSU_MULTI",
            f"{name}: Hatta {len(psus)} adet PS var. Aynı hatta iki PS "
            f"paralel bağlanmaz; gerekiyorsa aralarında en az 200 m "
            f"kablo olmalı veya hat bölünmeli."
        ))

    if psus:
        if bus_ma > psu_ma:
            issues.append(_issue(
                "error", "PSU_OVERLOAD",
                f"{name}: Toplam bus akımı {bus_ma} mA, PS kapasitesi "
                f"{psu_ma} mA. PS yetersiz."
            ))
        elif required > psu_ma:
            issues.append(_issue(
                "warn", "PSU_RESERVE",
                f"{name}: Bus akımı {bus_ma} mA, %30 rezervle "
                f"{required} mA gerekiyor; PS {psu_ma} mA. "
                f"Önerilen: {recommended or 'hattı bölün'} mA."
            ))

    if recommended is None and bus:
        issues.append(_issue(
            "error", "PSU_NONE_FITS",
            f"{name}: {required} mA ihtiyaç en büyük PS'yi (1280 mA) "
            f"aşıyor. Hattı ikiye bölün (line coupler)."
        ))

    # --- Cihaz sayisi ---
    if len(bus) > MAX_DEVICES_PER_LINE:
        issues.append(_issue(
            "error", "LINE_DEVICES",
            f"{name}: Hatta {len(bus)} bus cihazı var, sınır "
            f"{MAX_DEVICES_PER_LINE}. Yeni hat + line coupler gerekli."
        ))
    elif len(bus) > WARN_DEVICES_PER_LINE:
        issues.append(_issue(
            "warn", "LINE_DEVICES_RESERVE",
            f"{name}: Hatta {len(bus)} bus cihazı var. 64 sınırına "
            f"yakın, genişleme payı az."
        ))

    # --- Aktüatör / gateway kanalları (genel kural) ---
    # Önce her yük kendi BİRİNCİL kanal tipine yerleştirilir; sığmayanlar
    # izinli ALTERNATİFE (uyarıyla) taşınır; hiçbir yere sığmayan hatadır.
    have = {}
    for p in products:
        cat = p.get("category")
        if cat in OUTPUT_CATEGORIES:
            have[cat] = have.get(cat, 0) + max(0, _int(p.get("channels"), 0))
    free = dict(have)

    demand = {}   # yük tipi -> adet
    for _, d in _room_devices(floor):
        t = d.get("type")
        if t in COMPAT:
            demand[t] = demand.get(t, 0) + max(1, _int(d.get("count", 1), 1))

    need = {}     # kategori -> birincil ihtiyaç (kanal)
    leftover = {}
    for t, n in demand.items():
        cat, span, _ = COMPAT[t][0]
        need[cat] = need.get(cat, 0) + n * span
        fit = min(n, free.get(cat, 0) // span)
        free[cat] = free.get(cat, 0) - fit * span
        if n - fit:
            leftover[t] = n - fit

    for t, n in leftover.items():
        label = DEVICE_BY_TYPE[t]["label"]
        for cat, span, warn in COMPAT[t][1:]:
            fit = min(n, free.get(cat, 0) // span)
            if fit:
                free[cat] -= fit * span
                n -= fit
                iss = _issue(
                    "warn", "ALT_CHANNEL",
                    f"{name}: {fit} adet {label} için "
                    f"{CATEGORY_LABEL[COMPAT[t][0][0]]} kanalı yok; "
                    f"{CATEGORY_LABEL[cat]} kullanılabilir. {warn}"
                )
                iss["type"] = t
                issues.append(iss)
            if not n:
                break
        if n:
            primary = COMPAT[t][0][0]
            note = COMPAT_NOTE.get(t, "")
            issues.append(_issue(
                "error", "CHANNELS_MISSING",
                f"{name}: {n} adet {label} için "
                f"{CATEGORY_LABEL[primary]} kanalı eksik. {note}".strip()
            ))

    line["channels"] = {
        cat: [need.get(cat, 0), have.get(cat, 0)]
        for cat in sorted(set(need) | set(have))
    }
    # geriye uyumlu alanlar (PDF/ekran eski sütunları)
    line["relay"] = line["channels"].get("relay", [0, 0])
    line["dimmer"] = line["channels"].get("dimmer", [0, 0])
    line["blind"] = line["channels"].get("curtain_actuator", [0, 0])

    # --- Kollektor ---
    for c in floor.get("collectors", []) or []:
        if not c.get("room"):
            issues.append(_issue(
                "warn", "COLLECTOR_ROOM",
                f"{name}: '{c.get('name', 'Kollektör')}' bir odaya "
                f"bağlı değil; vanaları kanal hesabına girmedi."
            ))

    return issues, line


def check_project(data):
    floors = _floors(data)
    issues = []
    lines = []

    active_lines = 0
    for fi, floor in enumerate(floors):
        f_issues, line = check_floor(floor, fi + 1)
        issues.extend(f_issues)
        lines.append(line)
        if line["device_count"] or floor.get("panelProducts"):
            active_lines += 1

    if len(floors) > MAX_LINES_PER_AREA:
        issues.append(_issue(
            "error", "AREA_LINES",
            f"{len(floors)} kat var; bir alanda en fazla "
            f"{MAX_LINES_PER_AREA} hat olabilir."
        ))

    # Birden fazla hat varsa HER hatta coupler / router sart
    if active_lines > 1:
        for fi, floor in enumerate(floors):
            if not lines[fi]["device_count"]:
                continue
            has_coupler = any(
                p.get("category") in ("router", "line_coupler")
                for p in floor.get("panelProducts", []) or []
            )
            if not has_coupler:
                issues.append(_issue(
                    "error", "NO_COUPLER",
                    f"{floor.get('name', 'Kat')} (hat 1.{fi + 1}): "
                    f"Projede {active_lines} hat var; bu hatta IP Router "
                    f"veya Line Coupler yok. Hat diğerleriyle haberleşemez."
                ))

    # Programlama erisimi
    has_access = any(
        p.get("category") in ("interface", "router")
        for f in floors for p in f.get("panelProducts", []) or []
    )
    any_bus = any(l["device_count"] for l in lines)
    if any_bus and not has_access:
        issues.append(_issue(
            "warn", "NO_INTERFACE",
            "Projede IP Interface / IP Router yok. ETS ile programlama "
            "için USB veya IP erişimi gerekir."
        ))

    gas, ga_issues = build_gas(data)
    issues.extend(ga_issues)

    errors = sum(1 for i in issues if i["level"] == "error")
    warns = sum(1 for i in issues if i["level"] == "warn")

    return {
        "summary": {
            "errors": errors,
            "warnings": warns,
            "status": "error" if errors else ("warn" if warns else "ok"),
        },
        "issues": issues,
        "lines": lines,
        "group_addresses": gas,
        "physical_addresses": build_physical(data),
    }
