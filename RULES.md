# KNXdoit v22 — Kural Listesi

Kodda karşılığı: `knx_rules.py` (proje kuralları) ve `knx_wiring.py` (elle çekilen kablolar). Ekran, PDF ve `.knxproj` aynı hesaptan beslenir.
Durum: 🔴 Hata (proje uygulanmamalı) · 🟠 Uyarı (kontrol edilmeli) · 🟢 Uygun

## Varsayımlar
- 1 alan (Area 1). **Her kat = 1 hat**: Zemin Kat → 1.1.x, 1. Kat → 1.2.x
- mA değerleri **varsayılan**dır; kesin hesap için ürün datasheet değeri girilmeli.

## Elektrik / Kablo (çizim kuralları)
| Kural | Durum |
|---|---|
| Kahverengi = 230V enerji, Yeşil = KNX bus | Çizimde bus yeşil ✅ (enerji kablosu çizimi v19) |
| Bus klemensi: kırmızı (+) / siyah (−) | Çizimde her modülde ✅ |
| PS → modüller daisy chain, ring yok | Çizimde ✅ |
| Kollektör dolabına KNX bus girmez | v19 (kablo çizimiyle) |

## Aktüatör kanalları (her kat kendi panosu)
| Kod | Kural | Seviye |
|---|---|---|
| RELAY_CHANNELS | Lamba + vana sayısı ≤ röle kanalı | 🔴 |
| DIM_CHANNELS | Dim lamba sayısı ≤ dimmer kanalı (röleye bağlanırsa dim çalışmaz) | 🔴 |
| BLIND_CHANNELS | Perde sayısı ≤ perde aktüatörü kanalı | 🔴 |
| BLIND_ON_RELAY | Perde kanalı yok ama perde başına 2 boş röle kanalı var → UP/DOWN + kilitleme gerekir | 🟠 |
| COLLECTOR_ROOM | Kollektör bir odaya bağlı değil → vanalar hesaba girmedi | 🟠 |

## Power Supply / Bus
| Kod | Kural | Seviye |
|---|---|---|
| PSU_MISSING | Bus cihazı olan her hatta PS olmalı | 🔴 |
| PSU_MULTI | Aynı hatta birden fazla PS (paralel bağlanmaz, ≥200 m ayrım) | 🟠 |
| PSU_OVERLOAD | Toplam bus akımı > PS akımı | 🔴 |
| PSU_RESERVE | Toplam × 1.3 > PS akımı (%30 rezerv yok) | 🟠 |
| PSU_NONE_FITS | İhtiyaç 1280 mA'yı aşıyor → hattı böl | 🔴 |
| LINE_DEVICES | Hatta > 64 bus cihazı | 🔴 |
| LINE_DEVICES_RESERVE | Hatta > 50 bus cihazı (genişleme payı az) | 🟠 |

Önerilen PS = toplam bus akımı × 1.3 → 160 / 320 / 640 / 1280 mA'dan büyük ilk değer.
Bus cihazı sayılır: aktüatörler, binary input, interface, router, coupler, anahtar, termostat, sensör.
Sayılmaz: PS, lamba, vana, perde motoru (230V yükler).

## Topoloji
| Kod | Kural | Seviye |
|---|---|---|
| NO_COUPLER | Birden fazla hat varsa her hatta IP Router / Line Coupler | 🔴 |
| AREA_LINES | Bir alanda en fazla 15 hat | 🔴 |
| NO_INTERFACE | Projede IP Interface / Router yok (ETS erişimi) | 🟠 |
| — | Ring yasak; yıldız/ağaç serbest (hata değil) | çizimde ring çizilmez |
| — | Mesafe 350 m / 700 m / 1000 m | v19+ (metre bilgisi yok) |

## Adresleme
**Fiziksel adres** (Alan.Hat.Cihaz): coupler/router `1.<hat>.0`, diğerleri `1.<hat>.1`'den başlar. PS adres almaz.

**Grup adresi** (3 seviye, fonksiyon bazlı):
| Ana grup | Fonksiyon |
|---|---|
| 1 | Aydınlatma (lamba, dim) |
| 2 | Perde / Jalüzi |
| 3 | Isıtma / HVAC (termostat, vana) |
| 4 | Tuş / Sensör |

Orta grup = kat (0–7), alt grup = sıra (1–255).
| Kod | Kural | Seviye |
|---|---|---|
| GA_MIDDLE | 8'den fazla kat → orta grup sınırı (0–7) | 🔴 |
| GA_SUB | Bir fonksiyon/katta 255'ten fazla nesne | 🔴 |

DPT: Aç/Kapa 1.001 · Rölatif dim 3.007 · Değer 5.001 · Perde Yukarı/Aşağı 1.008 · Perde Adım/Dur **1.007** · Sıcaklık 9.001 · HVAC mod 20.102

## Elle çekilen kablolar (v19 editör)
Editör yanlış bağlantıya izin vermez (anında engeller); sunucu aynı kontrolü kaydedilen projede tekrar yapar.

| Kod | Kural | Seviye |
|---|---|---|
| WRONG_ACTUATOR | Lamba / vana / on-off → Switch Aktüatör; dim lamba → Dimmer (röleye bağlanırsa dim çalışmaz); perde → Jalüzi Aktüatörü | 🔴 |
| CURTAIN_ON_RELAY | Perde röleye ancak yan yana 2 boş kanalla (Yukarı + Aşağı) bağlanır; ETS'de kilitleme ayarlanmalı | 🟠 |
| NOT_A_LOAD | KNX cihazı (anahtar, termostat, sensör) aktüatör kanalına bağlanmaz | 🔴 |
| CHANNEL_DOUBLE | Bir kanala tek yük | 🔴 |
| LOAD_DOUBLE | Bir yük tek kanaldan beslenir | 🔴 |
| LOAD_UNCONNECTED | Kanala bağlanmamış yük var | 🟠 |
| BUS_INVALID | 230V yüke ve kollektör dolabına KNX bus bağlanmaz | 🔴 |
| BUS_RING | Bus kablosu ring oluşturamaz | 🔴 |
| BUS_UNCONNECTED | Bus ile panoya ulaşmayan KNX cihazı var | 🟠 |

Kablo Çekim Listesi (PDF): her enerji kablosu için pano/ürün/kanal → oda → yük → kesit;
her bus kablosu için düğümden düğüme. Kesitler ÖRNEKTİR (aydınlatma 3×1.5, perde 4×1.5,
bus 2×2×0.8 J-Y(St)Y); kesit ve sigortayı elektrikçi belirler.

## Ürün kataloğu ve kanal uyumu (v21) — kaynak: `catalog.py`
Her yükün BİRİNCİL kanal tipi vardır; birincil dolarsa izinli ALTERNATİF uyarıyla kullanılır.

| Yük | Birincil | Alternatif |
|---|---|---|
| Lamba, On/Off | Switch Aktüatör | — |
| Dim lamba | Dimmer Aktüatör | — (röleye bağlanırsa dim çalışmaz) |
| RGBW LED şerit | RGBW / LED Kontrol | — |
| DALI armatür | DALI Gateway (kontrol hattı) | — |
| Perde motoru | Jalüzi Aktüatörü | Röle 2 kanal (Yukarı/Aşağı) + kilitleme 🟠 |
| Termoelektrik vana (yerden ısıtma, kollektör) | Isıtma Aktüatörü | Röle 1 kanal 🟠 |
| Solenoid vana | Switch Aktüatör | — |
| Motorlu vana Aç/Kapa | Jalüzi Aktüatörü | Röle 2 kanal (Aç/Kapa) + kilitleme 🟠 |
| Motorlu vana 0-10V | Analog Aktüatör | — |
| Fancoil | Fancoil Aktüatörü | — |
| Split klima | KNX-AC Gateway (1 iç ünite) | — · enerji panodan DOĞRUDAN (ayrı sigorta) |
| VRF iç ünite | KNX-VRF Gateway (kapasite = kanal: 16 / 64) | — · enerji panodan DOĞRUDAN |

| Kod | Kural | Seviye |
|---|---|---|
| CHANNELS_MISSING | Bir yük tipi için birincil + alternatif kanallar yetmiyor | 🔴 |
| ALT_CHANNEL / ALT_ACTUATOR | Yük alternatif kanala yerleşti / bağlandı | 🟠 |

Klima ve VRF için Kablo Çekim Listesi'ne iki satır düşer: gateway → iç ünite **kontrol hattı**
ve panodan **doğrudan enerji** (ayrı sigorta). Tuş panellerinde (1/2/4/6/8) her tuşa bir grup adresi.
Grup adresi ana grupları: 1 Aydınlatma · 2 Perde · 3 Isıtma/HVAC · 4 Tuş/Sensör · 5 Genel Yükler · 6 Klima.

## Akubela ürünleri (v22)
Sol listede en üstte. Hypanel Elite 10, KeyPlus KS03, KNX Kasası PS51-KS41, Lux RT61, Pro, Supreme,
Ultra; Aura K32-B4 4 tuş (çoklu / tekli), Aura K32-M termostat (çoklu / tekli). Stok kodu olanlar katalogda.

Dahili röle çıkışı olanlar (Lux, Pro, Supreme, Ultra, PS51-KS41: 2 röle) odada **R1/R2** kanalı olarak
görünür; lamba / on-off / solenoid vana gibi röle yükleri doğrudan bunlara bağlanabilir ve röle
kapasitesine sayılır. Dim lamba bu rölelere bağlanamaz.
⚠️ Dahili röle yük akımı, bus akımı (varsayılan 10 mA) ve panel beslemesi datasheet'ten doğrulanmalı.

## Henüz yok (sonraki sürümler)
- Otomatik kanal ataması ("Otomatik bağla") — şimdilik kablolar elle çekiliyor
- Kombi, kapı otomasyonu; Akuvox / Akubela entegrasyonu (ürün bilgisi bekleniyor)
- Kablo mesafesi kontrolü
- `.knxproj` gerçek ETS'de **doğrulanmadı**
