# RAKSHAK

RAKSHAK is a Flask, Socket.IO, and MySQL based safety platform for real-time SOS response, trusted-contact alerts, danger-zone intelligence, safe-walk tracking, and AI-assisted safety guidance.

Live app: https://rakshak.up.railway.app

## Current Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.11+, Flask 3, Flask-SocketIO, Eventlet, Gunicorn |
| Database | MySQL-compatible provider with optional SSL |
| Auth | Google OAuth, Flask-Login, optional development login |
| Realtime | Socket.IO rooms for users, admins, SOS, risk updates, danger zones |
| Frontend | Jinja templates, custom CSS, Canvas/WebGL experiences |
| Reports | ReportLab PDF incident dossiers |
| Deployment | Docker on Railway |
| PWA | Service worker, manifest, offline fallback |

## Features

- SOS alerts with trusted-contact delivery links, PDF report support, and realtime admin broadcasts
- Safe Walk journey tracking with live updates and route state
- Danger zone reporting, approval workflow, heatmap, proximity checks, and upvotes
- AI threat engine for heartbeat risk scoring and missed-ping escalation
- Safety Score calculator based on location, time, danger zones, and recent SOS alerts
- ARIA Guardian safety assistant and Guardian Network responder mode
- Valkyrie PIN safety flow, Fake Call, Emergency quick dial, Safety Tips
- Vision Shield and X-Ray Vision camera experiences
- Admin command center with analytics, users, alerts, zones, and audit logs

## Project Layout

```text
RAKSHAK/
├── app.py
├── config.py
├── models.py
├── socket_events.py
├── healer.py
├── init_db.py
├── migrate_guardian.py
├── pdf_reports.py
├── wsgi.py
├── modules/
│   ├── admin/
│   ├── ai_engine/
│   ├── aria_guardian/
│   ├── auth/
│   ├── danger_zones/
│   ├── emergency/
│   ├── fake_call/
│   ├── guardian_network/
│   ├── main/
│   ├── safe_walk/
│   ├── safety_score/
│   ├── safety_tips/
│   ├── sos/
│   ├── valkyrie/
│   ├── vision_shield/
│   └── xray_vision/
├── static/
│   ├── css/
│   ├── img/
│   ├── js/
│   ├── manifest.json
│   └── sw.js
├── templates/
├── Dockerfile
├── LICENSE
├── docker-compose.yml
├── entrypoint.sh
├── railway.json
├── requirements.txt
└── schema.sql
```

## Environment

Create `.env` from `.env.example` and fill production values before deploy.

Required in production:

```env
FLASK_ENV=production
SECRET_KEY=change-this-to-a-long-random-secret
ALLOWED_ORIGINS=https://your-domain.example

DB_HOST=your-mysql-host
DB_PORT=3306
DB_USER=your-mysql-user
DB_PASSWORD=your-mysql-password
DB_NAME=rakshak
DB_SSL=true

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Railway MySQL variables are also supported automatically:

```env
MYSQLHOST=
MYSQLPORT=
MYSQLUSER=
MYSQLPASSWORD=
MYSQLDATABASE=
```

Optional:

```env
KEEP_ALIVE_URL=https://rakshak.up.railway.app/ping
ALLOW_DEV_LOGIN=false
VALKYRIE_PIN=1234
RATELIMIT_STORAGE_URI=redis://default:password@host:6379/0
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true
```

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python init_db.py
python app.py
```

The local app runs on `http://localhost:5001` by default. To choose another port:

```bash
PORT=5000 python app.py
```

## Deployment

Railway uses the Dockerfile and `entrypoint.sh`.

```bash
git push origin main
```

Runtime command:

```bash
/bin/sh /app/entrypoint.sh
```

Health check:

```text
/ping
```

## Verification Commands

```bash
python3 -m py_compile $(git ls-files '*.py')
for f in $(git ls-files '*.js'); do node --check "$f" || exit 1; done
```

## Contributor

Manik Sahni

## License

MIT
