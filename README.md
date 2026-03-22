<p align="center">
  <img src="https://img.shields.io/badge/🛡️-RAKSHAK-red?style=for-the-badge&labelColor=1a1a2e&color=e94560" alt="RAKSHAK" height="60"/>
</p>

<h1 align="center">

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    ██████   █████  ██   ██ ███████ ██   ██  █████  ██   ██   ║
║    ██   ██ ██   ██ ██  ██  ██      ██   ██ ██   ██ ██  ██    ║
║    ██████  ███████ █████   ███████ ███████ ███████ █████      ║
║    ██   ██ ██   ██ ██  ██       ██ ██   ██ ██   ██ ██  ██    ║
║    ██   ██ ██   ██ ██   ██ ███████ ██   ██ ██   ██ ██   ██   ║
║                                                              ║
║     Real-time Alert & Knowledge System for Hazard And Crisis ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

</h1>

<p align="center">
  <strong>🛡️ AI-Powered Women's Safety & Emergency Response Platform 🛡️</strong>
</p>

<p align="center">
  <a href="https://rakshak.up.railway.app"><img src="https://img.shields.io/badge/🌐_LIVE-rakshak.up.railway.app-e94560?style=for-the-badge&labelColor=1a1a2e" alt="Live Site"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white" alt="MySQL"/>
  <img src="https://img.shields.io/badge/Socket.IO-Realtime-010101?style=flat-square&logo=socket.io&logoColor=white" alt="SocketIO"/>
  <img src="https://img.shields.io/badge/Railway-Deployed-0B0D0E?style=flat-square&logo=railway&logoColor=white" alt="Railway"/>
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white" alt="Bootstrap"/>
  <img src="https://img.shields.io/badge/PWA-Installable-5A0FC8?style=flat-square&logo=pwa&logoColor=white" alt="PWA"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
</p>

<p align="center">
  <em>Empowering women with real-time safety intelligence, AI-driven threat assessment, and instant emergency response — all in one platform.</em>
</p>

---

## 🔥 About

**RAKSHAK** is a comprehensive, AI-integrated women's safety system designed to provide real-time protection through intelligent threat detection, emergency SOS alerts, danger zone mapping, and a suite of safety tools. Built with Flask and Socket.IO, it delivers instant WebSocket-powered notifications and supports Progressive Web App (PWA) installation for always-available access.

Whether walking alone at night or navigating unfamiliar areas, RAKSHAK acts as a silent guardian — monitoring, alerting, and connecting users to help in seconds.

---

## 🌐 Live Demo

<table>
  <tr>
    <td align="center"><strong>🔗 Live URL</strong></td>
    <td><a href="https://rakshak.up.railway.app">https://rakshak.up.railway.app</a></td>
  </tr>
  <tr>
    <td align="center"><strong>👑 Admin Login</strong></td>
    <td><code>manik@rakshak.com</code> / <code>Manik@123</code></td>
  </tr>
  <tr>
    <td align="center"><strong>👤 User Login</strong></td>
    <td><code>keshav@rakshak.com</code> / <code>Keshav@123</code></td>
  </tr>
</table>

---

## ✨ Features

| # | Feature | Description |
|:-:|---------|-------------|
| 🚨 | **SOS Emergency Alert** | Trigger via phone shake, volume button press, or triple-tap — sends instant alerts with GPS location |
| 🗺️ | **Real-time Danger Zone Mapping** | Interactive heatmap of reported incidents and high-risk areas powered by live data |
| 📊 | **AI Threat Engine & Risk Assessment** | Machine-learning-driven threat scoring that analyzes location, time, and historical data |
| 🛡️ | **Safety Score Calculator** | Personalized safety score based on your route, time of day, and area risk profile |
| 🚶 | **Safe Walk Journey Tracking** | Share live location with trusted contacts during walks; auto-alert if you deviate or stop |
| 📞 | **Fake Call Generator** | Instantly simulate an incoming phone call to escape uncomfortable or dangerous situations |
| 🆘 | **Emergency Quick Dial** | One-tap access to Police (100), Women Helpline (1091), Ambulance (102), Fire (101) |
| 💡 | **Safety Tips & Guidelines** | Curated, actionable safety advice for various scenarios |
| 👥 | **Trusted Contacts Management** | Add, manage, and instantly notify your emergency contacts |
| 🔐 | **Google OAuth + Secure Auth** | Passwordless Google sign-in alongside bcrypt-hashed credentials |
| 📱 | **PWA Support** | Install as a native app on any device — works offline with service worker caching |
| 🔔 | **Real-time Notifications** | WebSocket-powered instant alerts for SOS events and zone warnings |
| 📋 | **Evidence Vault** | Document incidents and export detailed PDF reports via ReportLab |
| 🎯 | **Admin Command Center** | Full admin dashboard — manage users, zones, incidents, and system health |

---

## 🏗️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11+, Flask 3.0, Flask-SocketIO, Gunicorn + Eventlet |
| **Database** | MySQL 8.0 (hosted on Railway) |
| **Frontend** | Bootstrap 5.3, Custom CSS, HTML5 Canvas Animations, Three.js Shield |
| **Authentication** | Flask-Login, Google OAuth 2.0 (Authlib), bcrypt |
| **Real-time** | Socket.IO, WebSocket (Eventlet transport) |
| **PDF Reports** | ReportLab, Pillow |
| **Task Scheduling** | APScheduler |
| **Rate Limiting** | Flask-Limiter |
| **Deployment** | Railway, Nixpacks, Docker |
| **PWA** | Service Worker, Web App Manifest |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│   │ PWA App  │  │ Browser  │  │ Mobile   │  │ Service      │   │
│   │ Install  │  │ Client   │  │ Browser  │  │ Worker       │   │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│        └──────────────┴─────────────┴───────────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS + WebSocket
┌────────────────────────────┴────────────────────────────────────┐
│                      SERVER LAYER                               │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Gunicorn + Eventlet WSGI                   │   │
│   └───────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│   ┌───────────────────────┴─────────────────────────────────┐   │
│   │                  Flask Application                      │   │
│   │                                                         │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │   │
│   │  │   Auth   │ │   SOS    │ │ Danger   │ │ Safe Walk │  │   │
│   │  │  Module  │ │  Module  │ │  Zones   │ │  Module   │  │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │   │
│   │  │ AI Threat│ │  Safety  │ │  Admin   │ │ Emergency │  │   │
│   │  │  Engine  │ │  Score   │ │  Panel   │ │  & Calls  │  │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │   │
│   └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│   ┌───────────────────────┴─────────────────────────────────┐   │
│   │            Socket.IO (Eventlet WebSocket)               │   │
│   └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                      DATA LAYER                                 │
│                                                                 │
│   ┌──────────────────────┐  ┌───────────────────────────────┐   │
│   │    MySQL Database    │  │     PDF Report Generator      │   │
│   │   (Railway Hosted)   │  │        (ReportLab)            │   │
│   └──────────────────────┘  └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📸 Screenshots

<p align="center">
  <img src="static/images/screenshot-landing.png" alt="Landing Page" width="45%"/>
  &nbsp;&nbsp;
  <img src="static/images/screenshot-dashboard.png" alt="Dashboard" width="45%"/>
</p>
<p align="center">
  <img src="static/images/screenshot-sos.png" alt="SOS Alert" width="45%"/>
  &nbsp;&nbsp;
  <img src="static/images/screenshot-admin.png" alt="Admin Panel" width="45%"/>
</p>

<p align="center"><em>Screenshots coming soon — visit the <a href="https://rakshak.up.railway.app">live demo</a> to explore!</em></p>

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/RAKSHAK.git
cd RAKSHAK

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (see below)
cp .env.example .env  # Then edit with your values

# Initialize the database
python init_db.py

# Run the application
python app.py
```

The app will be available at `http://localhost:5000`.

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=development

# MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=rakshak

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Railway (production)
RAILWAY_ENVIRONMENT=production
MYSQLHOST=your-railway-mysql-host
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=your-railway-password
MYSQLDATABASE=railway
```

---

## 📂 Project Structure

```
RAKSHAK/
├── app.py                  # Flask app factory & main entry point
├── config.py               # Configuration (env-based)
├── wsgi.py                 # WSGI entry for Gunicorn
├── models.py               # Database models & queries
├── socket_events.py        # Socket.IO event handlers
├── pdf_reports.py          # Evidence vault PDF generation
├── healer.py               # Self-healing & monitoring utilities
├── init_db.py              # Database schema initialization
├── schema.sql              # MySQL schema definitions
│
├── modules/                # Feature modules (Blueprints)
│   ├── admin/              # Admin command center
│   ├── ai_engine/          # AI threat assessment engine
│   ├── auth/               # Authentication (login, register, OAuth)
│   ├── danger_zones/       # Danger zone CRUD & heatmap API
│   ├── emergency/          # Emergency contacts & quick dial
│   ├── fake_call/          # Fake call generator
│   ├── main/               # Dashboard & core routes
│   ├── safe_walk/          # Safe walk journey tracking
│   ├── safety_score/       # Safety score calculator
│   ├── safety_tips/        # Safety tips & guidelines
│   └── sos/                # SOS alert system
│
├── static/
│   ├── css/main.css        # Custom styles
│   ├── js/
│   │   ├── dashboard.js    # Dashboard interactivity
│   │   ├── heatmap.js      # Danger zone heatmap rendering
│   │   ├── sos_triggers.js # Shake, volume, tap SOS triggers
│   │   ├── three_shield.js # Three.js 3D shield animation
│   │   └── admin.js        # Admin panel scripts
│   ├── images/             # Static assets
│   ├── manifest.json       # PWA manifest
│   └── sw.js               # Service worker
│
├── templates/              # Jinja2 HTML templates
│   ├── index.html          # Landing page
│   ├── base.html           # Base layout
│   ├── offline.html        # PWA offline fallback
│   ├── dashboard/          # Dashboard views
│   ├── admin/              # Admin panel views
│   ├── auth/               # Login / register views
│   ├── danger_zones/       # Danger zone views
│   ├── safe_walk/          # Safe walk views
│   └── errors/             # Error pages (404, 500)
│
├── Dockerfile              # Docker build configuration
├── docker-compose.yml      # Local multi-container setup
├── Procfile                # Railway process configuration
├── requirements.txt        # Python dependencies
└── README.md               # You are here!
```

---

## 👨‍💻 Contributors

<table>
  <tr>
    <td align="center">
      <strong>Manik Sahni</strong><br/>
      <em>Lead Developer & Creator</em>
    </td>
    <td align="center">
      <strong>Keshav</strong><br/>
      <em>Developer & Contributor</em>
    </td>
  </tr>
</table>

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Made with ❤️ in India for women's safety</strong>
</p>

<p align="center">
  <em>Because every woman deserves to feel safe — anytime, anywhere.</em>
</p>

<p align="center">
  <a href="https://rakshak.up.railway.app">🌐 Visit RAKSHAK</a>
</p>
