# KNXdoit v18 — Kural Listesi

Kodda karşılığı: `knx_rules.py`. Ekran, PDF ve `.knxproj` aynı hesaptan beslenir.
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

## Henüz yok (sonraki sürümler)
- Kahverengi enerji kablolarının çizimi, kanal numarası ataması
- Klima/kombi (panodan doğrudan besleme) cihaz tipi, RGBW, çok tuşlu anahtar seçenekleri
- Kablo mesafesi kontrolü
- `.knxproj` gerçek ETS'de **doğrulanmadı**
