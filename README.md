# XGuard Org Chart

Internal organizational chart tool for XGuard's Training Division (Formation Gardiennage / Formation Drone).

**Live:** [nicksoucy.github.io/orgnigram-xguard](https://nicksoucy.github.io/orgnigram-xguard)

## Tech Stack

- **Frontend:** Vanilla HTML / CSS / JS (single `index.html`, no build step)
- **Fonts:** DM Sans + Space Mono (Google Fonts)
- **Backend:** Supabase (PostgreSQL) via `supabase-js` v2 CDN
- **Hosting:** GitHub Pages

## Features

- **5 views:** By Department, Reporting Hierarchy, Future State, Canvas View, Tasks & Outcomes
- Add, edit, and delete people and departments
- Dynamic department creation
- Program tags and delegation tracking
- Notes per person
- Drag-to-pan canvas with zoom
- Real-time sync via Supabase
- **ID card printing** — print-ready staff/trainer badges at exact CR-80 size for HiTi card printers ([setup guide](docs/HITI_PRINTING.md))

## Card Printing (HiTi)

The **Cartes** tab turns any people in the org chart into print-ready ID badges sized to
the ISO **CR-80** standard (85.6 × 54 mm) used by every HiTi CS-series card printer.

- **🖨 Imprimer** — browser print, one physical card per page (`@page` locked to card size).
- **📄 Export PDF** — one card per page, rasterized at ≥300 dpi (the printer's native resolution).
- Options: recto or recto+verso, bleed (for edge-to-edge / over-the-edge printing), light or
  dark theme, QR (profile link or vCard), accent colour, and per-field toggles.
- QR/print rendering uses the vendored MIT [`qrcode-generator`](js/vendor/qrcode.js) plus the
  `html2canvas` + `jsPDF` libraries already loaded by the app — no new runtime CDN dependency.

Full driver install, ribbon/media, calibration and troubleshooting: **[docs/HITI_PRINTING.md](docs/HITI_PRINTING.md)**.

## Database Schema

| Table | Purpose |
|---|---|
| `departments` | Department definitions (name, color, etc.) |
| `people` | Personnel records (name, role, department, reports_to, tags, notes) |
| `tasks` | Task and outcome tracking |
| `canvas_order` | Persisted positions for the canvas view |

## Local Development

No build step required. Open `index.html` directly in a browser or serve it locally:

```bash
npx http-server .
```

### Environment Variables

The app reads Supabase credentials from its source. For local development, ensure the following values are configured:

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Your Supabase anonymous (public) API key |

> **Note:** Do not commit real keys to a public repository. Use a `.env` file or inject them at deploy time.
