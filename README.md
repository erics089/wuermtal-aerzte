# Würmtal Ärzte – Relaunch

Neue Website des **Ärztevereins im Würmtal e.V.** (wuermtalaerzte.de): kantiges Design in Orange, 43 Praxiseinträge in 9 Orten, Arztsuche mit Filter, Praxisprofile, Impressum und Datenschutz.

Die Seite ist statisch (HTML, CSS, etwas JavaScript), braucht keine Datenbank und keine Abhängigkeiten. Der Generator nutzt nur die Python-Standardbibliothek.

## Schnellstart

```bash
python3 build.py                                  # erzeugt dist/
python3 -m http.server 8080 --directory dist      # Vorschau: http://localhost:8080
python3 scripts/check_links.py dist               # prüft alle internen Links
```

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `data/daten.json` | Alle Inhalte: Orte, Praxen, Profile, Vorstand |
| `build.py` | Generator: erzeugt alle Seiten aus den Daten |
| `public/` | Statische Dateien: CSS, JS, Schriften, Icons, Favicons, `og.png`, `.htaccess`, `_headers` |
| `dist/` | Build-Ergebnis (nicht im Git) |
| `scripts/check_links.py` | Link-Prüfung für CI |
| `docs/redaktionelle-pruefung.md` | Offene Punkte vor dem Livegang |
| `.github/workflows/pages.yml` | Build und Deployment auf GitHub Pages |

Inhalte ändern: `data/daten.json` bearbeiten und `python3 build.py` ausführen. Neue Fachgebiete werden in `build.py` unter `FACHGEBIETE` zugeordnet.

## URLs

Die alten Adressen bleiben erhalten (`htm/aerzte_<ort>.htm`, `htm/avw_impressum.htm`, `htm/datenschutz.html`, `htm/aerzte/<name>/<name>.htm`). Neu ist `aerzte.html` (Arztsuche).

## Deployment

**GitHub Pages:** In den Repository-Einstellungen unter Pages die Quelle „GitHub Actions“ wählen. Jeder Push auf `main` baut und veröffentlicht die Seite. Für eine eigene Domain die Repository-Variablen `SITE_URL` (z. B. `https://www.wuermtalaerzte.de`) und `BASE_PATH` (`/`) setzen.

**Netlify / Cloudflare Pages:** Build-Befehl `python3 build.py`, Verzeichnis `dist`, Umgebungsvariable `SITE_URL`. Sicherheits-Header liegen in `public/_headers`.

**Klassischer Webspace (Apache):** Inhalt von `dist/` hochladen. `public/.htaccess` setzt Header, Caching und die 404-Seite. Vor dem Build `SITE_URL=https://www.wuermtalaerzte.de python3 build.py` ausführen.

## Technik

- Schriften (Archivo, Inter, JetBrains Mono, SIL OFL) liegen lokal in `public/assets/fonts`. Es werden keine Drittanbieter geladen.
- Hell- und Dunkelmodus folgen dem System.
- Barrierearm: Skip-Link, Tastaturfokus, Kontrast, `prefers-reduced-motion`.
- Sitemap und `robots.txt` entstehen beim Build. Profile ohne aktuellen Eintrag sind `noindex`.

## Vor dem Livegang

Die Inhalte stammen aus einer Bestandsaufnahme der alten Seite (Stand 22.11.2023). Impressum und Datenschutz müssen rechtlich geprüft und ergänzt werden (Vereinsregister, Hosting-Anbieter). Alle Punkte stehen in [`docs/redaktionelle-pruefung.md`](docs/redaktionelle-pruefung.md).
