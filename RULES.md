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

**v23 — Modüler Otomasyon bilgisi:**
- Dahili röleler **maks. 1 A** (≈230 W rezistif; LED sürücülerde ani akım nedeniyle daha az). Dahili
  röleye yük bağlanınca editör uyarır; Kablo Çekim Listesi'nde not olarak yazılır.
- Bus akımı **10 mA** (her Akubela cihazı).
- **Ekranlı tüm cihazlar 24V DC ayrı besleme ister** (Elite 10, KeyPlus, PS51-KS41, Lux, Pro, Supreme,
  Ultra). **Aura serisi (K32-B4, K32-M) istemez.** Katta 24V isteyen cihaz varken o katın panosunda
  `psu24` kategorisinde güç kaynağı yoksa **SUPPLY24_MISSING** hatası.
- **Hypanel Elite 10 (PH59) PoE ile de çalışır:** panoda 24V kaynak yoksa hata değil **POE_SUPPLY**
  uyarısı verilir; kablo listesinde "Network / PoE switch → Cat6 (PoE)" hattı yazılır.
- Katalog: 24V DC Güç Kaynağı 30 W / 60 W / 100 W. KNX bus cihazı değildir: fiziksel adres almaz,
  bus akımına sayılmaz.
- Kablo listesi her 24V cihaz için panodan "24V DC besleme" hattı (2×1.5) üretir.
- **24V güç kaynağı boyutlandırma:** toplam panel W × 1.3 ≥ kurulu 24V kaynak W; değilse **SUPPLY24_LOW**.
  Öneri 30 / 60 / 100 W; 100 W'ı aşarsa beslemeyi bölün.
  Değerler: Pro 10 W, PS51 5 W (datasheet). Elite 10 → 10 W, KeyPlus 5 W, Lux 5 W, Supreme 15 W,
  Ultra 10 W **tahmini** (datasheet bulunamadı).

## PDF: Kablo şeması ve tek hat şeması (v24 / v25)
- **Kablo Şeması:** editörde çizilen plan her kat için görüntü olarak PDF'e girer; altında o katın
  hata / uyarıları.
- **Tek Hat Şeması (pano başına):** ana besleme → ana şalter → kaçak akım 30 mA → bara; baradan
  her cihaz için sigorta → cihaz → kanal çıkışları (K1…, R1…, 24V, BUS) → oda / yük / kablo.
  Boş kanallar "yedek" olarak yazılır. Doğrudan beslenen klima / VRF ve oda panellerinin dahili
  röleleri (maks. 1 A) ilk panoya ayrı hat olarak çizilir.
- Önerilen sigortalar: KNX PS / 24V PS / gateway / ısıtma C6, röle C16, dimmer B10, perde / fancoil
  / RGBW C10, klima C16. **Öneridir**; elektrikçi belirler.

## Henüz yok (sonraki sürümler)
- Otomatik kanal ataması ("Otomatik bağla") — şimdilik kablolar elle çekiliyor
- Kombi, kapı otomasyonu; Akuvox / Akubela entegrasyonu (ürün bilgisi bekleniyor)
- Kablo mesafesi kontrolü
- `.knxproj` gerçek ETS'de **doğrulanmadı**
