from flask import (
    Flask, render_template, request, jsonify,
    send_file, redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from datetime import datetime, timedelta
import base64
from io import BytesIO
from xml.sax.saxutils import escape
import os
import json
import zipfile
import uuid

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "knxdoit-v18-development-only"
)
# Canlıda (REQUIRE_DATABASE_URL=1) DATABASE_URL yoksa uygulama
# BAŞLAMAZ: verilerin geçici bir SQLite dosyasına yazılıp
# kaybolmasını engeller.
if (
    os.environ.get("REQUIRE_DATABASE_URL") == "1"
    and not os.environ.get("DATABASE_URL")
):
    raise RuntimeError(
        "DATABASE_URL tanımlı değil. Render > Environment kısmına "
        "Postgres 'Internal Database URL' değerini ekleyin."
    )

_db_url = os.environ.get("DATABASE_URL", "sqlite:///knxdoit.db")
# Render "postgres://" ya da "postgresql://" verir. SQLAlchemy 2.1'de
# varsayılan sürücü psycopg (v3) oldu; biz psycopg2 kullanıyoruz, bu
# yüzden sürücüyü adresle açıkça belirtiyoruz.
for _prefix in ("postgres://", "postgresql://"):
    if _db_url.startswith(_prefix):
        _db_url = "postgresql+psycopg2://" + _db_url[len(_prefix):]
        break
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Veritabanı yeniden başlarsa (Render bakımı) ölü bağlantıyı kullanma:
# her bağlantı kullanılmadan önce kontrol edilir ve gerekirse yenilenir.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


# --------------------------------
# KULLANICI MODELİ
# --------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    plan = db.Column(
        db.String(50),
        default="trial"
    )

    trial_start = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    projects = db.relationship(
        "Project",
        backref="user",
        lazy=True
    )

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password, password
        )

    def is_trial_active(self):
        return (
            self.plan == "pro"
            or datetime.utcnow()
            < self.trial_start + timedelta(days=7)
        )

    def project_count(self):
        return len(self.projects)

    def can_create_project(self):
        return (
            self.plan == "pro"
            or (
                self.is_trial_active()
                and self.project_count() < 3
            )
        )

    def days_left(self):
        if self.plan == "pro":
            return 999

        delta = (
            self.trial_start + timedelta(days=7)
        ) - datetime.utcnow()

        return max(0, delta.days)


# --------------------------------
# PROJE MODELİ
# --------------------------------

class Project(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    ets_version = db.Column(
        db.String(10),
        default="ETS6"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    data = db.Column(
        db.Text,
        default="{}"
    )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --------------------------------
# KNX KURAL MOTORU (knx_rules.py)
# --------------------------------

from knx_rules import build_gas  # noqa: E402
from knx_wiring import analyze  # noqa: E402
from catalog import CATEGORY_LABEL, public_catalog  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# --------------------------------
# PDF OLUŞTURMA
# --------------------------------

_FONTS_READY = False


def _register_fonts():
    """Türkçe karakterler (ş, ğ, ı, İ) için DejaVu fontu."""
    global _FONTS_READY
    if _FONTS_READY:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fdir = os.path.join(BASE_DIR, "fonts")
    pdfmetrics.registerFont(
        TTFont("DejaVu", os.path.join(fdir, "DejaVuSans.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("DejaVu-Bold", os.path.join(fdir, "DejaVuSans-Bold.ttf"))
    )
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVu-Bold"
    )
    _FONTS_READY = True


def make_pdf(data):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, PageBreak, Image, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    _register_fonts()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        topMargin=28, bottomMargin=28,
        leftMargin=28, rightMargin=28
    )

    ss = getSampleStyleSheet()
    title = ParagraphStyle(
        "t", parent=ss["Title"], fontName="DejaVu-Bold"
    )
    h2 = ParagraphStyle(
        "h2", parent=ss["Heading2"], fontName="DejaVu-Bold"
    )
    normal = ParagraphStyle(
        "n", parent=ss["Normal"], fontName="DejaVu", fontSize=9
    )

    diagrams = (data or {}).pop("diagrams", None) or []
    editor_data = (data or {}).get("editor") or {}
    data, res = analyze(data)
    summary = res["summary"]
    pname = escape(data.get("project_name", "KNXdoit Projesi"))
    ets = escape(data.get("ets_version", "ETS6"))

    def table(rows, widths, head_color="#185FA5", extra=None):
        t = Table(rows, colWidths=widths, repeatRows=1)
        style = [
            ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
            ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(head_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        t.setStyle(TableStyle(style + (extra or [])))
        return t

    # ---------- Sayfa 1: KNX Sistem Özeti ----------
    status_text = {
        "error": "HATA VAR - proje bu haliyle uygulanmamalı",
        "warn": "UYARI VAR - kontrol edilmeli",
        "ok": "UYGUN",
    }[summary["status"]]

    story = [
        Paragraph("KNXdoit v23 - KNX Sistem Özeti", title),
        Paragraph(f"Proje: {pname} | ETS: {ets}", normal),
        Spacer(1, 8),
        Paragraph(
            f"<b>Proje sağlığı:</b> {status_text} "
            f"({summary['errors']} hata, {summary['warnings']} uyarı)",
            normal
        ),
        Spacer(1, 10),
        Paragraph("Hatlar ve Power Supply", h2),
    ]

    rows = [[
        "Hat", "Kat", "Bus cihazı", "Bus akımı",
        "+%30 rezerv", "Mevcut PS", "Önerilen PS",
        "Kanallar (ihtiyaç / mevcut)"
    ]]
    for ln in res["lines"]:
        rows.append([
            ln["line"], ln["floor"], ln["device_count"],
            f"{ln['bus_ma']} mA", f"{ln['required_ma']} mA",
            f"{ln['psu_ma']} mA" if ln["psu_count"] else "YOK",
            f"{ln['recommended_psu']} mA"
            if ln["recommended_psu"] else "Hattı böl",
            Paragraph(escape(" · ".join(
                [f"{CATEGORY_LABEL.get(c, c)} {n}/{h}"
                 for c, (n, h) in (ln.get("channels") or {}).items()]
                + ([f"24V: {ln.get('supply24')} ekran"
                    + (f", {ln['w24']} W (+%30 = {ln['w24_required']} W) / kurulu {ln['w24_installed']} W"
                       if ln.get("w24") else " (PoE / kaynak yok)")]
                   if ln.get("supply24") else [])
            ) or "—"), normal),
        ])
    story.append(table(rows, [40, 85, 55, 60, 65, 60, 65, 300]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "mA değerleri varsayılandır; kesin hesap için ürün "
        "datasheet değerleri kullanılmalıdır.", normal
    ))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Kural Kontrolü", h2))
    if res["issues"]:
        rows = [["Durum", "Kural", "Açıklama"]]
        extra = []
        for i, iss in enumerate(res["issues"], start=1):
            is_err = iss["level"] == "error"
            rows.append([
                "HATA" if is_err else "UYARI",
                iss["code"],
                Paragraph(escape(iss["message"]), normal),
            ])
            extra.append((
                "TEXTCOLOR", (0, i), (0, i),
                colors.HexColor("#B91C1C" if is_err else "#B45309")
            ))
        story.append(table(rows, [50, 110, 570], extra=extra))
    else:
        story.append(Paragraph("Tüm kontroller uygun.", normal))

    def issue_block(issues, heading):
        if not issues:
            return [Paragraph(f"<b>{heading}:</b> uygun, hata / uyarı yok.", normal)]
        rows = [["Durum", "Açıklama"]]
        extra = []
        for i, iss in enumerate(issues, start=1):
            is_err = iss["level"] == "error"
            rows.append(["HATA" if is_err else "UYARI", Paragraph(escape(iss["message"]), normal)])
            extra.append(("TEXTCOLOR", (0, i), (0, i),
                          colors.HexColor("#B91C1C" if is_err else "#B45309")))
        return [Paragraph(f"<b>{heading}</b>", normal), Spacer(1, 3),
                table(rows, [50, 736], "#7C2D12", extra=extra)]

    # ---------- Sayfa: Kablo Şeması (editörde çizilen plan) ----------
    for dg in diagrams[:12]:
        try:
            raw = str(dg.get("png", ""))
            if not raw.startswith("data:image/png;base64,") or len(raw) > 12_000_000:
                continue
            img_bytes = base64.b64decode(raw.split(",", 1)[1])
            fname = str(dg.get("floor", ""))
            w, h = float(dg.get("w") or 1), float(dg.get("h") or 1)
            # bu katın adı, odaları veya panoları geçen hata/uyarılar
            keys = [k for k in [fname, *(dg.get("names") or [])] if k]
            if len(diagrams) <= 1:
                f_issues = res["issues"]
            else:
                f_issues = [i for i in res["issues"] if any(k in i["message"] for k in keys)]
            # şema + uyarılar aynı sayfaya sığsın
            rows_h = sum(14 + 11 * (len(i["message"]) // 150) for i in f_issues) + 34 if f_issues else 16
            max_w, max_h = 786, max(200, 455 - rows_h)
            k = min(max_w / w, max_h / h)
            img = Image(BytesIO(img_bytes), width=w * k, height=h * k)
            story += [
                PageBreak(),
                Paragraph(f"Kablo Şeması — {escape(fname)}", h2),
                Paragraph(
                    '<font color="#8B4513"><b>━━</b></font> Enerji (230V) &nbsp;&nbsp; '
                    '<font color="#16a34a"><b>━━</b></font> KNX bus &nbsp;&nbsp; '
                    '<font color="#0284c7"><b>╍╍</b></font> Gateway kontrol hattı', normal),
                Spacer(1, 4), img, Spacer(1, 6),
            ]
            story += issue_block(f_issues, f"{escape(fname)} — Hatalar ve uyarılar")
        except Exception:
            app.logger.exception("Kablo şeması PDF'e eklenemedi")

    # ---------- Sayfa: Tek hat şeması (pano başına) ----------
    if editor_data.get("floors"):
        try:
            from single_line import single_line_story
            story += single_line_story(editor_data, res, h2, normal)
        except Exception:
            app.logger.exception("Tek hat şeması PDF'e eklenemedi")

    # ---------- Sayfa 2: Fiziksel adresler ----------
    story += [PageBreak(), Paragraph("Fiziksel Adresler", h2)]
    rows = [["Adres", "Kat / Hat", "Konum", "Cihaz", "Bus akımı"]]
    for p in res["physical_addresses"]:
        rows.append([
            p["address"], p["floor"], p["location"],
            p["name"], f"{p['ma']} mA"
        ])
    story.append(table(rows, [70, 120, 120, 300, 80], "#0F766E"))

    # ---------- Sayfa: Kablo Çekim Listesi ----------
    if res.get("cables"):
        story += [PageBreak(), Paragraph("Kablo Çekim Listesi", h2)]
        notes = []
        if any("dahili röle" in (c.get("from") or "") for c in res["cables"]):
            notes.append("Panel dahili röleleri maks. 1 A — LED / sürücülü yükte ani akım nedeniyle daha düşük yük bağlayın.")
        if any(c.get("line") == "24V DC besleme" for c in res["cables"]):
            notes.append("24V DC besleme hatları 2×1.5 çekilmeli; uzun hatlarda gerilim düşümünü kontrol edin, KNX bus kablosu ile karıştırmayın.")
        if any(c.get("line") == "PoE besleme + data" for c in res["cables"]):
            notes.append("PoE ile beslenen paneller için switch portu PoE (802.3af/at) olmalı; Cat6 çekin.")
        if res["issues"]:
            notes.append(f"Projede {summary['errors']} hata, {summary['warnings']} uyarı var — "
                         "ayrıntı aşağıda; hatalar giderilmeden uygulamaya geçmeyin.")
        if notes:
            story.append(Paragraph("<b>⚠ Dikkat</b><br/>" + "<br/>".join("• " + escape(n) for n in notes), normal))
            story.append(Spacer(1, 6))
        if res["issues"]:
            story += issue_block(res["issues"], "Hatalar ve uyarılar")
            story.append(Spacer(1, 8))
        rows = [[
            "Kat", "Pano çıkışı", "Gittiği yer", "Yük",
            "Kablo", "Hat türü", "Not"
        ]]
        small = ParagraphStyle("sm", parent=normal, fontSize=7.5, leading=9)
        extra = []
        for i, c in enumerate(res["cables"], start=1):
            rows.append([
                c["floor"],
                Paragraph(escape(c["from"]), normal),
                Paragraph(escape(c["to"]), normal),
                Paragraph(escape(c["load"]), normal),
                Paragraph(escape(c["cable"]), normal),
                c["line"],
                Paragraph(escape(c.get("note") or ""), small),
            ])
            extra.append((
                "TEXTCOLOR", (5, i), (5, i),
                colors.HexColor(
                    "#15803D" if c["kind"] == "bus" else "#8B4513"
                )
            ))
        story.append(table(
            rows, [55, 170, 110, 115, 80, 85, 171], "#8B4513", extra
        ))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "Kablo kesitleri örnektir; kesit ve sigortayı devrenin "
            "yüküne ve yönetmeliğe göre elektrikçi belirler. KNX bus "
            "kablosu 230V hatlarından ayrı güzergâhtan çekilir, ring "
            "yapılmaz.", normal
        ))

    # ---------- Sayfa 3: Grup adresleri ----------
    story += [PageBreak(), Paragraph("Grup Adresleri", h2)]
    rows = [[
        "Grup Adresi", "Fonksiyon", "Kat", "Oda",
        "Cihaz", "Nesne", "DPT"
    ]]
    for g in res["group_addresses"]:
        rows.append([
            g["address"], g["main_name"], g["floor"], g["room"],
            g["device"], g["function"], g["dpt"]
        ])
    story.append(table(rows, [70, 95, 90, 100, 150, 120, 80]))

    doc.build(story)
    buf.seek(0)
    return buf


# --------------------------------
# KNX PROJE DIŞA AKTARMA
# --------------------------------

def attr(value):
    # XML attribute icin: & < > ile birlikte " ve ' de kacirilir
    return escape(
        str(value),
        {'"': "&quot;", "'": "&apos;"}
    )


def make_knxproj(data):
    """ETS uyumluluğu henüz gerçek ETS'de DOĞRULANMADI."""
    data, _ = analyze(data)
    gas, _ = build_gas(data)
    floors = data.get("floors", []) or []

    pid = "P-" + uuid.uuid4().hex[:4].upper()
    project_name = data.get("project_name", "KNXdoit Projesi")

    puid = [0]

    def next_puid():
        puid[0] += 1
        return puid[0]

    # Topoloji: Alan 1, her kat bir hat
    lines_xml = "\n".join(
        f'          <Line Id="{pid}-0_A-1_L-{i + 1}" '
        f'Address="{i + 1}" Name="{attr(f.get("name", "Kat"))}" '
        f'Puid="{next_puid()}"/>'
        for i, f in enumerate(floors[:15])
    )

    # Grup adresleri: Ana grup -> Orta grup -> Adres
    tree = {}
    for g in gas:
        tree.setdefault(
            (g["main"], g["main_name"]), {}
        ).setdefault(
            (g["middle"], g["floor"]), []
        ).append(g)

    ranges = []
    ga_no = 0
    for (main, main_name), middles in sorted(tree.items()):
        inner = []
        for (middle, floor_name), items in sorted(middles.items()):
            start = (main << 11) | (middle << 8)
            addrs = []
            for g in items:
                ga_no += 1
                name = f'{g["room"]} {g["device"]} {g["function"]}'
                addrs.append(
                    f'                <GroupAddress '
                    f'Id="{pid}-0_GA-{ga_no}" '
                    f'Address="{g["int"]}" '
                    f'Name="{attr(name)}" '
                    f'DatapointType="{g["dpt"]}" '
                    f'Puid="{next_puid()}"/>'
                )
            inner.append(
                f'              <GroupRange Id="{pid}-0_GR-{main}-{middle}" '
                f'RangeStart="{start}" RangeEnd="{start + 255}" '
                f'Name="{attr(floor_name)}" Puid="{next_puid()}">\n'
                + "\n".join(addrs) +
                "\n              </GroupRange>"
            )
        mstart = main << 11
        ranges.append(
            f'            <GroupRange Id="{pid}-0_GR-{main}" '
            f'RangeStart="{mstart}" RangeEnd="{mstart + 2047}" '
            f'Name="{attr(main_name)}" Puid="{next_puid()}">\n'
            + "\n".join(inner) +
            "\n            </GroupRange>"
        )

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<KNX xmlns="http://knx.org/xml/project/21" CreatedBy="KNXdoit" ToolVersion="v19">
  <Project Id="{pid}">
    <Installations>
      <Installation Name="{attr(project_name)}" GroupAddressStyle="ThreeLevel">
        <Topology>
          <Area Id="{pid}-0_A-1" Address="1" Name="Alan 1" Puid="{next_puid()}">
{lines_xml}
          </Area>
        </Topology>
        <GroupAddresses>
          <GroupRanges>
{chr(10).join(ranges)}
          </GroupRanges>
        </GroupAddresses>
      </Installation>
    </Installations>
  </Project>
</KNX>"""

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{pid}/0.xml", xml)
        z.writestr(
            f"{pid}/project.xml",
            f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<KNX xmlns="http://knx.org/xml/project/21" '
            f'CreatedBy="KNXdoit" ToolVersion="v19">\n'
            f'  <Project Id="{pid}">\n'
            f'    <ProjectInformation Name="{attr(project_name)}"/>\n'
            f'  </Project>\n</KNX>'
        )
    buf.seek(0)
    return buf

# --------------------------------
# SAYFALAR
# --------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    projects = Project.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Project.created_at.desc()
    ).all()

    return render_template(
        "dashboard.html",
        projects=projects
    )


@app.route("/project")
@login_required
def project():
    return redirect(
        url_for("new_project")
    )


@app.route("/project/new")
@login_required
def new_project():
    if not current_user.can_create_project():
        flash(
            "Trial süreniz doldu veya "
            "proje limitine ulaştınız."
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "project.html",
        project_id=None,
        saved=None
    )


@app.route("/project/<int:project_id>")
@login_required
def open_project(project_id):
    p = Project.query.filter_by(
        id=project_id, user_id=current_user.id
    ).first_or_404()

    try:
        saved = json.loads(p.data or "{}")
    except ValueError:
        saved = {}

    return render_template(
        "project.html",
        project_id=p.id,
        saved=saved
    )


# --------------------------------
# API
# --------------------------------

@app.route("/api/catalog")
def catalog():
    # Editör ürün listesini buradan alır (tek kaynak: catalog.py)
    return jsonify(public_catalog())


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/healthz")
def healthz():
    # Render sağlık kontrolü: uygulama + veritabanı bağlantısı
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({
            "ok": True,
            "db": "ok",
            "engine": db.engine.dialect.name
        })
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "db": str(e)[:200]}), 503


@app.route("/api/save", methods=["POST"])
@login_required
def save_project():
    d = request.get_json(silent=True) or {}
    project_id = d.pop("project_id", None)

    name = (d.get("project_name") or "KNXdoit Projesi")[:200]
    ets = (d.get("ets_version") or "ETS6")[:10]
    payload = json.dumps(d, ensure_ascii=False)

    if project_id:
        # Var olan projeyi güncelle (yalnızca sahibi)
        p = Project.query.filter_by(
            id=int(project_id), user_id=current_user.id
        ).first()
        if not p:
            return jsonify({"ok": False, "error": "Proje bulunamadı"}), 404
        p.name, p.ets_version, p.data = name, ets, payload
    else:
        if not current_user.can_create_project():
            return jsonify({
                "ok": False,
                "error": "Trial süreniz doldu veya proje limitine ulaştınız."
            }), 403
        p = Project(
            user_id=current_user.id,
            name=name, ets_version=ets, data=payload
        )
        db.session.add(p)

    db.session.commit()

    return jsonify({
        "ok": True,
        "id": p.id
    })


@app.route("/api/preview", methods=["POST"])
@login_required
def preview():
    _, res = analyze(
        request.get_json(silent=True) or {}
    )

    return jsonify({
        "ok": True,
        "total": len(res["group_addresses"]),
        **res
    })


@app.route("/api/check", methods=["POST"])
@login_required
def check():
    _, res = analyze(request.get_json(silent=True) or {})
    return jsonify(res)


@app.route("/api/pdf", methods=["POST"])
@login_required
def pdf():
    d = request.get_json(silent=True) or {}

    return send_file(
        make_pdf(d),
        as_attachment=True,
        download_name="knxdoit_elektrikci.pdf",
        mimetype="application/pdf"
    )


@app.route("/api/generate", methods=["POST"])
@login_required
def generate():
    d = request.get_json(silent=True) or {}

    return send_file(
        make_knxproj(d),
        as_attachment=True,
        download_name="knxdoit.knxproj",
        mimetype="application/octet-stream"
    )


# --------------------------------
# KULLANICI GİRİŞİ
# --------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(
            url_for("new_project")
        )

    if request.method == "POST":
        u = User.query.filter_by(
            email=request.form.get("email")
        ).first()

        if u and u.check_password(
            request.form.get("password", "")
        ):
            login_user(u)

            return redirect(
                url_for("new_project")
            )

        flash("Hatalı email veya şifre")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(
            url_for("new_project")
        )

    if request.method == "POST":
        email = request.form.get(
            "email", ""
        ).strip().lower()

        if User.query.filter_by(
            email=email
        ).first():
            flash("Bu email zaten kayıtlı")

            return redirect(
                url_for("register")
            )

        u = User(email=email)

        u.set_password(
            request.form.get("password", "")
        )

        db.session.add(u)
        db.session.commit()

        login_user(u)

        return redirect(
            url_for("new_project")
        )

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()

    return redirect(
        url_for("index")
    )


# --------------------------------
# VERİTABANI BAŞLATMA
# --------------------------------

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
