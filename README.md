# FocusFlow

FocusFlow is a calm, practical productivity workspace for turning projects into clear next actions. Each account gets private projects and tasks, with quick filters, priorities, due dates, completion tracking, and paginated task results.

## Stack

- React + Vite frontend
- Flask REST API
- PostgreSQL in deployment, SQLite for zero-setup local development
- SQLAlchemy, Flask-JWT-Extended, and bcrypt-compatible Werkzeug password hashing

## Run locally

```bash
# API
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

# In another terminal, from the project root
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend proxies `/api` requests to Flask on port 5000.

For PostgreSQL, set `DATABASE_URL=postgresql+psycopg://user:password@host:5432/focusflow` and a strong `JWT_SECRET_KEY` before starting the API. The API includes signup, login, current-user, project CRUD, task CRUD, ownership enforcement, filtering, and pagination at `/api/tasks?page=1&per_page=8`.

## Deploy with Render

The included `render.yaml` provisions a PostgreSQL database, Flask API, and React static site. In Render, create a new Blueprint from this repository and deploy the generated services. The frontend automatically receives the API service host through `VITE_API_URL`.

## Test

```bash
cd backend
pytest
```

## Project brief

FocusFlow fulfills the productivity application brief with two related resources: projects belong to users, and tasks belong to projects. Every protected read and write is scoped through the authenticated user's identity. The interface includes loading states, empty states, responsive layout, and a small dashboard summary so users can understand their week at a glance.
