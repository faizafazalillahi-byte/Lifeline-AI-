-- ============================================================
-- LifeLine AI — Migration 002: Account Security
-- Adds email verification + brute-force lockout support.
--
-- SAFE TO RUN ON AN EXISTING DATABASE — this does NOT drop or
-- recreate any table. It only ADDS new columns. Existing users
-- get is_verified = TRUE automatically (so nobody who already
-- registered gets locked out), and new registrations explicitly
-- set is_verified = FALSE in the application code so they go
-- through the new verification flow.
--
-- Run:
--   mysql -u root -p lifeline_ai < backend/database/migration_002_security.sql
-- ============================================================

USE lifeline_ai;

ALTER TABLE users
  ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT TRUE AFTER is_active,
  ADD COLUMN verification_code VARCHAR(10) DEFAULT NULL AFTER is_verified,
  ADD COLUMN verification_expires DATETIME DEFAULT NULL AFTER verification_code,
  ADD COLUMN failed_login_attempts INT NOT NULL DEFAULT 0 AFTER verification_expires,
  ADD COLUMN locked_until DATETIME DEFAULT NULL AFTER failed_login_attempts;
