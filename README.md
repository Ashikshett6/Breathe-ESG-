# Breathe ESG — Data Ingestion & Review Prototype

Django REST + React app for ingesting SAP, utility, and corporate travel data, normalizing to activity records, and analyst review before audit lock.

## Repository

**GitHub:** [github.com/Ashikshett6/Breathe-ESG-](https://github.com/Ashikshett6/Breathe-ESG-)

## Live deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Ashikshett6/Breathe-ESG-)

1. Click **Deploy to Render** above (sign in with GitHub as **Ashikshett6**).
2. Confirm the blueprint (`render.yaml` creates DB + web service) and click **Apply**.
3. Wait ~5–10 minutes for the build. Open your `*.onrender.com` URL.

**Live URL:** _(add after deploy, e.g. `https://breathe-esg-review.onrender.com`)_

**Demo login:** `analyst` / `demo1234` (created by `seed_demo` on build)

Set `ALLOWED_HOSTS` to your `*.onrender.com` hostname if needed.

## Documentation (assignment deliverables)

| File | Contents |
|------|----------|
| [MODEL.md](./MODEL.md) | Data model, multi-tenancy, scopes, audit trail |
| [DECISIONS.md](./DECISIONS.md) | Format choices and PM questions |
| [TRADEOFFS.md](./TRADEOFFS.md) | Three deliberate omissions |
| [SOURCES.md](./SOURCES.md) | Research notes and sample data rationale |

## Local development

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

API: http://127.0.0.1:8000/api/  
UI (dev): http://127.0.0.1:5173 (proxies `/api` to Django)

## Sample uploads

CSV files in [`samples/`](./samples/) match the three source parsers. Upload via **Upload** in the UI or re-run `python manage.py seed_demo`.

## API overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login/` | `{username, password}` → token |
| `GET /api/dashboard/` | Review stats |
| `GET /api/activities/` | Filterable activity list |
| `POST /api/activities/{id}/approve/` | Approve row |
| `POST /api/activities/bulk_approve/` | `{ids: []}` |
| `POST /api/activities/lock_approved/` | Lock approved for audit |
| `POST /api/ingest/upload/` | multipart: `source_type`, `file` |



**##Reviewer access**

saurav@breatheesg.com
rahul@breatheesg.com
shivang@breatheesg.com
## Tech stack

- Python 3.12, Django 5, DRF, PostgreSQL (prod) / SQLite (local)
- React 18, Vite, TypeScript
- Gunicorn + WhiteNoise on Render
