# LifeLine AI — Development Roadmap (Build Order)

We build module by module. Each module = working code, no stubs left behind.

## Module 0 — Foundations (this step)
- Architecture, folder structure, ER diagram, DFD, features list, roadmap.
- MySQL schema (`schema.sql`) + seed data (`seed.sql`).

## Module 1 — Backend Core + Auth
- `config.py`, `utils/db.py`, `utils/auth_utils.py`
- `models/user_model.py`
- `routes/auth_routes.py` (register/login/me)
- `app.py` entry point wired with blueprints + CORS
- `requirements.txt`

## Module 2 — Frontend Design System + Auth Pages
- `css/style.css` (design tokens, layout, components, animations)
- `css/auth.css`
- `login.html`, `register.html`, `index.html`
- `js/config.js`, `js/main.js`, `js/auth.js`

## Module 3 — User Dashboard + Emergency Contacts
- `models/contact_model.py`, `routes/user_routes.py`
- `user_dashboard.html`, `css/dashboard.css`, `js/dashboard.js`

## Module 4 — AI Layer (Severity + Fake Alert Detection)
- `ai/train_severity_model.py` (synthetic training data generation + training)
- `ai/severity_model.py`, `ai/fake_alert_detector.py`
- Saved model artifacts

## Module 5 — SOS + Emergency Engine + Maps
- `models/emergency_model.py`, `models/facility_model.py`
- `routes/emergency_routes.py`, `routes/facility_routes.py`
- `sos.html`, `css/sos.css`, `js/sos.js`, `js/map.js`
- Google Maps integration + nearest hospital/police logic

## Module 6 — Notifications
- `models/notification_model.py`, `utils/email_service.py`
- Wired into SOS flow + notification inbox UI

## Module 7 — Admin Dashboard
- `routes/admin_routes.py`
- `admin_dashboard.html`, `js/admin.js`
- Live emergency table, map of all alerts, user management, analytics

## Module 8 — Polish & Integration Pass
- Cross-check every API call against every route.
- Animation pass, responsive QA, error states, loading states.
- Final README with setup instructions (MySQL, Flask, Google Maps key).

---
**Next step after this message:** Module 1 (Backend Core + Auth) and the
MySQL schema, delivered as complete, working files.
