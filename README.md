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
