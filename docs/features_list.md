# LifeLine AI — Complete Features List

## Authentication & Security
1. User registration with validation (name, email, phone, password strength).
2. Secure login with hashed passwords + JWT session tokens.
3. Role-based access control (User vs Admin).
4. Protected routes (frontend redirects + backend decorator checks).

## User Features
5. Personal dashboard: profile summary, quick stats, last emergency status.
6. Emergency SOS button (one-tap, big, animated, hard to miss).
7. Real-time GPS location capture via browser Geolocation API.
8. Live location shown on Google Map with user marker.
9. Emergency type selection (medical/fire/accident/crime/other) + optional description.
10. AI severity prediction shown instantly (Low/Medium/High/Critical) with color coding.
11. Fake-alert self-check badge (transparency: shows if system flagged low confidence).
12. Nearest hospital recommendation (name, distance, phone, map route).
13. Nearest police station recommendation (name, distance, phone, map route).
14. Emergency contacts management (add/edit/delete, relationship, phone).
15. Simulated notifications sent to emergency contacts on SOS trigger.
16. Full emergency history table (date, type, severity, status, location).
17. Notification inbox (system + simulated email log).
18. Mobile responsive SOS flow (designed mobile-first, works on any device).

## Admin Features
19. Admin dashboard with live counts (pending/active/resolved emergencies).
20. Real-time emergencies table with filters (status, severity, fake-suspected).
21. Map view of all active emergencies plotted together.
22. Verify / acknowledge / resolve / cancel emergency workflow.
23. User management (view, activate/deactivate).
24. Hospital & police station directory management (CRUD).
25. Admin action audit log.
26. Basic analytics (emergencies by type, by severity, over time).

## AI Features
27. Severity prediction model (RandomForestClassifier, scikit-learn) trained
    on engineered features (type, time of day, description signal, history).
28. Fake-alert detection (hybrid rule-based + IsolationForest anomaly score).
29. Model training script + persisted `.joblib` artifacts, retrainable offline.

## Maps & Geolocation
30. Google Maps JavaScript API integration for live map rendering.
31. Nearby hospitals/police stations via Places API (with haversine fallback
    against the seeded MySQL directory if API key/quota unavailable).
32. Directions/route line from user to selected facility.

## UI/UX
33. Modern, professional, consistent design system (CSS variables, spacing scale).
34. Smooth animations: SOS pulse, page transitions, toast notifications, skeleton loaders.
35. Fully responsive (mobile, tablet, desktop breakpoints).
36. Accessible focus states and semantic HTML.

## Engineering Quality
37. Clean modular Flask blueprint structure.
38. Parameterized SQL, no ORM magic — transparent for a viva/defense.
39. Commented code throughout for FYP documentation/viva purposes.
40. Seed data + schema script for one-command DB setup.
