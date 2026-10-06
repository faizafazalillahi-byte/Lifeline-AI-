# LifeLine AI
### An Intelligent Emergency Response and Real-Time Safety Management System

A Final Year Project: one-tap SOS with AI-scored severity, fake-alert
detection, nearest hospital/police routing via Google Maps, emergency
contact notification, and a full admin response console.

**Tech stack:** HTML5 / CSS3 / Vanilla JS &middot; Python Flask &middot; MySQL &middot; Scikit-learn &middot; Google Maps API

See `docs/` for the architecture, ER diagram, DFD, features list, and
build roadmap that this project was developed against.

---

## 1. Prerequisites
- Python 3.10+
- MySQL 8.x (running locally or reachable remotely)
- A modern browser
- (Optional, for live maps) a Google Maps JavaScript API key with the
  Maps JavaScript API + Places API enabled

## 2. Database setup
```bash
mysql -u root -p < backend/database/schema.sql
mysql -u root -p lifeline_ai < backend/database/seed.sql
```
This creates the `lifeline_ai` database, all 8 tables, sample
hospitals/police stations, and a placeholder admin row.

## 3. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set your DB credentials as environment variables if they differ from
the defaults (`root` / empty password / `localhost`):
```bash
export LIFELINE_DB_USER=root
export LIFELINE_DB_PASSWORD=yourpassword
export LIFELINE_DB_NAME=lifeline_ai
export LIFELINE_JWT_SECRET=some-long-random-string
```

Create a real admin login (replaces the placeholder hash from seed.sql):
```bash
python create_admin.py
```

Train the AI models explicitly (optional — they auto-train on first
use otherwise, but running this yourself lets you see the
classification report for your FYP writeup/viva):
```bash
python -m ai.train_severity_model
```

Run the server:
```bash
python app.py
```
The API now listens on `http://localhost:5000`. Check `http://localhost:5000/api/health`.

## 4. Frontend setup
The frontend is static HTML/CSS/JS — no build step. Two options:

**Option A — just open the files:**
Open `frontend/index.html` directly in your browser.

**Option B — serve it (recommended, avoids some browser file:// quirks):**
```bash
cd frontend
python -m http.server 8080
```
Then visit `http://localhost:8080`.

If you enabled a Google Maps key, put it in `frontend/js/config.js`:
```js
GOOGLE_MAPS_API_KEY: "your-real-key-here",
```
Without a key, the SOS map screen gracefully falls back to a text
summary + "Open in Google Maps" link — nothing breaks.

## 5. Using the app
1. Register a user account on `register.html`.
2. Add a couple of emergency contacts from the dashboard.
3. Click "Raise SOS", allow location permission, and trigger it —
   watch the AI severity score, nearest hospital/police, and
   (in your Flask console) the simulated email/SMS notifications print.
4. Log in as the admin account (`python create_admin.py` output) at
   `login.html`, and you'll land on `admin_dashboard.html` — monitor
   the alert live, change its status, and see the audit log update.

## 6. Project structure
See `docs/folder_structure.txt` for the annotated full tree.

## 7. Notes for your FYP report/viva
- `docs/architecture.md`, `ER_diagram.txt`, and `DFD.txt` are written
  in plain text/markdown specifically so they can be pasted into a
  report or redrawn in draw.io/Lucidchart.
- `ai/train_severity_model.py` documents exactly how the synthetic
  training data is generated and why — this is the section to walk an
  examiner through if asked "where did your training data come from?"
- All SQL is hand-written and parameterized (no ORM), so every query
  in `models/*.py` is easy to explain line-by-line if asked.
