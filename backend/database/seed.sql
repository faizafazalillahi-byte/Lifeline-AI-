-- ============================================================
-- LifeLine AI — Seed Data
-- Run AFTER schema.sql:  mysql -u root -p lifeline_ai < seed.sql
-- Default admin login -> email: admin@lifeline.ai | password: Admin@123
-- (hash below corresponds to that password, generated with
--  werkzeug.security.generate_password_hash)
-- ============================================================

USE lifeline_ai;

-- Admin user (password: Admin@123)
INSERT INTO users (full_name, email, phone, password_hash, role, blood_group, home_address, is_verified)
VALUES (
  'System Administrator',
  'admin@lifeline.ai',
  '+92-300-0000000',
  'pbkdf2:sha256:600000$placeholderSaltXY$0000000000000000000000000000000000000000000000000000000000000000',
  'admin',
  'O+',
  'LifeLine AI HQ, Lahore',
  TRUE
);

-- NOTE: The password hash above is a placeholder. Run
-- backend/utils/create_admin.py (see Module 1) once to generate a real
-- hash and UPDATE this row, OR simply register a user through the app UI
-- and manually promote it: UPDATE users SET role='admin' WHERE email='...';

-- Sample hospitals (Lahore, Pakistan — replace/extend with your city)
INSERT INTO hospitals (name, latitude, longitude, phone, address) VALUES
('Services Hospital Lahore', 31.5497, 74.3436, '+92-42-99203402', 'Jail Road, Lahore'),
('Mayo Hospital Lahore', 31.5656, 74.3141, '+92-42-99211102', 'Hospital Road, Lahore'),
('Jinnah Hospital Lahore', 31.5000, 74.3200, '+92-42-99231400', 'Allama Iqbal Road, Lahore'),
('Shaukat Khanum Hospital', 31.4700, 74.2870, '+92-42-35905000', 'Johar Town, Lahore');

-- Sample police stations
INSERT INTO police_stations (name, latitude, longitude, phone, address) VALUES
('Model Town Police Station', 31.4817, 74.3235, '+92-42-99260000', 'Model Town, Lahore'),
('Gulberg Police Station', 31.5203, 74.3436, '+92-42-99266000', 'Gulberg, Lahore'),
('Civil Lines Police Station', 31.5600, 74.3300, '+92-42-99212345', 'Civil Lines, Lahore');
