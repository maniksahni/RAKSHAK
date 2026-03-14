# RAKSHAK — Real-time Alert & Knowledge System for Hazard And Crisis
# Women's Safety & Emergency Response System

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- MySQL 8.0+
- pip

### 1. Clone & Install
```bash
cd rakshak
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Create MySQL database and run schema
mysql -u root -p < schema.sql
```

### 3. Environment Configuration
```bash
cp .env.example .env
# Edit .env — set DB_PASSWORD and SECRET_KEY
```

### 4. Run
```bash
python app.py
# Visit: http://localhost:5000
```

---

## 🔑 Default Credentials

| Role  | Email                 | Password   |
|-------|-----------------------|------------|
| Admin | admin@rakshak.com     | Admin@123  |
| User  | priya@example.com     | User@123   |

> ⚠️ Change passwords immediately in production!

---

## 📦 Project Structure

```
rakshak/
├── app.py                  # Flask app factory
├── config.py               # Dev / Prod config
├── models.py               # DB pool + User model
├── socket_events.py        # Flask-SocketIO events
├── pdf_reports.py          # ReportLab PDF generation
├── schema.sql              # MySQL schema (7 tables)
├── requirements.txt        
├── .env.example            
│
├── modules/
│   ├── auth/routes.py      # Register, Login, Profile, Contacts
│   ├── sos/routes.py       # SOS Trigger, History, PDF, Dashboard
│   ├── ai_engine/routes.py # Ping, Risk Scoring, Auto-SOS
│   ├── danger_zones/routes.py  # Heatmap, Report, Proximity
│   ├── admin/routes.py     # Dashboard, Analytics, Approvals
│   └── main/routes.py      # Landing page
│
├── templates/
│   ├── base.html           # Sidebar + Navbar + Toast system
│   ├── index.html          # Landing page (Three.js shield)
│   ├── auth/               # Login, Register, Profile, Forgot PW
│   ├── dashboard/          # User dashboard (SOS button + map)
│   ├── danger_zones/       # Full-screen Leaflet heatmap
│   ├── admin/              # Admin dashboard (charts + live feed)
│   └── errors/             # 404, 500 error pages
│
└── static/
    ├── css/main.css        # Dark glassmorphism design system
    └── js/
        ├── three_shield.js # Three.js landing hero animation
        ├── dashboard.js    # SOS, AI ping, Leaflet mini-map
        ├── heatmap.js      # Leaflet.heat + danger zone markers
        └── admin.js        # Chart.js analytics + admin controls
```

---

## 🎨 Tech Stack

| Layer     | Technology                                    |
|-----------|-----------------------------------------------|
| Backend   | Python Flask + Flask-SocketIO + Flask-Login   |
| Database  | MySQL 8.0 (7 tables, indexed)                 |
| Security  | bcrypt, CSRF, Rate Limiting, Parameterized SQL|
| Real-time | Flask-SocketIO (eventlet)                     |
| PDF       | ReportLab                                     |
| Frontend  | HTML5, CSS3, Bootstrap 5, Vanilla JS          |
| 3D/Anim   | Three.js, GSAP, ScrollTrigger                 |
| Maps      | Leaflet.js + Leaflet.heat                     |
| Charts    | Chart.js 4                                    |

---

## 👥 User Roles

| Role            | Capabilities                                              |
|-----------------|-----------------------------------------------------------|
| **User**        | Dashboard, SOS trigger, AI ping, danger map, PDF reports  |
| **Trusted Contact** | Receives SOS alerts via SocketIO + in-app notification  |
| **Admin**       | Full control: users, zones, analytics, live alert feed    |

---

## 🔒 Security Features

- bcrypt password hashing (cost factor 12)
- Flask-WTF CSRF protection on all forms
- Flask-Limiter rate limiting (auth routes: 5–20/hour)
- Parameterized SQL queries (no SQL injection risk)
- Security-question based password recovery
- Input validation (server-side) on all endpoints
- Audit log for all user actions

---

## 📡 Real-time Events (SocketIO)

| Event            | Direction       | Description                          |
|------------------|-----------------|--------------------------------------|
| `ping_alive`     | Client → Server | Heartbeat every 2 minutes            |
| `new_alert`      | Server → Client | SOS alert to trusted contacts        |
| `new_sos`        | Server → Admin  | SOS alert to admin room              |
| `risk_update`    | Server → Admin  | User risk level changed              |
| `new_danger_zone`| Server → All    | Approved danger zone broadcasted     |

---

## 🧠 AI Engine Logic

```
Every 2 minutes: JS sends /ai/ping
  → If ping received: reset consecutive_missed_pings → risk = LOW

If user misses 1 ping  → risk = LOW
If user misses 2 pings → risk = MEDIUM  (warning shown)
If user misses 3 pings → risk = HIGH + AUTO SOS TRIGGERED
```

---

## 📝 License
MIT — Built for educational and safety purposes.
