# LifeLine AI — System Architecture

## 1. Overview
LifeLine AI is a web-based Intelligent Emergency Response and Real-Time Safety
Management System. Users can raise an SOS in one tap, get their live GPS
location shared with emergency contacts and the admin/response team, receive
an AI-generated severity score for their emergency, get routed to the nearest
hospital/police station on Google Maps, and review their emergency history.
Admins get a control-tower dashboard to monitor, verify, and respond to all
incoming alerts in real time.

## 2. High-Level Architecture (3-Tier)

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT TIER                              │
│  HTML5 + CSS3 + Vanilla JS (SPA-style multi-page app)             │
│  - Login/Register  - User Dashboard  - Admin Dashboard            │
│  - SOS Button       - Live Map (Google Maps JS API)                │
│  Communicates over REST (fetch/JSON) + Geolocation API             │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ HTTPS / JSON (REST API)
┌───────────────────────────────▼───────────────────────────────────┐
│                        APPLICATION TIER                           │
│  Python Flask (Blueprints)                                        │
│  - auth_routes     : register / login / logout / session (JWT)     │
│  - user_routes      : profile, contacts, history                    │
│  - emergency_routes : SOS create, location update, status           │
│  - admin_routes     : manage users, view/verify alerts, analytics    │
│  AI Layer (Scikit-learn, loaded in-process)                         │
│  - severity_model.py       -> predicts Low/Medium/High/Critical      │
│  - fake_alert_detector.py  -> flags likely-fake SOS signals           │
│  Utils: db.py (MySQL connector pool), email_service.py (simulated),   │
│         auth_utils.py (password hashing, JWT)                        │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ SQL (mysql-connector-python)
┌───────────────────────────────▼───────────────────────────────────┐
│                          DATA TIER                                │
│  MySQL 8.x                                                         │
│  users, emergency_contacts, emergencies, emergency_locations,        │
│  hospitals, police_stations, notifications, admin_logs               │
└─────────────────────────────────────────────────────────────────────┘

  External: Google Maps JavaScript API + Places/Directions API
            (nearby hospitals/police, live map, routing)
```

## 3. Component Responsibilities

| Layer | Component | Responsibility |
|---|---|---|
| Frontend | auth.js | Handles login/register form validation & API calls |
| Frontend | dashboard.js | Renders user stats, contacts, history |
| Frontend | sos.js | Captures GPS, triggers SOS, polls status |
| Frontend | map.js | Renders Google Map, markers, nearest hospital/police |
| Backend | auth_routes.py | JWT-based session issuing & verification |
| Backend | emergency_routes.py | Create/update emergencies, attach AI predictions |
| Backend | admin_routes.py | Admin-only CRUD & analytics endpoints |
| AI | severity_model.py | Scikit-learn classifier: Low/Medium/High/Critical |
| AI | fake_alert_detector.py | Rule + ML hybrid to flag suspicious alerts |
| DB | MySQL | Persistent storage, relational integrity, audit trail |

## 4. Security
- Passwords hashed with Werkzeug's `generate_password_hash` (PBKDF2-SHA256).
- JWT access tokens (short-lived) for stateless auth; role claim (`user`/`admin`).
- Parameterized SQL queries everywhere (no string-concatenated SQL).
- CORS restricted to the frontend origin.
- Server-side validation on every endpoint in addition to client-side checks.

## 5. Tech Stack
- Frontend: HTML5, CSS3 (custom, no framework), Vanilla JavaScript (ES6+)
- Backend: Python 3.10+, Flask, Flask-CORS, PyJWT
- Database: MySQL 8.x, mysql-connector-python
- AI: scikit-learn (RandomForestClassifier for severity, IsolationForest +
  rules for fake-alert detection), joblib for model persistence
- Maps: Google Maps JavaScript API, Places API (nearby search), Directions API
- Notifications: simulated email (logged + stored in `notifications` table,
  swappable for real SMTP later)
