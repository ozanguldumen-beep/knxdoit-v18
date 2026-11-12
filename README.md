# KNXdoit v18

Bayiler için KNX proje sihirbazı: kat/oda/pano tasarımı, KNX kural kontrolü,
elektrikçi PDF'i ve `.knxproj` çıktısı.

Kurallar: [RULES.md](RULES.md)

## Yerelde çalıştırma
```bash
pip install -r requirements.txt
python run.py          # http://127.0.0.1:5000
```

## Render
| Ayar | Değer |
|---|---|
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |
| Env | `SECRET_KEY` (güçlü rastgele değer), `DATABASE_URL` (kalıcı veri için PostgreSQL) |

SQLite (varsayılan) Render'da her deploy'da sıfırlanabilir; gerçek müşteri verisi için PostgreSQL kullanın.

## Dosya yapısı
```
app.py          Flask: kullanıcı, proje, PDF, .knxproj
knx_rules.py    KNX kural motoru (GA, fiziksel adres, PSU, kanallar)
run.py          yerel çalıştırma
templates/      HTML
static/         JS + CSS
fonts/          DejaVu (PDF'te Türkçe karakter)
```

## Durum
Test aşamasında. `.knxproj` dosyası gerçek ETS'de henüz doğrulanmadı.
