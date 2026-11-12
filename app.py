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
_db_url = os.environ.get("DATABASE_URL", "sqlite:///knxdoit.db")
# Render/Heroku "postgres://" verir; SQLAlchemy "postgresql://" ister
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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

from knx_rules import check_project, build_gas  # noqa: E402

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
        Paragraph, Spacer, PageBreak
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

    res = check_project(data)
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
        Paragraph("KNXdoit v18 - KNX Sistem Özeti", title),
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
        "Röle (ihtiyaç/var)", "Dimmer", "Perde"
    ]]
    for ln in res["lines"]:
        rows.append([
            ln["line"], ln["floor"], ln["device_count"],
            f"{ln['bus_ma']} mA", f"{ln['required_ma']} mA",
            f"{ln['psu_ma']} mA" if ln["psu_count"] else "YOK",
            f"{ln['recommended_psu']} mA"
            if ln["recommended_psu"] else "Hattı böl",
            "{}/{}".format(*ln["relay"]),
            "{}/{}".format(*ln["dimmer"]),
            "{}/{}".format(*ln["blind"]),
        ])
    story.append(table(rows, [40, 90, 60, 65, 70, 70, 75, 95, 60, 60]))
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

    # ---------- Sayfa 2: Fiziksel adresler ----------
    story += [PageBreak(), Paragraph("Fiziksel Adresler", h2)]
    rows = [["Adres", "Kat / Hat", "Konum", "Cihaz", "Bus akımı"]]
    for p in res["physical_addresses"]:
        rows.append([
            p["address"], p["floor"], p["location"],
            p["name"], f"{p['ma']} mA"
        ])
    story.append(table(rows, [70, 120, 120, 300, 80], "#0F766E"))

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
<KNX xmlns="http://knx.org/xml/project/21" CreatedBy="KNXdoit" ToolVersion="v18">
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
            f'CreatedBy="KNXdoit" ToolVersion="v18">\n'
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
        "project.html"
    )


# --------------------------------
# API
# --------------------------------

@app.route("/healthz")
def healthz():
    # Render sağlık kontrolü: uygulama + veritabanı bağlantısı
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"ok": True, "db": "ok"})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "db": str(e)[:200]}), 503


@app.route("/api/save", methods=["POST"])
@login_required
def save_project():
    d = request.get_json(silent=True) or {}

    p = Project(
        user_id=current_user.id,
        name=d.get("project_name")
        or "KNXdoit Projesi",
        ets_version=d.get("ets_version")
        or "ETS6",
        data=json.dumps(
            d,
            ensure_ascii=False
        )
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
    res = check_project(
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
    return jsonify(check_project(
        request.get_json(silent=True) or {}
    ))


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
