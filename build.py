#!/usr/bin/env python3
"""Statischer Generator für wuermtalaerzte.de.

Liest data/daten.json, kopiert public/ nach dist/ und erzeugt alle HTML-Seiten.
Keine externen Abhängigkeiten (nur Python-Standardbibliothek).

Umgebungsvariablen:
  SITE_URL   Absolute Basis-URL für Canonical/Sitemap (Standard: https://www.wuermtalaerzte.de)
  BASE_PATH  Pfad, unter dem die Seite ausgeliefert wird (Standard: "/"; GitHub-Pages-Projektseite: "/repo/")
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SITE_URL = os.environ.get("SITE_URL", "https://www.wuermtalaerzte.de").rstrip("/")
BASE_PATH = os.environ.get("BASE_PATH", "/")
if not BASE_PATH.endswith("/"):
    BASE_PATH += "/"
TODAY = dt.date.today().isoformat()
DATA_STAND = "22.11.2023"
# Karte nur nach Einwilligung (siehe public/assets/js/consent.js); Marker ungefähr am Bahnhof Gauting
OSM_EMBED = ("https://www.openstreetmap.org/export/embed.html?bbox=11.3715%2C48.0655%2C11.3825%2C48.0725"
             "&layer=mapnik&marker=48.0690%2C11.3770")
OSM_LINK = "https://www.openstreetmap.org/search?query=Bahnhofplatz%203%2C%2082131%20Gauting"

esc = html.escape

# --------------------------------------------------------------------------- Daten

ORT_SLUG = {
    "Gauting": "gauting", "Germering": "germering", "Gräfelfing": "graefelfing",
    "Krailling": "krailling", "Lochham": "lochham", "Martinsried": "martinsried",
    "Neuried": "neuried", "Planegg": "planegg", "Stockdorf": "stockdorf",
}
# (slug, Label, Icon, Muster); Reihenfolge = Priorität für das Haupt-Icon
FACHGEBIETE = [
    ("kardiologie", "Kardiologie", "kardio", r"kardiolog"),
    ("pneumologie", "Pneumologie", "lunge", r"pneumolog"),
    ("gynaekologie", "Gynäkologie", "gyn", r"gynäkolog|frauenheilkunde"),
    ("urologie", "Urologie", "uro", r"urolog"),
    ("hno", "Hals-Nasen-Ohren", "hno", r"hals-nasen|\bhno\b"),
    ("augenheilkunde", "Augenheilkunde", "augen", r"augenheil"),
    ("dermatologie", "Dermatologie & Allergologie", "haut", r"dermatolog|hautheil|allergolog"),
    ("neurologie", "Neurologie", "neuro", r"neurolog|neurochirurg"),
    ("kinder", "Kinder & Jugend", "kinder", r"kinder"),
    ("orthopaedie", "Orthopädie & Chirurgie", "ortho", r"orthop|chirurg|unfall|bewegungsapparat"),
    ("schmerz-rheuma", "Schmerz & Rheuma", "schmerz", r"schmerz|rheuma"),
    ("komplementaer", "Naturheil- & Japanische Medizin", "komplement", r"naturheil|japanische"),
    ("innere", "Innere Medizin", "innere", r"innere medizin|gastroenter|endokrin|diabet"),
    ("allgemein", "Allgemein- & Hausarzt", "allgemein", r"allgemeinmedizin|praktische medizin|hausärztl"),
]
FACH_BY_SLUG = {f[0]: f for f in FACHGEBIETE}

VORSTAND_ICON = {"Vorsitz": "V", "Stellvertretung und Schriftführung": "S", "Stellvertretung": "S", "Kassenführung": "K"}

ZIELE = [
    ("quality", "Qualität in der Versorgung", "Unterstützung einer qualitätsorientierten medizinischen Versorgung im Würmtal."),
    ("learn", "Austausch & Fortbildung", "Fachlicher Austausch und Fortbildungen für Ärztinnen und Ärzte der Region."),
    ("people", "Gesundheitsinformation", "Information für Bürgerinnen und Bürger rund um Gesundheit und Versorgung."),
    ("care", "Netzwerk der Versorger", "Zusammenarbeit mit Pflege-, Sozial- und Gesundheitsdiensten vor Ort."),
    ("duty", "Ambulante Versorgung", "Mitwirkung an der ambulanten Versorgung und am ärztlichen Bereitschaftsdienst."),
    ("voice", "Gemeinsame Interessen", "Vertretung gemeinsamer beruflicher Belange der Mitglieder."),
]


def fach_slugs(text: str) -> list[str]:
    t = text.lower()
    return [s for s, _, _, rx in FACHGEBIETE if re.search(rx, t)]


def main_icon(slugs: list[str]) -> str:
    return FACH_BY_SLUG[slugs[0]][2] if slugs else "weitere"


def split_fach(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r",\s*(?![^()]*\))", text) if p.strip()]
    return parts[:6] if len(parts) > 1 else [text]


def url_web(w: str) -> str:
    return w if w.startswith("http") else "https://" + w


def web_label(w: str) -> str:
    return re.sub(r"^https?://", "", w).rstrip("/")


def phone_items(s: str) -> list[tuple[str, str]]:
    """Gibt (Anzeige, tel:-Wert) zurück. Nummern ohne Vorwahl gelten für 089."""
    s = s.strip()
    if not s:
        return []
    if s.startswith("0176"):
        return [("0176 21 28 49 08", "+4917621284908")]
    if s.startswith("89 / "):
        d = re.sub(r"\D", "", s[5:])
        return [("089 " + s[5:].replace(" - ", "-"), "+4989" + d)]
    out = []
    for part in s.split(" / "):
        d = re.sub(r"\D", "", part)
        out.append(("089 " + part.strip(), "+4989" + d))
    return out


def tel_from_profile(s: str) -> str:
    """'089 / 85 35 36' -> '+498985 3536' (nur erste Nummer)."""
    parts = [p.strip() for p in s.split("/")]
    if len(parts) >= 2 and re.fullmatch(r"0\d+", parts[0]):
        return "+49" + parts[0][1:] + re.sub(r"\D", "", parts[1])
    return "+49" + re.sub(r"\D", "", parts[0]).lstrip("0")


data = json.loads((ROOT / "data" / "daten.json").read_text(encoding="utf-8"))
entries: list[dict] = []
for ort, lst in data["orte"].items():
    for e in lst:
        e = dict(e, ort=ort)
        e["slugs"] = fach_slugs(e["fachrichtung"])
        entries.append(e)

profiles: dict[str, list[dict]] = {}
for p in data["profile"]:
    parts = p["pfad"].split("/")
    profiles.setdefault(parts[-2], []).append(dict(p, file=parts[-1]))
for d in profiles.values():
    d.sort(key=lambda p: p["file"])


def profile_main(slug: str) -> dict | None:
    d = profiles.get(slug)
    if not d:
        return None
    for p in d:
        if p["file"] == slug + ".htm":
            return p
    return d[0]


listed_profile_dirs = {e["profil_alt"] for e in entries if e["profil_alt"]}
by_ort = {o: [e for e in entries if e["ort"] == o] for o in ORT_SLUG}
fach_counts = {s: sum(1 for e in entries if s in e["slugs"]) for s, *_ in FACHGEBIETE}

# --------------------------------------------------------------------------- HTML-Bausteine


def icon(name: str, root: str, cls: str = "") -> str:
    return (f'<svg class="icon {cls}" aria-hidden="true" focusable="false">'
            f'<use href="{root}assets/icons.svg#i-{name}"/></svg>')


def brand_mark(root: str) -> str:
    return (f'<img class="brand-logo" src="{root}assets/img/logo-avw.png" width="64" height="29" alt="AVW">'
            '<span class="brand-text"><span class="brand-name">Würmtal Ärzte</span>'
            '<span class="brand-sub">Ärzteverein im Würmtal e.V.</span></span>')


def head(title: str, desc: str, root: str, path: str, noindex: bool = False, abs_assets: bool = False) -> str:
    a = BASE_PATH if abs_assets else root
    canon = f"{SITE_URL}/{path}" if path != "index.html" else f"{SITE_URL}/"
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#2e4b38">
<meta name="color-scheme" content="light dark">
{robots}
<link rel="canonical" href="{canon}">
<link rel="icon" href="{a}favicon.png" type="image/png" sizes="64x64">
<link rel="apple-touch-icon" href="{a}apple-touch-icon.png">
<link rel="manifest" href="{a}site.webmanifest">
<meta property="og:type" content="website">
<meta property="og:locale" content="de_DE">
<meta property="og:site_name" content="Würmtal Ärzte">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE_URL}/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="{a}assets/fonts/playfair-display-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{a}assets/css/main.css">
</head>
<body>
<a class="skip" href="#main">Zum Inhalt springen</a>
"""


def header(root: str, active: str = "") -> str:
    def a(href: str, label: str, key: str) -> str:
        cur = ' aria-current="page"' if active == key else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    return f"""<header class="site-header">
<div class="wrap bar">
<a class="brand" href="{root}index.html" aria-label="Würmtal Ärzte – Startseite">{brand_mark(root)}</a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav">Menü</button>
<nav class="nav" id="site-nav" aria-label="Hauptnavigation">
{a(root + "aerzte.html", "Ärzte finden", "aerzte")}
{a(root + "index.html#fachgebiete", "Fachgebiete", "")}
{a(root + "index.html#orte", "Orte", "")}
{a(root + "index.html#verein", "Verein", "")}
{a(root + "index.html#kontakt", "Kontakt", "")}
<a class="btn" href="{root}aerzte.html">Arzt suchen {icon("arrow", root, "sm")}</a>
</nav>
</div>
</header>
"""


def consent_markup(root: str) -> str:
    return f"""<div class="consent" id="consent" role="region" aria-label="Datenschutz-Einstellungen" hidden>
<h2>Ihre Privatsphäre</h2>
<p>Diese Website setzt keine Cookies und kein Tracking ein. Nur mit Ihrer Einwilligung laden wir externe Inhalte nach, zum Beispiel die Karte von OpenStreetMap. Dabei wird Ihre IP-Adresse an den Anbieter übertragen. Mehr dazu in der <a href="{root}htm/datenschutz.html">Datenschutzerklärung</a> und im <a href="{root}htm/avw_impressum.htm">Impressum</a>.</p>
<div class="consent-actions">
<button type="button" class="btn" data-consent-action="accept">Alle akzeptieren</button>
<button type="button" class="btn" data-consent-action="reject">Nur notwendige</button>
<button type="button" class="btn outline" data-consent-action="settings">Einstellungen</button>
</div>
</div>
<div class="consent-modal" id="consent-modal" hidden>
<div class="consent-dialog" role="dialog" aria-modal="true" aria-labelledby="consent-title">
<h2 id="consent-title">Datenschutz-Einstellungen</h2>
<p>Sie entscheiden, welche Inhalte geladen werden. Ihre Auswahl können Sie jederzeit über „Cookie-Einstellungen“ im Seitenfuß ändern oder widerrufen.</p>
<div class="consent-cat">
<h3>Notwendig</h3>
<label class="switch"><input type="checkbox" name="necessary" checked disabled>Immer aktiv</label>
<p>Speichert ausschließlich Ihre Auswahl auf diesem Gerät, damit die Abfrage nicht bei jedem Besuch erscheint. Es werden keine Cookies gesetzt.</p>
<dl><div><dt>Speicherort</dt><dd>localStorage Ihres Browsers (Schlüssel „avw-consent“)</dd></div><div><dt>Dauer</dt><dd>6 Monate</dd></div></dl>
</div>
<div class="consent-cat">
<h3>Externe Inhalte</h3>
<label class="switch"><input type="checkbox" name="external">Erlauben</label>
<p>Lädt die Karte von OpenStreetMap im Kontaktbereich. Dabei erhält der Anbieter Ihre IP-Adresse und technische Browserdaten.</p>
<dl><div><dt>Anbieter</dt><dd>OpenStreetMap Foundation, Vereinigtes Königreich</dd></div><div><dt>Zweck</dt><dd>Anfahrtskarte zur Geschäftsstelle</dd></div><div><dt>Rechtsgrundlage</dt><dd>Einwilligung (Art. 6 Abs. 1 lit. a DSGVO, § 25 Abs. 1 TDDDG)</dd></div></dl>
</div>
<div class="consent-actions">
<button type="button" class="btn" data-consent-action="save">Auswahl speichern</button>
<button type="button" class="btn" data-consent-action="accept">Alle akzeptieren</button>
<button type="button" class="btn outline" data-consent-action="reject">Nur notwendige</button>
</div>
</div>
</div>"""


def footer(root: str) -> str:
    orte = "".join(f'<li><a href="{root}htm/aerzte_{ORT_SLUG[o]}.htm">{o}</a></li>' for o in ORT_SLUG)
    return f"""<footer class="site-footer">
<div class="wrap footer-grid">
<div>
<a class="brand" href="{root}index.html">{brand_mark(root)}</a>
<p>Das Verzeichnis der Ärztinnen und Ärzte in Gauting, Germering, Gräfelfing, Krailling, Lochham, Martinsried, Neuried, Planegg und Stockdorf.</p>
</div>
<div><h4>Orte</h4><ul class="cols">{orte}</ul></div>
<div><h4>Seiten</h4><ul>
<li><a href="{root}aerzte.html">Ärzte finden</a></li>
<li><a href="{root}index.html#fachgebiete">Fachgebiete</a></li>
<li><a href="{root}index.html#verein">Über den Verein</a></li>
<li><a href="{root}htm/avw_impressum.htm">Impressum</a></li>
<li><a href="{root}htm/datenschutz.html">Datenschutz</a></li>
<li><button type="button" class="linklike" data-consent-open>Cookie-Einstellungen</button></li>
</ul></div>
</div>
<div class="wrap footer-base"><span>© {dt.date.today().year} Ärzteverein im Würmtal e.V.</span><span>Arztangaben: Stand der bisherigen Website {DATA_STAND}</span></div>
</footer>
{consent_markup(root)}
<script src="{root}assets/js/main.js" defer></script>
<script src="{root}assets/js/consent.js" defer></script>
</body>
</html>
"""


def page(title, desc, root, path, body, active="", noindex=False, abs_assets=False) -> str:
    hd = head(title, desc, root, path, noindex, abs_assets)
    return hd + header(root, active) + f'<main id="main">\n{body}\n</main>\n' + footer(root)


def page_head(root, crumbs, h1, lead="", bg_word=""):
    cs = ""
    for i, (label, href) in enumerate(crumbs):
        if i:
            cs += '<span aria-hidden="true">/</span>'
        cs += f'<a href="{href}">{esc(label)}</a>' if href else f"<span>{esc(label)}</span>"
    bg = ""
    lead_html = f"<p>{lead}</p>" if lead else ""
    return f'<section class="page-head">{bg}<div class="wrap"><nav class="crumbs" aria-label="Brotkrumen">{cs}</nav><h1>{h1}</h1>{lead_html}</div></section>'


def card(e: dict, root: str) -> str:
    slugs = e["slugs"]
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in split_fach(e["fachrichtung"]))
    adr = e["adresse"] if re.search(r"\d{5}", e["adresse"]) else f'{e["adresse"]}, {e["ort"]}'
    li = [f'<li>{icon("pin", root, "sm")}<span>{esc(adr)}</span></li>']
    for disp, tel in phone_items(e["telefon"]):
        li.append(f'<li>{icon("phone", root, "sm")}<a href="tel:{tel}">{esc(disp)}</a></li>')
    if e["webseite"]:
        w = e["webseite"]
        li.append(f'<li>{icon("globe", root, "sm")}<a href="{esc(url_web(w))}" target="_blank" rel="noopener noreferrer">{esc(web_label(w))}</a></li>')
    foot = f'<span class="ort-badge">{esc(e["ort"])}</span>'
    pm = profile_main(e["profil_alt"]) if e["profil_alt"] else None
    if pm:
        foot += f'<a href="{root}{pm["pfad"]}">Praxisprofil {icon("arrow", root, "sm")}</a>'
    text = " ".join([e["name"], e["fachrichtung"], adr, e["ort"]])
    return (f'<article class="card" data-ort="{ORT_SLUG[e["ort"]]}" data-fach="{" ".join(slugs)}" data-text="{esc(text)}">'
            f'<div class="card-top"><div class="card-icon">{icon(main_icon(slugs), root)}</div>'
            f'<div><h3>{esc(e["name"])}</h3><div class="tags">{tags}</div></div></div>'
            f'<ul>{"".join(li)}</ul><div class="card-foot">{foot}</div></article>')


# --------------------------------------------------------------------------- Seiten


def build_index() -> str:
    root = ""
    maxn = max(len(v) for v in by_ort.values())
    fach_tiles = ""
    for s, lbl, ic, _ in FACHGEBIETE:
        n = fach_counts[s]
        if not n:
            continue
        fach_tiles += (f'<a class="fach" href="aerzte.html#{s}">{icon(ic, root, "bg-icon")}'
                       f'<div class="fach-txt"><h3>{esc(lbl)}</h3><small>{n} {"Eintrag" if n == 1 else "Einträge"}</small></div></a>')
    fach_tiles += (f'<a class="fach cta" href="aerzte.html"><div><h3>Alle {len(entries)} Praxen ansehen</h3>'
                   f'<small>Zur Arztsuche</small></div>{icon("arrow", root, "arrow")}</a>')
    orte_rows = ""
    for o in ORT_SLUG:
        n = len(by_ort[o])
        orte_rows += (f'<a class="ort" href="htm/aerzte_{ORT_SLUG[o]}.htm" style="--n:{n};--max:{maxn}">'
                      f'<span class="name">{o}</span><span class="meter" aria-hidden="true"><i></i></span>'
                      f'<span class="count">{n} {"Praxis" if n == 1 else "Praxen"}</span>{icon("arrow", root)}</a>')
    ziele = "".join(f'<div class="ziel">{icon(ic, root)}<h3>{esc(t)}</h3><p>{esc(d)}</p></div>' for ic, t, d in ZIELE)
    vorstand = ""
    for v in data["vorstand"]:
        name = v["name"]
        ini = re.sub(r"^((Priv\.-Doz\.|Dr\. med\.|Dr\.)\s*)+", "", name)[:1]
        vorstand += (f'<div class="person">'
                     f'<span class="role">{esc(v["amt"])}</span><strong>{esc(name)}</strong>'
                     f'<span class="sub">{esc(v["fachrichtung"])}</span></div>')
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "Organization",
        "name": "Ärzteverein im Würmtal e.V.", "url": SITE_URL + "/",
        "address": {"@type": "PostalAddress", "streetAddress": "Bahnhofplatz 3", "postalCode": "82131",
                    "addressLocality": "Gauting", "addressCountry": "DE"},
        "telephone": "+49 89 857 1057",
    }, ensure_ascii=False)
    body = f"""<section class="hero">
<div class="hero-bg" aria-hidden="true"></div>
<div class="wrap hero-inner">
<span class="eyebrow">Ärzteverein im Würmtal e.V.</span>
<h1>Gut versorgt im <em>Würmtal</em>.</h1>
<p class="lead">{len(entries)} Praxen aus {len(ORT_SLUG)} Orten an einer Stelle. Suchen Sie nach Name, Fachgebiet oder Ort und finden Sie Adresse, Telefon und Praxis-Website.</p>
<form class="search" action="aerzte.html" method="get" role="search">
<label class="sr-only" for="hero-q">Arzt, Fachgebiet oder Ort suchen</label>
<input id="hero-q" name="q" type="search" placeholder="z. B. Kardiologie, Planegg, Dr. Huber" autocomplete="off">
<button type="submit">{icon("search", root, "sm")}Suchen</button>
</form>
<a class="textlink" href="#fachgebiete">Nach Fachgebiet stöbern {icon("arrow", root, "sm")}</a>
</div>
<div class="wrap"><div class="stats">
<div class="stat"><b>{len(entries)}</b><span>Praxiseinträge</span></div>
<div class="stat"><b>{len(ORT_SLUG)}</b><span>Orte im Würmtal</span></div>
<div class="stat"><b>{sum(1 for v in fach_counts.values() if v)}</b><span>Fachgebiete</span></div>
<div class="stat"><b>{len(listed_profile_dirs)}</b><span>Praxisprofile</span></div>
</div></div>
</section>

<section class="section" id="fachgebiete">
<div class="wrap">
<div class="section-head"><div><span class="eyebrow">Fachgebiete</span><h2>Der richtige Arzt<br>für jedes Anliegen.</h2></div>
<p>Wählen Sie ein Fachgebiet und sehen Sie sofort alle passenden Praxen im Würmtal.</p></div>
<div class="fach-grid">{fach_tiles}</div>
</div>
</section>

<section class="section alt" id="orte">
<div class="wrap">
<div class="section-head"><div><span class="eyebrow">Orte</span><h2>Neun Orte.<br>Ein Verzeichnis.</h2></div>
<p>Von Gauting bis Germering: Die Praxen nach Standort, mit Anzahl der Einträge.</p></div>
<div class="orte">{orte_rows}</div>
</div>
</section>

<section class="section" id="verein">
<div class="wrap">
<div class="verein-grid">
<div class="about">
<span class="eyebrow">Der Verein</span>
<h2>Ärzte, die sich vernetzen.</h2>
<p>Im Ärzteverein im Würmtal e.V. engagieren sich Ärztinnen und Ärzte verschiedener Fachrichtungen aus dem westlichen Münchner Umland. Vertreten sind unter anderem Gräfelfing mit Lochham, Planegg mit Martinsried, Germering, Krailling mit Stockdorf und Gauting. Der Verein hat seinen Sitz in Gräfelfing.</p>
<p>Gemeinsam stärken die Mitglieder die wohnortnahe Versorgung und halten den fachlichen Austausch lebendig.</p>
</div>
<div class="ziele">{ziele}</div>
</div>
<div class="vorstand">{vorstand}</div>
</div>
</section>

<section class="kontakt" id="kontakt">
<div class="wrap kontakt-grid">
<div class="kontakt-info">
<div><span class="eyebrow">Kontakt</span><h2>Fragen zum Verein?</h2></div>
<dl>
<div><dt>Verein</dt><dd>Ärzteverein im Würmtal e.V.</dd></div>
<div><dt>Anschrift</dt><dd>Bahnhofplatz 3, 82131 Gauting</dd></div>
<div><dt>Telefon</dt><dd><a href="tel:+49898571057">+49 89 857 1057</a></dd></div>
<div><dt>Fax</dt><dd>+49 89 857 7762</dd></div>
</dl>
</div>
<div class="map">
<div class="map-ph" data-consent-placeholder="external">
<h3>Anfahrt</h3>
<p>Die Karte stammt von OpenStreetMap. Beim Laden wird Ihre IP-Adresse an den Anbieter übertragen. Bis dahin findet keine Verbindung statt.</p>
<button type="button" class="btn" data-consent-grant="external">Karte laden</button>
</div>
<iframe data-consent="external" data-src="{OSM_EMBED}" title="Karte: Bahnhofplatz 3, 82131 Gauting" loading="lazy" referrerpolicy="no-referrer" hidden></iframe>
<div class="map-foot"><span>Bahnhofplatz 3, 82131 Gauting</span><a href="{OSM_LINK}" target="_blank" rel="noopener noreferrer">Karte bei OpenStreetMap öffnen</a></div>
</div>
</div>
</section>
<script type="application/ld+json">{ld}</script>"""
    return page("Würmtal Ärzte | Ärzteverein im Würmtal e.V.",
                f"Ärzteverzeichnis im Würmtal: {len(entries)} Praxen in Gauting, Germering, Gräfelfing, Krailling, Lochham, Martinsried, Neuried, Planegg und Stockdorf.",
                root, "index.html", body)


def build_search() -> str:
    root = ""
    fach_chips = "".join(
        f'<button type="button" class="chip" data-filter="fach" data-value="{s}" aria-pressed="false">{esc(l)} <small>{fach_counts[s]}</small></button>'
        for s, l, *_ in FACHGEBIETE if fach_counts[s])
    ort_chips = "".join(
        f'<button type="button" class="chip" data-filter="ort" data-value="{ORT_SLUG[o]}" aria-pressed="false">{o} <small>{len(by_ort[o])}</small></button>'
        for o in ORT_SLUG)
    cards = "".join(card(e, root) for e in sorted(entries, key=lambda e: (e["ort"], e["name"])))
    body = page_head(root, [("Start", "index.html"), ("Ärzte finden", "")], "Ärzte finden",
                     "Durchsuchen Sie alle Einträge nach Name, Fachgebiet, Straße oder Ort.", "SUCHE") + f"""
<section class="section"><div class="wrap">
<form class="toolbar" role="search">
<div class="search"><label class="sr-only" for="q">Suchbegriff</label>
<input id="q" type="search" placeholder="Name, Fachgebiet, Straße oder Ort" autocomplete="off">
<button type="button" data-reset aria-label="Suche zurücksetzen">Zurücksetzen</button></div>
<div><div class="toolbar-label">Ort</div><div class="chips">{ort_chips}</div></div>
<div><div class="toolbar-label">Fachgebiet</div><div class="chips">{fach_chips}</div></div>
</form>
<div class="result-line"><span id="count" aria-live="polite">{len(entries)} von {len(entries)} Einträgen</span><button type="button" id="reset" data-reset hidden>Filter zurücksetzen</button></div>
<div class="cards" id="results">{cards}</div>
<div class="empty" id="empty" hidden><h3>Keine Treffer</h3><p>Zu dieser Auswahl gibt es keinen Eintrag. Lockern Sie die Filter oder suchen Sie nach einem anderen Begriff.</p><button class="btn" type="button" data-reset>Alle anzeigen</button></div>
</div></section>"""
    return page("Ärzte finden | Würmtal Ärzte", f"Alle {len(entries)} Praxen im Würmtal durchsuchen: nach Name, Fachgebiet und Ort filtern.",
                root, "aerzte.html", body, active="aerzte")


def build_ort(o: str) -> str:
    root = "../"
    lst = by_ort[o]
    cards = "".join(card(e, root) for e in lst)
    others = "".join(
        f'<a class="chip" href="aerzte_{ORT_SLUG[x]}.htm"{" aria-current=page" if x == o else ""}>{x} <small>{len(by_ort[x])}</small></a>'
        for x in ORT_SLUG)
    n = len(lst)
    body = page_head(root, [("Start", root + "index.html"), ("Ärzte finden", root + "aerzte.html"), (o, "")], o,
                     f'{n} {"Praxiseintrag" if n == 1 else "Praxiseinträge"} im Verzeichnis des Ärztevereins.', o.upper()) + f"""
<section class="section"><div class="wrap">
<div class="cards">{cards}</div>
<div class="neighbors"><span class="toolbar-label">Weitere Orte</span><div class="chips">{others}</div></div>
</div></section>"""
    return page(f"Ärzte in {o} | Würmtal Ärzte", f"{n} Arztpraxen in {o}: Fachgebiet, Adresse, Telefon und Praxis-Website.",
                root, f"htm/aerzte_{ORT_SLUG[o]}.htm", body, active="aerzte")


def tab_label(p: dict) -> str:
    if " – " in p["name"]:
        return p["name"].split(" – ", 1)[1]
    return "Praxis"


def build_profile(slug: str, p: dict) -> str:
    root = "../../../"
    siblings = profiles[slug]
    base_name = p["name"].split(" – ")[0]
    ort = p["ort"]
    tabs = ""
    if len(siblings) > 1:
        tabs = '<nav class="tabs" aria-label="Profilbereiche">' + "".join(
            f'<a href="{s["file"]}"{" aria-current=page" if s["file"] == p["file"] else ""}>{esc(tab_label(s))}</a>' for s in siblings) + "</nav>"
    mainp = profile_main(slug)
    kv = [("Anschrift", esc(p["anschrift"]))]
    src = p if p["telefon"] else mainp
    if p["telefon"]:
        kv.append(("Telefon", f'<a href="tel:{tel_from_profile(p["telefon"])}">{esc(p["telefon"])}</a>'))
    if p["fax"]:
        kv.append(("Telefax", esc(p["fax"])))
    if p["email"]:
        kv.append(("E-Mail", f'<a href="mailto:{esc(p["email"])}">{esc(p["email"])}</a>'))
    kv_html = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in kv)
    blocks = f'<div class="block"><h2>{icon("pin", root)}Kontakt</h2><dl class="kv">{kv_html}</dl></div>'
    left = ""
    if p["sprechzeiten"]:
        left += (f'<div class="block"><h2>{icon("clock", root)}Sprechzeiten</h2><ul class="hours">'
                 + "".join(f"<li>{esc(h)}</li>" for h in p["sprechzeiten"]) + "</ul></div>")
    if p["leistungen"]:
        left += (f'<div class="block"><h2>{icon("check", root)}Leistungen & Schwerpunkte</h2><ul class="checks">'
                 + "".join(f"<li>{icon('check', root, 'sm')}<span>{esc(l)}</span></li>" for l in p["leistungen"]) + "</ul></div>")
    if not left:
        left = (f'<div class="block"><h2>{icon("info", root)}Profil</h2><p>Zu dieser Seite liegen keine weiteren Angaben vor. '
                f'Kontaktdaten finden Sie rechts, aktuelle Informationen erhalten Sie direkt in der Praxis.</p></div>')
    if len(siblings) > 1 and p is not mainp:
        blocks += f'<a class="btn ghost" href="{mainp["file"]}">Zurück zum Praxisprofil</a>'
    note = (f'<div class="note">{icon("info", root, "sm")}<p>Ältere Profilseite des Vereins. Bitte bestätigen Sie Adresse, '
            f'Sprechzeiten und Leistungen direkt in der Praxis.</p></div>')
    fach = p["fachrichtung"] if "Keine Fachrichtung" not in p["fachrichtung"] else "Fachrichtung nicht angegeben"
    body = page_head(root, [("Start", root + "index.html"), (ort, root + f"htm/aerzte_{ORT_SLUG[ort]}.htm"), (base_name, "")],
                     esc(base_name), esc(fach), ort.upper()) + f"""
<section class="section"><div class="wrap">
{tabs}
<div class="profile"><div style="display:grid;gap:1.1rem">{left}</div><div style="display:grid;gap:1.1rem">{blocks}</div></div>
{note}
</div></section>"""
    listed = slug in listed_profile_dirs
    return page(f"{base_name} | Würmtal Ärzte", f"{base_name}, {fach} in {ort}: Kontakt, Sprechzeiten und Leistungen.",
                root, p["pfad"], body, active="aerzte", noindex=not listed)


def build_impressum() -> str:
    root = "../"
    body = page_head(root, [("Start", root + "index.html"), ("Impressum", "")], "Impressum") + f"""
<section class="section"><div class="wrap"><div class="prose">
<h2>Anbieter</h2>
<address>Ärzteverein im Würmtal e.V.<br>Bahnhofplatz 3<br>82131 Gauting</address>
<h2>Vertreten durch</h2>
<p>Priv.-Doz. Dr. med. Markus G. Engelmann, Vorsitzender</p>
<h2>Kontakt</h2>
<p>Telefon: <a href="tel:+49898571057">+49 89 857 1057</a><br>Telefax: +49 89 857 7762</p>
<h2>Berufsaufsicht</h2>
<p>Bayerische Landesärztekammer</p>
<h2>Verantwortung für Inhalte der Praxen</h2>
<p>Die Praxisangaben im Verzeichnis liegen in der Verantwortung der jeweiligen Praxen. Der Verein prüft sie nicht auf Vollständigkeit oder Aktualität. Maßgeblich sind die Berufsordnung und die berufsrechtlichen Regelungen der Bayerischen Landesärztekammer.</p>
<h2>Urheberrecht</h2>
<p>Inhalte und Gestaltung dieser Seiten unterliegen dem Urheberrecht. Eine Verwendung außerhalb der gesetzlichen Schranken bedarf der Zustimmung des Vereins.</p>
<h2>Haftung für Links</h2>
<p>Die Seiten verlinken auf Websites einzelner Praxen. Für deren Inhalte sind ausschließlich die jeweiligen Betreiber verantwortlich.</p>
<h2>Kontakt per E-Mail</h2>
<p>Vertrauliche Informationen sollten nicht unverschlüsselt per E-Mail übermittelt werden.</p>
</div></div></section>"""
    return page("Impressum | Würmtal Ärzte", "Impressum des Ärztevereins im Würmtal e.V.", root, "htm/avw_impressum.htm", body)


def build_datenschutz() -> str:
    root = "../"
    body = page_head(root, [("Start", root + "index.html"), ("Datenschutz", "")], "Datenschutz") + f"""
<section class="section"><div class="wrap"><div class="prose">
<h2>Verantwortlicher</h2>
<address>Ärzteverein im Würmtal e.V.<br>Priv.-Doz. Dr. med. Markus G. Engelmann<br>Bahnhofplatz 3, 82131 Gauting<br>Telefon +49 89 857 1057 · Telefax +49 89 857 7762</address>
<h2>Cookies, Tracking und Formulare</h2>
<p>Diese Website setzt keine Cookies, verwendet keine Analyse- oder Werbedienste und bietet keine Formulare, über die Sie Daten an uns senden. Die Arztsuche läuft vollständig in Ihrem Browser. Suchbegriffe werden nicht übertragen oder gespeichert.</p>
<h2>Einwilligungsverwaltung</h2>
<p>Beim ersten Besuch fragen wir Sie, ob externe Inhalte geladen werden dürfen. Ihre Auswahl speichern wir im localStorage Ihres Browsers (Schlüssel „avw-consent“, Gültigkeit 6 Monate). Das ist technisch erforderlich, um Ihre Entscheidung zu respektieren (§ 25 Abs. 2 Nr. 2 TDDDG). Über „Cookie-Einstellungen“ im Seitenfuß können Sie Ihre Auswahl jederzeit ändern oder widerrufen.</p>
<h2>Karte (OpenStreetMap)</h2>
<p>Im Kontaktbereich bieten wir eine Karte von OpenStreetMap an. Sie wird erst nach Ihrer Einwilligung geladen (Art. 6 Abs. 1 lit. a DSGVO, § 25 Abs. 1 TDDDG). Beim Laden überträgt Ihr Browser Ihre IP-Adresse und technische Daten (z. B. Browsertyp, aufgerufene Seite) an die OpenStreetMap Foundation im Vereinigten Königreich. Ohne Einwilligung findet keine Verbindung statt. Die Einwilligung können Sie jederzeit mit Wirkung für die Zukunft widerrufen.</p>
<h2>Schriften</h2>
<p>Alle Schriften werden von dieser Website selbst ausgeliefert. Es werden keine Schriftdateien von Drittanbietern geladen.</p>
<h2>Server-Protokolle</h2>
<p>Beim Aufruf der Seiten verarbeitet der Hosting-Anbieter technisch notwendige Daten in Server-Protokollen:</p>
<ul><li>Typ und Version des Browsers</li><li>Betriebssystem</li><li>zuvor besuchte Seite (Referrer)</li><li>Hostname bzw. technische Herkunft der Anfrage</li><li>Zeitpunkt der Anfrage</li><li>IP-Adresse</li></ul>
<p>Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (Betrieb und Sicherheit der Website). Die Daten werden nicht mit anderen Datenquellen zusammengeführt.</p>
<h2>Links zu anderen Websites</h2>
<p>Die Praxiseinträge verlinken auf externe Websites. Beim Anklicken gelten die Datenschutzhinweise der jeweiligen Betreiber.</p>
<h2>Ihre Rechte</h2>
<p>Sie haben das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Widerspruch und Datenübertragbarkeit. Wenden Sie sich dazu an die oben genannte Stelle. Sie können sich außerdem bei der zuständigen Aufsichtsbehörde beschweren: Bayerisches Landesamt für Datenschutzaufsicht, Promenade 18, 91522 Ansbach.</p>
</div></div></section>"""
    return page("Datenschutz | Würmtal Ärzte", "Datenschutzerklärung der Website des Ärztevereins im Würmtal e.V.", root, "htm/datenschutz.html", body)


def build_404() -> str:
    root = BASE_PATH
    body = f"""<section class="section"><div class="wrap" style="display:grid;gap:1.5rem;justify-items:start">
<span class="eyebrow">Fehler 404</span><h1>Seite nicht gefunden.</h1>
<p>Diese Adresse gibt es nicht oder nicht mehr. Über die Arztsuche finden Sie alle Praxen im Würmtal.</p>
<a class="btn" href="{root}aerzte.html">Zur Arztsuche {icon("arrow", root, "sm")}</a></div></section>"""
    return page("Seite nicht gefunden | Würmtal Ärzte", "Diese Seite existiert nicht.", root, "404.html", body, noindex=True, abs_assets=True)


# --------------------------------------------------------------------------- Ausgabe


def write(rel: str, content: str) -> None:
    p = DIST / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "public", DIST)
    urls = ["index.html", "aerzte.html"]
    write("index.html", build_index())
    write("aerzte.html", build_search())
    for o in ORT_SLUG:
        rel = f"htm/aerzte_{ORT_SLUG[o]}.htm"
        write(rel, build_ort(o))
        urls.append(rel)
    for slug, plist in profiles.items():
        for p in plist:
            write(p["pfad"], build_profile(slug, p))
            if slug in listed_profile_dirs:
                urls.append(p["pfad"])
    write("htm/avw_impressum.htm", build_impressum())
    write("htm/datenschutz.html", build_datenschutz())
    urls += ["htm/avw_impressum.htm", "htm/datenschutz.html"]
    write("404.html", build_404())
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        loc = SITE_URL + "/" + ("" if u == "index.html" else u)
        sm.append(f"<url><loc>{loc}</loc><lastmod>{TODAY}</lastmod></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"OK: {len(list(DIST.rglob('*.htm*')))} HTML-Seiten in {DIST}")


if __name__ == "__main__":
    main()
