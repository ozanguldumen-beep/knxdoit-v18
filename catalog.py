"""
KNXdoit ürün kataloğu — TEK KAYNAK.

Editör bu kataloğu /api/catalog ile alır; kural motoru (knx_rules.py)
ve kablo kontrolü (knx_wiring.py) doğrudan buradan okur.

Saha cihazı türleri (kind):
  "load"    : 230V yük; bir aktüatör kanalından beslenir (enerji kablosu)
  "control" : enerjisi panodan DOĞRUDAN gelir (sigorta); kontrolü bir
              gateway kanalından yapılır (klima, VRF iç ünite)
  "bus"     : KNX bus cihazı (yeşil kablo)

mA değerleri VARSAYILANDIR; kesin hesap için datasheet kullanılmalıdır.
Kablo kesitleri ÖRNEKTİR; kesit ve sigortayı elektrikçi belirler.
"""

# --------------------------------
# GRUP ADRESİ ANA GRUPLARI (fonksiyon)
# --------------------------------

GA_GROUPS = {
    1: "Aydınlatma",
    2: "Perde / Jalüzi",
    3: "Isıtma / HVAC",
    4: "Tuş / Sensör",
    5: "Genel Yükler",
    6: "Klima",
}

# --------------------------------
# SAHA CİHAZLARI (odaya eklenir)
# --------------------------------
# objects: (kod, DPT, fonksiyon adı) — "×buttons" / "×inputs" çoğaltılır

ROOM_DEVICES = [
    # --- Aydınlatma ---
    {"id": "light", "type": "light", "label": "Lamba", "icon": "💡",
     "group": "Aydınlatma", "kind": "load", "ga": 1, "cable": "3×1.5",
     "objects": [("SW", "DPST-1-1", "Aç/Kapa"), ("SW_FB", "DPST-1-1", "Aç/Kapa D.B.")]},
    {"id": "dim", "type": "dim", "label": "Dim Lamba", "icon": "🔆",
     "group": "Aydınlatma", "kind": "load", "ga": 1, "cable": "3×1.5",
     "objects": [("DIM_SW", "DPST-1-1", "Aç/Kapa"), ("DIM_REL", "DPST-3-7", "Rölatif Dim"),
                 ("DIM_VAL", "DPST-5-1", "Değer"), ("DIM_VAL_FB", "DPST-5-1", "Değer D.B.")]},
    {"id": "rgbw", "type": "rgbw", "label": "RGBW LED Şerit", "icon": "🌈",
     "group": "Aydınlatma", "kind": "load", "ga": 1, "cable": "5×0.75 (24V DC)",
     "objects": [("RGB_SW", "DPST-1-1", "Aç/Kapa"), ("RGB", "DPST-232-600", "Renk RGB"),
                 ("W", "DPST-5-1", "Beyaz Kanal"), ("RGB_FB", "DPST-232-600", "Renk D.B.")]},
    {"id": "dali", "type": "dali", "label": "DALI Armatür", "icon": "💠",
     "group": "Aydınlatma", "kind": "load", "ga": 1, "cable": "DALI 2×1.5 + 3×1.5",
     "objects": [("DALI_SW", "DPST-1-1", "Aç/Kapa"), ("DALI_REL", "DPST-3-7", "Rölatif Dim"),
                 ("DALI_VAL", "DPST-5-1", "Değer")]},
    {"id": "onoff", "type": "onoff", "label": "On/Off Yük", "icon": "⏻",
     "group": "Aydınlatma", "kind": "load", "ga": 5, "cable": "3×1.5",
     "objects": [("SW", "DPST-1-1", "Aç/Kapa"), ("SW_FB", "DPST-1-1", "Aç/Kapa D.B.")]},

    # --- Perde ---
    {"id": "curtain", "type": "curtain", "label": "Perde Motoru", "icon": "🪟",
     "group": "Perde / Jalüzi", "kind": "load", "ga": 2, "cable": "4×1.5",
     "objects": [("BLD_MOVE", "DPST-1-8", "Yukarı/Aşağı"), ("BLD_STOP", "DPST-1-7", "Adım/Dur"),
                 ("BLD_POS", "DPST-5-1", "Pozisyon"), ("BLD_POS_FB", "DPST-5-1", "Pozisyon D.B.")]},

    # --- Isıtma / Soğutma ---
    {"id": "valve", "type": "valve", "label": "Termoelektrik Vana", "icon": "♨️",
     "group": "Isıtma / Soğutma", "kind": "load", "ga": 3, "cable": "2×1.5",
     "objects": [("VALVE", "DPST-1-1", "Vana Aç/Kapa"), ("VALVE_FB", "DPST-1-1", "Vana D.B.")]},
    {"id": "valve_solenoid", "type": "valve_solenoid", "label": "Solenoid Vana", "icon": "🔩",
     "group": "Isıtma / Soğutma", "kind": "load", "ga": 3, "cable": "3×1.5",
     "objects": [("VALVE", "DPST-1-1", "Vana Aç/Kapa")]},
    {"id": "valve_motor", "type": "valve_motor", "label": "Motorlu Vana (Aç/Kapa)", "icon": "⚙️",
     "group": "Isıtma / Soğutma", "kind": "load", "ga": 3, "cable": "4×1.5",
     "objects": [("VALVE_OC", "DPST-1-9", "Aç/Kapa"), ("VALVE_FB", "DPST-1-9", "Konum D.B.")]},
    {"id": "valve_prop", "type": "valve_prop", "label": "Motorlu Vana (0-10V)", "icon": "🎚",
     "group": "Isıtma / Soğutma", "kind": "load", "ga": 3, "cable": "4×0.75 (24V + 0-10V)",
     "objects": [("VALVE_POS", "DPST-5-1", "Vana Konumu %"), ("VALVE_FB", "DPST-5-1", "Konum D.B.")]},
    {"id": "fancoil", "type": "fancoil", "label": "Fancoil", "icon": "🌀",
     "group": "Isıtma / Soğutma", "kind": "load", "ga": 3, "cable": "7×1.5 (3 fan hızı + vana)",
     "objects": [("FC_SW", "DPST-1-1", "Aç/Kapa"), ("FC_SPEED", "DPST-5-1", "Fan Hızı %"),
                 ("FC_VALVE", "DPST-5-1", "Vana %"), ("FC_FB", "DPST-1-1", "Durum D.B.")]},

    # --- Klima ---
    {"id": "ac_split", "type": "ac_split", "label": "Split Klima", "icon": "❄️",
     "group": "Klima", "kind": "control", "ga": 6, "cable": "3×2.5 (doğrudan sigorta)",
     "objects": [("AC_SW", "DPST-1-1", "Aç/Kapa"), ("AC_MODE", "DPST-20-105", "Mod"),
                 ("AC_SET", "DPST-9-1", "Ayar Sıcaklığı"), ("AC_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
                 ("AC_FAN", "DPST-5-1", "Fan Hızı")]},
    {"id": "vrf_indoor", "type": "vrf_indoor", "label": "VRF İç Ünite", "icon": "🧊",
     "group": "Klima", "kind": "control", "ga": 6, "cable": "3×1.5 (doğrudan sigorta)",
     "objects": [("AC_SW", "DPST-1-1", "Aç/Kapa"), ("AC_MODE", "DPST-20-105", "Mod"),
                 ("AC_SET", "DPST-9-1", "Ayar Sıcaklığı"), ("AC_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
                 ("AC_FAN", "DPST-5-1", "Fan Hızı")]},

    # --- Duvar (KNX bus) ---
    {"id": "switch1", "type": "switch", "buttons": 1, "label": "Tuş Paneli 1'li", "icon": "🔘",
     "group": "Duvar", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("PUSH", "DPST-1-1", "Tuş")]},
    {"id": "switch2", "type": "switch", "buttons": 2, "label": "Tuş Paneli 2'li", "icon": "🔘",
     "group": "Duvar", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("PUSH", "DPST-1-1", "Tuş")]},
    {"id": "switch4", "type": "switch", "buttons": 4, "label": "Tuş Paneli 4'lü", "icon": "🔘",
     "group": "Duvar", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("PUSH", "DPST-1-1", "Tuş")]},
    {"id": "switch6", "type": "switch", "buttons": 6, "label": "Tuş Paneli 6'lı", "icon": "🔘",
     "group": "Duvar", "kind": "bus", "ga": 4, "ma": 12,
     "objects": [("PUSH", "DPST-1-1", "Tuş")]},
    {"id": "switch8", "type": "switch", "buttons": 8, "label": "Tuş Paneli 8'li", "icon": "🔘",
     "group": "Duvar", "kind": "bus", "ga": 4, "ma": 12,
     "objects": [("PUSH", "DPST-1-1", "Tuş")]},
    {"id": "thermo_switch", "type": "thermo_switch", "label": "Termostatlı Tuş Paneli", "icon": "🎛",
     "group": "Duvar", "kind": "bus", "ga": 3, "ma": 15,
     "objects": [("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"), ("TEMP_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
                 ("TEMP_MODE", "DPST-20-102", "Mod"), ("PUSH1", "DPST-1-1", "Tuş 1"),
                 ("PUSH2", "DPST-1-1", "Tuş 2"), ("PUSH3", "DPST-1-1", "Tuş 3"), ("PUSH4", "DPST-1-1", "Tuş 4")]},
    {"id": "thermostat", "type": "thermostat", "label": "Termostat", "icon": "🌡",
     "group": "Duvar", "kind": "bus", "ga": 3, "ma": 15,
     "objects": [("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"), ("TEMP_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
                 ("TEMP_MODE", "DPST-20-102", "Mod"), ("TEMP_FB", "DPST-9-1", "Ayar D.B.")]},
    {"id": "room_ctrl", "type": "room_ctrl", "label": "Oda Kontrol Ünitesi (ekranlı)", "icon": "📟",
     "group": "Duvar", "kind": "bus", "ga": 3, "ma": 20,
     "objects": [("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"), ("TEMP_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
                 ("TEMP_MODE", "DPST-20-102", "Mod"), ("SCENE", "DPST-18-1", "Sahne")]},
    {"id": "touch", "type": "touch", "label": "Dokunmatik Panel", "icon": "📱",
     "group": "Duvar", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("SCENE", "DPST-18-1", "Sahne")]},
    {"id": "universal_if", "type": "universal_if", "inputs": 4, "label": "Universal Interface (4 giriş)",
     "icon": "🔌", "group": "Duvar", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("INPUT", "DPST-1-1", "Giriş")]},

    # --- Sensör (KNX bus) ---
    {"id": "presence", "type": "presence", "label": "Varlık / Hareket Sensörü", "icon": "👁",
     "group": "Sensör", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("PRES", "DPST-1-18", "Varlık"), ("LUX", "DPST-9-4", "Işık Seviyesi")]},
    {"id": "temp_hum", "type": "temp_hum", "label": "Sıcaklık-Nem Sensörü", "icon": "💧",
     "group": "Sensör", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("TEMP", "DPST-9-1", "Sıcaklık"), ("HUM", "DPST-9-7", "Nem")]},
    {"id": "co2", "type": "co2", "label": "CO₂ / Hava Kalitesi", "icon": "🫧",
     "group": "Sensör", "kind": "bus", "ga": 4, "ma": 15,
     "objects": [("CO2", "DPST-9-8", "CO₂ ppm")]},
    {"id": "weather", "type": "weather", "label": "Hava İstasyonu", "icon": "🌦",
     "group": "Sensör", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("WIND", "DPST-9-5", "Rüzgâr"), ("LUX", "DPST-9-4", "Işık"),
                 ("RAIN", "DPST-1-5", "Yağmur Alarmı"), ("TEMP", "DPST-9-1", "Dış Sıcaklık")]},
    {"id": "light_sensor", "type": "light_sensor", "label": "Işık Sensörü", "icon": "🌤",
     "group": "Sensör", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("LUX", "DPST-9-4", "Işık Seviyesi")]},
    {"id": "leak", "type": "leak", "label": "Su Kaçak Sensörü", "icon": "💦",
     "group": "Sensör", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("LEAK", "DPST-1-5", "Su Kaçak Alarmı")]},
    {"id": "sensor", "type": "sensor", "label": "Sensör (genel)", "icon": "📡",
     "group": "Sensör", "kind": "bus", "ga": 4, "ma": 10,
     "objects": [("SENS", "DPST-1-1", "Sensör")]},

    # --- Akubela (Modüler Otomasyon) ---
    # Açıklamalar ürün listesinden alınmıştır. Dahili röle yük akımı, bus
    # akımı ve panel beslemesi DATASHEET'ten doğrulanmalıdır.
    {"id": "akb_elite10", "type": "akb_elite10", "brand": "Akubela", "sku": None,
     "label": "Akubela Hypanel Elite 10\" PH59-KNX", "icon": "🖥",
     "desc": "10\" KNX dokunmatik panel",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 0,
     "objects": [("SCENE", "DPST-18-1", "Sahne"), ("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı")]},
    {"id": "akb_keyplus", "type": "akb_keyplus", "brand": "Akubela", "sku": "153-02-321",
     "label": "Akubela Hypanel KeyPlus KS03 KNX", "icon": "🎛",
     "desc": "Ekranlı tuşlu KNX panel",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 0,
     "objects": [("SCENE", "DPST-18-1", "Sahne"), ("PUSH1", "DPST-1-1", "Tuş 1"),
                 ("PUSH2", "DPST-1-1", "Tuş 2"), ("PUSH3", "DPST-1-1", "Tuş 3")]},
    {"id": "akb_ps51", "type": "akb_ps51", "brand": "Akubela", "sku": "153-02-124",
     "label": "Akubela Hypanel KNX Kasası PS51-KS41", "icon": "🔲",
     "desc": "Hypanel KNX kasası, ilave 2 kuru kontak röle",
     "group": "Akubela", "kind": "bus", "ga": 1, "ma": 10, "relays": 2,
     "objects": []},
    {"id": "akb_lux", "type": "akb_lux", "brand": "Akubela", "sku": None,
     "label": "Akubela Hypanel Lux RT61 KNX", "icon": "⏺",
     "desc": "Android 10, döner yuvarlak 2.3\" ekran, 4 fiziksel buton, dahili 2 röle, dahili sıcaklık-nem sensörü",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 2,
     "objects": [("PUSH1", "DPST-1-1", "Tuş 1"), ("PUSH2", "DPST-1-1", "Tuş 2"),
                 ("PUSH3", "DPST-1-1", "Tuş 3"), ("PUSH4", "DPST-1-1", "Tuş 4"),
                 ("TEMP", "DPST-9-1", "Sıcaklık"), ("HUM", "DPST-9-7", "Nem")]},
    {"id": "akb_pro", "type": "akb_pro", "brand": "Akubela", "sku": None,
     "label": "Akubela Hypanel Pro KNX (8\", kameralı)", "icon": "📷",
     "desc": "Kameralı 8\" KNX panel, 2 röle ilaveli",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 2,
     "objects": [("SCENE", "DPST-18-1", "Sahne"), ("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı")]},
    {"id": "akb_supreme", "type": "akb_supreme", "brand": "Akubela", "sku": None,
     "label": "Akubela Hypanel Supreme KNX (12.36\")", "icon": "🖥",
     "desc": "12.36\" KNX, 2 çıkış, 1 kapı zili girişi, Zigbee, 2M kasa",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 2,
     "objects": [("SCENE", "DPST-18-1", "Sahne"), ("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"),
                 ("BELL", "DPST-1-1", "Kapı Zili")]},
    {"id": "akb_ultra", "type": "akb_ultra", "brand": "Akubela", "sku": None,
     "label": "Akubela Hypanel Ultra KNX (10\")", "icon": "🖥",
     "desc": "10\" KNX, 2 çıkış, 1 kapı zili girişi, Zigbee, 2M kasa",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 2,
     "objects": [("SCENE", "DPST-18-1", "Sahne"), ("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"),
                 ("BELL", "DPST-1-1", "Kapı Zili")]},
    {"id": "akb_k32b4_multi", "type": "akb_k32b4", "brand": "Akubela", "sku": "153-02-360",
     "label": "Akubela Aura K32-B4 4 Tuş (çoklu kit)", "icon": "🔳",
     "desc": "Aura serisi çoklu 4 buton KNX anahtar (support bracket dahil değil)",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 0,
     "objects": [("PUSH1", "DPST-1-1", "Tuş 1"), ("PUSH2", "DPST-1-1", "Tuş 2"),
                 ("PUSH3", "DPST-1-1", "Tuş 3"), ("PUSH4", "DPST-1-1", "Tuş 4")]},
    {"id": "akb_k32b4_single", "type": "akb_k32b4", "brand": "Akubela", "sku": "153-02-359",
     "label": "Akubela Aura K32-B4 4 Tuş (tekli)", "icon": "🔳",
     "desc": "Aura serisi tekli 4 buton KNX anahtar (tekli support bracket dahil)",
     "group": "Akubela", "kind": "bus", "ga": 4, "ma": 10, "relays": 0,
     "objects": [("PUSH1", "DPST-1-1", "Tuş 1"), ("PUSH2", "DPST-1-1", "Tuş 2"),
                 ("PUSH3", "DPST-1-1", "Tuş 3"), ("PUSH4", "DPST-1-1", "Tuş 4")]},
    {"id": "akb_k32m_multi", "type": "akb_k32m", "brand": "Akubela", "sku": "153-02-362",
     "label": "Akubela Aura K32-M Termostat (çoklu kit)", "icon": "🌡",
     "desc": "Aura serisi çoklu termostat paneli; HVAC mod / fan hızı / swing (support bracket dahil değil)",
     "group": "Akubela", "kind": "bus", "ga": 3, "ma": 10, "relays": 0,
     "objects": [("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"), ("TEMP_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
                 ("HVAC_MODE", "DPST-20-105", "HVAC Mod"), ("FAN", "DPST-5-1", "Fan Hızı"),
                 ("SWING", "DPST-1-1", "Swing")]},
    {"id": "akb_k32m_single", "type": "akb_k32m", "brand": "Akubela", "sku": "153-02-361",
     "label": "Akubela Aura K32-M Termostat (tekli)", "icon": "🌡",
     "desc": "Aura serisi tekli termostat paneli; HVAC mod / fan hızı / swing (tekli support bracket dahil)",
     "group": "Akubela", "kind": "bus", "ga": 3, "ma": 10, "relays": 0,
     "objects": [("TEMP_SET", "DPST-9-1", "Ayar Sıcaklığı"), ("TEMP_ACT", "DPST-9-1", "Ortam Sıcaklığı"),
                 ("HVAC_MODE", "DPST-20-105", "HVAC Mod"), ("FAN", "DPST-5-1", "Fan Hızı"),
                 ("SWING", "DPST-1-1", "Swing")]},
]

# --------------------------------
# KANAL UYUMU: hangi yük hangi ürün kanalına bağlanır
# --------------------------------
# (kategori, kaç kanal kaplar, uyarı metni ya da None)
# İlk seçenek BİRİNCİL'dir; sonrakiler izinli ALTERNATİF.

COMPAT = {
    "light": [("relay", 1, None)],
    "onoff": [("relay", 1, None)],
    "dim": [("dimmer", 1, None)],
    "rgbw": [("rgbw", 1, None)],
    "dali": [("dali", 1, None)],
    "curtain": [
        ("curtain_actuator", 1, None),
        ("relay", 2, "Perde röleye 2 kanalla (Yukarı/Aşağı) bağlanır; ETS'de UP/DOWN kilitlemesi ayarlanmalı."),
    ],
    "valve": [
        ("heating", 1, None),
        ("relay", 1, "Termoelektrik vana röleyle de sürülebilir; PWM/oransal kontrol için Isıtma Aktüatörü önerilir."),
    ],
    "valve_solenoid": [("relay", 1, None)],
    "valve_motor": [
        ("curtain_actuator", 1, None),
        ("relay", 2, "Motorlu vana röleye 2 kanalla (Aç/Kapa) bağlanır; ETS'de kilitleme ayarlanmalı."),
    ],
    "valve_prop": [("analog", 1, None)],
    "fancoil": [("fancoil", 1, None)],
    "ac_split": [("ac_gateway", 1, None)],
    "vrf_indoor": [("vrf_gateway", 1, None)],
}

# Bir yük kendi doğru aktüatörü dışında hiçbir yere bağlanamazsa
# kullanıcıya gösterilecek ek açıklama
COMPAT_NOTE = {
    "dim": "Dim lamba röleye bağlanırsa dim çalışmaz.",
    "valve_prop": "0-10V vana röleyle sürülemez; Analog Aktüatör gerekir.",
    "ac_split": "Klima röleye bağlanmaz: enerjisi panodan doğrudan gelir, kontrol KNX-AC Gateway ile yapılır.",
    "vrf_indoor": "VRF iç ünite röleye bağlanmaz: kontrol KNX-VRF Gateway ile yapılır.",
    "fancoil": "Fancoil'in 3 fan hızı ve vanası Fancoil Aktüatörü ile sürülür.",
}

# --------------------------------
# PANO ÜRÜNLERİ
# --------------------------------

CATEGORY_LABEL = {
    "power_supply": "Power Supply",
    "interface": "Programlama Arayüzü",
    "router": "IP Router",
    "line_coupler": "Line Coupler",
    "relay": "Switch Aktüatör",
    "dimmer": "Dimmer Aktüatör",
    "curtain_actuator": "Jalüzi/Perde Aktüatörü",
    "heating": "Isıtma Aktüatörü",
    "fancoil": "Fancoil Aktüatörü",
    "analog": "Analog Aktüatör (0-10V)",
    "rgbw": "RGBW / LED Kontrol",
    "dali": "DALI Gateway",
    "ac_gateway": "KNX-AC Gateway (split)",
    "vrf_gateway": "KNX-VRF Gateway",
    "gateway_other": "Diğer Gateway",
    "input": "Binary Input",
    "meter": "Enerji Sayacı",
    "logic": "Lojik Modül",
    "visu": "Görselleştirme Sunucusu",
}

# Kanalı olan (yük / kontrol çıkışı veren) kategoriler
OUTPUT_CATEGORIES = {c for opts in COMPAT.values() for c, _, _ in opts}
GATEWAY_CATEGORIES = {"ac_gateway", "vrf_gateway", "dali"}

PANEL_PRODUCTS = [
    # Sistem
    {"id": "psu160", "name": "KNX Power Supply 160mA", "category": "power_supply", "moduleWidth": 2, "channels": 1, "psuMa": 160, "color": "#2563eb"},
    {"id": "psu320", "name": "KNX Power Supply 320mA", "category": "power_supply", "moduleWidth": 4, "channels": 1, "psuMa": 320, "color": "#2563eb"},
    {"id": "psu640", "name": "KNX Power Supply 640mA", "category": "power_supply", "moduleWidth": 4, "channels": 1, "psuMa": 640, "color": "#2563eb"},
    {"id": "psu1280", "name": "KNX Power Supply 1280mA", "category": "power_supply", "moduleWidth": 6, "channels": 1, "psuMa": 1280, "color": "#1d4ed8"},
    {"id": "ip-interface", "name": "KNX IP Interface", "category": "interface", "moduleWidth": 2, "channels": 1, "busMa": 10, "color": "#7c3aed"},
    {"id": "usb-interface", "name": "KNX USB Interface", "category": "interface", "moduleWidth": 2, "channels": 1, "busMa": 10, "color": "#7c3aed"},
    {"id": "ip-router", "name": "KNX IP Router", "category": "router", "moduleWidth": 2, "channels": 1, "busMa": 20, "color": "#334155"},
    {"id": "line-coupler", "name": "KNX Line Coupler", "category": "line_coupler", "moduleWidth": 2, "channels": 1, "busMa": 15, "color": "#475569"},
    # Switch
    {"id": "relay8", "name": "Switch Aktüatör 8 Kanal", "category": "relay", "moduleWidth": 8, "channels": 8, "busMa": 15, "color": "#16a34a"},
    {"id": "relay12", "name": "Switch Aktüatör 12 Kanal", "category": "relay", "moduleWidth": 12, "channels": 12, "busMa": 15, "color": "#16a34a"},
    {"id": "relay16", "name": "Switch Aktüatör 16 Kanal", "category": "relay", "moduleWidth": 12, "channels": 16, "busMa": 15, "color": "#16a34a"},
    {"id": "relay24", "name": "Switch Aktüatör 24 Kanal", "category": "relay", "moduleWidth": 12, "channels": 24, "busMa": 15, "color": "#159947"},
    {"id": "relay8cs", "name": "Switch Aktüatör 8 Kanal (Akım Ölçümlü)", "category": "relay", "moduleWidth": 8, "channels": 8, "busMa": 15, "color": "#15803d"},
    # Dimmer / LED / DALI
    {"id": "dimmer2", "name": "Dimmer Aktüatör 2 Kanal", "category": "dimmer", "moduleWidth": 4, "channels": 2, "busMa": 15, "color": "#f97316"},
    {"id": "dimmer4", "name": "Dimmer Aktüatör 4 Kanal", "category": "dimmer", "moduleWidth": 4, "channels": 4, "busMa": 15, "color": "#f97316"},
    {"id": "dimmer8", "name": "Dimmer Aktüatör 8 Kanal", "category": "dimmer", "moduleWidth": 6, "channels": 8, "busMa": 15, "color": "#f97316"},
    {"id": "rgbw1", "name": "RGBW LED Kontrol 1 Şerit", "category": "rgbw", "moduleWidth": 4, "channels": 1, "busMa": 10, "color": "#db2777"},
    {"id": "rgbw2", "name": "RGBW LED Kontrol 2 Şerit", "category": "rgbw", "moduleWidth": 4, "channels": 2, "busMa": 10, "color": "#db2777"},
    {"id": "dali64", "name": "DALI Gateway 64 Armatür", "category": "dali", "moduleWidth": 4, "channels": 64, "busMa": 10, "color": "#0891b2"},
    # Perde
    {"id": "curtain4", "name": "Jalüzi/Perde Aktüatörü 4 Kanal", "category": "curtain_actuator", "moduleWidth": 4, "channels": 4, "busMa": 15, "color": "#0f766e"},
    {"id": "curtain8", "name": "Jalüzi/Perde Aktüatörü 8 Kanal", "category": "curtain_actuator", "moduleWidth": 6, "channels": 8, "busMa": 15, "color": "#0f766e"},
    # Isıtma / HVAC
    {"id": "heating6", "name": "Isıtma Aktüatörü 6 Kanal", "category": "heating", "moduleWidth": 4, "channels": 6, "busMa": 10, "color": "#dc2626"},
    {"id": "heating12", "name": "Isıtma Aktüatörü 12 Kanal", "category": "heating", "moduleWidth": 6, "channels": 12, "busMa": 10, "color": "#dc2626"},
    {"id": "fancoil1", "name": "Fancoil Aktüatörü 1 Ünite", "category": "fancoil", "moduleWidth": 4, "channels": 1, "busMa": 15, "color": "#b45309"},
    {"id": "fancoil2", "name": "Fancoil Aktüatörü 2 Ünite", "category": "fancoil", "moduleWidth": 8, "channels": 2, "busMa": 15, "color": "#b45309"},
    {"id": "analog4", "name": "Analog Aktüatör 4 Kanal (0-10V)", "category": "analog", "moduleWidth": 4, "channels": 4, "busMa": 15, "color": "#9333ea"},
    # Klima gateway
    {"id": "ac-gw", "name": "KNX-AC Gateway (1 iç ünite)", "category": "ac_gateway", "moduleWidth": 2, "channels": 1, "busMa": 10, "color": "#0284c7"},
    {"id": "vrf-gw16", "name": "KNX-VRF Gateway 16 İç Ünite", "category": "vrf_gateway", "moduleWidth": 4, "channels": 16, "busMa": 10, "color": "#0369a1"},
    {"id": "vrf-gw64", "name": "KNX-VRF Gateway 64 İç Ünite", "category": "vrf_gateway", "moduleWidth": 4, "channels": 64, "busMa": 10, "color": "#075985"},
    # Diğer gateway / giriş / ölçüm
    {"id": "modbus-gw", "name": "KNX-Modbus Gateway", "category": "gateway_other", "moduleWidth": 4, "channels": 1, "busMa": 10, "color": "#64748b"},
    {"id": "bacnet-gw", "name": "KNX-BACnet Gateway", "category": "gateway_other", "moduleWidth": 4, "channels": 1, "busMa": 10, "color": "#64748b"},
    {"id": "ir-gw", "name": "KNX IR Gateway", "category": "gateway_other", "moduleWidth": 2, "channels": 1, "busMa": 10, "color": "#64748b"},
    {"id": "binary4", "name": "Binary Input 4 Kanal", "category": "input", "moduleWidth": 2, "channels": 4, "busMa": 10, "color": "#475569"},
    {"id": "binary8", "name": "Binary Input 8 Kanal", "category": "input", "moduleWidth": 4, "channels": 8, "busMa": 10, "color": "#475569"},
    {"id": "meter3", "name": "KNX Enerji Sayacı 3 Faz", "category": "meter", "moduleWidth": 4, "channels": 1, "busMa": 10, "color": "#a16207"},
    {"id": "logic", "name": "KNX Lojik Modül", "category": "logic", "moduleWidth": 2, "channels": 1, "busMa": 10, "color": "#4b5563"},
    {"id": "visu", "name": "Görselleştirme Sunucusu", "category": "visu", "moduleWidth": 4, "channels": 1, "busMa": 10, "color": "#1f2937"},
]

# Bus akımı için kategori varsayılanları (ürün busMa vermezse)
DEFAULT_BUS_MA = {
    "interface": 10, "router": 20, "line_coupler": 15, "relay": 15,
    "dimmer": 15, "curtain_actuator": 15, "heating": 10, "fancoil": 15,
    "analog": 15, "rgbw": 10, "dali": 10, "ac_gateway": 10,
    "vrf_gateway": 10, "gateway_other": 10, "input": 10, "meter": 10,
    "logic": 10, "visu": 10,
}

# --------------------------------
# TÜRETİLMİŞ TABLOLAR
# --------------------------------

DEVICE_BY_TYPE = {}
for _d in ROOM_DEVICES:
    DEVICE_BY_TYPE.setdefault(_d["type"], _d)   # switch: ilki (1'li) temel tanım

LOAD_TYPES = {d["type"] for d in ROOM_DEVICES if d["kind"] in ("load", "control")}
CONTROL_TYPES = {d["type"] for d in ROOM_DEVICES if d["kind"] == "control"}
BUS_TYPES = {d["type"] for d in ROOM_DEVICES if d["kind"] == "bus"}


def device_objects(dev):
    """Bir cihaz örneğinin grup adresi nesneleri (tuş/giriş sayısına göre)."""
    base = DEVICE_BY_TYPE.get(dev.get("type"))
    if not base:
        base = DEVICE_BY_TYPE["light"]
    objs = list(base["objects"])
    if base["type"] == "switch":
        n = int(dev.get("buttons") or 1)
        return [(f"PUSH{i}", "DPST-1-1", f"Tuş {i}") for i in range(1, n + 1)]
    if base.get("relays"):
        objs = objs + [
            (f"R{i}", "DPST-1-1", f"Dahili Röle {i} Aç/Kapa")
            for i in range(1, int(base["relays"]) + 1)
        ]
        return objs
    if base["type"] == "universal_if":
        n = int(dev.get("inputs") or base.get("inputs") or 4)
        return [(f"IN{i}", "DPST-1-1", f"Giriş {i}") for i in range(1, n + 1)]
    return objs


def device_relays(dev):
    """Saha cihazının dahili röle (yük çıkışı) sayısı (Akubela paneller)."""
    base = DEVICE_BY_TYPE.get(dev.get("type"), {})
    return int(base.get("relays") or 0)


def relay_prod_id(dev_id, k):
    """Dahili röle kanalları için sahte ürün kimliği (kablo bağlantısında)."""
    return f"dr_{dev_id}_{k}"


def device_bus_ma(dev):
    base = DEVICE_BY_TYPE.get(dev.get("type"), {})
    if base.get("type") == "switch":
        return 12 if int(dev.get("buttons") or 1) > 4 else 10
    return base.get("ma", 10)


def public_catalog():
    """Editöre gönderilen katalog (JSON)."""
    return {
        "devices": [
            {k: v for k, v in d.items() if k != "objects"} for d in ROOM_DEVICES
        ],
        "products": PANEL_PRODUCTS,
        "categoryLabel": CATEGORY_LABEL,
        "compat": {
            t: [{"category": c, "span": s, "warn": w} for c, s, w in opts]
            for t, opts in COMPAT.items()
        },
        "compatNote": COMPAT_NOTE,
        "gaGroups": GA_GROUPS,
    }
