"""
KNXdoit v18 - KNX kural motoru

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

# Pano urunlerinin varsayilan bus akimi (mA)
DEFAULT_BUS_MA = {
    "interface": 10,
    "router": 20,
    "line_coupler": 15,
    "relay": 15,
    "dimmer": 15,
    "curtain_actuator": 15,
    "input": 10,
}

# Odaya eklenen bus cihazlarinin varsayilan akimi (mA)
ROOM_BUS_MA = {
    "switch": 10,
    "thermostat": 15,
    "sensor": 10,
}

# Hangi oda cihazi hangi aktuator kanalini kullanir
ACTUATOR_FOR = {
    "light": "relay",
    "valve": "relay",
    "onoff": "relay",
    "dim": "dimmer",
    "curtain": "curtain_actuator",
}

CATEGORY_LABEL = {
    "relay": "Switch Aktüatör",
    "dimmer": "Dimmer Aktüatör",
    "curtain_actuator": "Jalüzi/Perde Aktüatörü",
}

# Grup adresi ana gruplari (fonksiyon bazli)
GA_MAIN = {
    "light": (1, "Aydınlatma"),
    "dim": (1, "Aydınlatma"),
    "curtain": (2, "Perde / Jalüzi"),
    "thermostat": (3, "Isıtma / HVAC"),
    "valve": (3, "Isıtma / HVAC"),
    "onoff": (5, "Genel Yükler"),
    "switch": (4, "Tuş / Sensör"),
    "sensor": (4, "Tuş / Sensör"),
}

# Nesne listesi: (kisa kod, DPT, fonksiyon adi)
DPT = {
    "light": [
        ("SW", "DPST-1-1", "Aç/Kapa"),
        ("SW_FB", "DPST-1-1", "Aç/Kapa D.B."),
    ],
    "dim": [
        ("DIM_SW", "DPST-1-1", "Aç/Kapa"),
        ("DIM_REL", "DPST-3-7", "Rölatif Dim"),
        ("DIM_VAL", "DPST-5-1", "Değer"),
        ("DIM_VAL_FB", "DPST-5-1", "Değer D.B."),
    ],
    "curtain": [
        ("BLD_MOVE", "DPST-1-8", "Yukarı/Aşağı"),
        ("BLD_STOP", "DPST-1-7", "Adım/Dur"),
        ("BLD_POS", "DPST-5-1", "Pozisyon"),
        ("BLD_POS_FB", "DPST-5-1", "Pozisyon D.B."),
    ],
    "thermostat": [
        ("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"),
        ("TEMP_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
        ("TEMP_MODE", "DPST-20-102", "Mod"),
        ("TEMP_FB", "DPST-9-1", "Ayar D.B."),
    ],
    "switch": [
        ("PUSH", "DPST-1-1", "Komut"),
    ],
    "sensor": [
        ("SENS", "DPST-1-1", "Sensör"),
    ],
    "valve": [
        ("VALVE", "DPST-1-1", "Vana Aç/Kapa"),
    ],
    "onoff": [
        ("SW", "DPST-1-1", "Aç/Kapa"),
        ("SW_FB", "DPST-1-1", "Aç/Kapa D.B."),
    ],
}

# 230V yükler (aktüatör kanalına bağlanır) ve KNX bus cihazları
ENERGY_TYPES = {"light", "dim", "curtain", "valve", "onoff"}
BUS_TYPES = {"switch", "thermostat", "sensor"}
LOAD_OUTPUT_CATEGORIES = {"relay", "dimmer", "curtain_actuator"}


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
            main, main_name = GA_MAIN.get(dtype, GA_MAIN["light"])
            objects = DPT.get(dtype, DPT["light"])
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
        if dtype not in ROOM_BUS_MA:
            continue   # lamba, vana, perde motoru bus cihazi degil
        count = max(1, _int(dev.get("count", 1), 1))
        for n in range(1, count + 1):
            label = dev.get("label", "Cihaz")
            items.append({
                "name": f"{label} {n}" if count > 1 else label,
                "category": dtype,
                "location": room.get("name", "Oda"),
                "ma": ROOM_BUS_MA[dtype],
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

    # --- Aktuator kanallari ---
    relay_have = _channels(floor, "relay")
    relay_need = (
        _needed(floor, "light")
        + _needed(floor, "valve")
        + _needed(floor, "onoff")
    )
    dim_have = _channels(floor, "dimmer")
    dim_need = _needed(floor, "dim")
    blind_have = _channels(floor, "curtain_actuator")
    blind_need = _needed(floor, "curtain")

    line.update({
        "relay": [relay_need, relay_have],
        "dimmer": [dim_need, dim_have],
        "blind": [blind_need, blind_have],
    })

    if dim_need > dim_have:
        issues.append(_issue(
            "error", "DIM_CHANNELS",
            f"{name}: {dim_need} dim lamba var, dimmer kanalı "
            f"{dim_have}. Dim lamba röleye bağlanırsa dim çalışmaz; "
            f"{dim_need - dim_have} dimmer kanalı daha gerekli."
        ))

    relay_spare = relay_have - relay_need
    blind_missing = max(0, blind_need - blind_have)

    if relay_spare < 0:
        issues.append(_issue(
            "error", "RELAY_CHANNELS",
            f"{name}: Lamba + vana + on/off için {relay_need} röle kanalı "
            f"gerekli, {relay_have} var. {-relay_spare} kanal eksik."
        ))

    if blind_missing:
        if relay_spare >= blind_missing * 2:
            issues.append(_issue(
                "warn", "BLIND_ON_RELAY",
                f"{name}: {blind_missing} perde için perde aktüatörü "
                f"kanalı yok. Boştaki röle kanallarıyla yapılacaksa "
                f"perde başına 2 kanal (UP/DOWN) ve kilitleme gerekir."
            ))
        else:
            issues.append(_issue(
                "error", "BLIND_CHANNELS",
                f"{name}: {blind_need} perde var, perde aktüatörü "
                f"kanalı {blind_have}. {blind_missing} kanal eksik."
            ))

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
