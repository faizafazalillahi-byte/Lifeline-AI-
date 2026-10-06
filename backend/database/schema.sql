-- ============================================================
-- LifeLine AI — MySQL Schema
-- Run:  mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS lifeline_ai
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE lifeline_ai;

-- ------------------------------------------------------------
-- USERS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,
    phone          VARCHAR(20)  NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    role           ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    blood_group    VARCHAR(5)  DEFAULT NULL,
    home_address   VARCHAR(255) DEFAULT NULL,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified    BOOLEAN NOT NULL DEFAULT FALSE,
    verification_code     VARCHAR(10) DEFAULT NULL,
    verification_expires   DATETIME DEFAULT NULL,
    failed_login_attempts  INT NOT NULL DEFAULT 0,
    locked_until    DATETIME DEFAULT NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- EMERGENCY CONTACTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emergency_contacts (
    contact_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    contact_name   VARCHAR(100) NOT NULL,
    contact_phone  VARCHAR(20) NOT NULL,
    relationship   VARCHAR(50) DEFAULT NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_contacts_user (user_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- HOSPITALS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hospitals (
    hospital_id  INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(150) NOT NULL,
    latitude     DECIMAL(10,7) NOT NULL,
    longitude    DECIMAL(10,7) NOT NULL,
    phone        VARCHAR(20) DEFAULT NULL,
    address      VARCHAR(255) DEFAULT NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- POLICE STATIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS police_stations (
    station_id   INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(150) NOT NULL,
    latitude     DECIMAL(10,7) NOT NULL,
    longitude    DECIMAL(10,7) NOT NULL,
    phone        VARCHAR(20) DEFAULT NULL,
    address      VARCHAR(255) DEFAULT NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- EMERGENCIES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emergencies (
    emergency_id        INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT NOT NULL,
    emergency_type      ENUM('medical','fire','accident','crime','other') NOT NULL,
    description         TEXT DEFAULT NULL,
    latitude            DECIMAL(10,7) NOT NULL,
    longitude           DECIMAL(10,7) NOT NULL,
    severity_level      ENUM('Low','Medium','High','Critical') DEFAULT NULL,
    severity_score      FLOAT DEFAULT NULL,
    is_fake_suspected   BOOLEAN NOT NULL DEFAULT FALSE,
    fake_score          FLOAT DEFAULT NULL,
    status              ENUM('pending','acknowledged','in_progress','resolved','cancelled')
                         NOT NULL DEFAULT 'pending',
    nearest_hospital_id INT DEFAULT NULL,
    nearest_police_id   INT DEFAULT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at         DATETIME DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (nearest_hospital_id) REFERENCES hospitals(hospital_id) ON DELETE SET NULL,
    FOREIGN KEY (nearest_police_id) REFERENCES police_stations(station_id) ON DELETE SET NULL,
    INDEX idx_emergencies_user (user_id),
    INDEX idx_emergencies_status (status),
    INDEX idx_emergencies_created (created_at)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- EMERGENCY LOCATIONS (live GPS trail)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emergency_locations (
    location_id   INT AUTO_INCREMENT PRIMARY KEY,
    emergency_id  INT NOT NULL,
    latitude      DECIMAL(10,7) NOT NULL,
    longitude     DECIMAL(10,7) NOT NULL,
    recorded_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (emergency_id) REFERENCES emergencies(emergency_id) ON DELETE CASCADE,
    INDEX idx_locations_emergency (emergency_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- NOTIFICATIONS (simulated email / system)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT NOT NULL,
    emergency_id      INT DEFAULT NULL,
    channel           ENUM('email_sim','sms_sim','system') NOT NULL DEFAULT 'system',
    message           TEXT NOT NULL,
    is_read           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (emergency_id) REFERENCES emergencies(emergency_id) ON DELETE CASCADE,
    INDEX idx_notifications_user (user_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- ADMIN LOGS (audit trail)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_logs (
    log_id       INT AUTO_INCREMENT PRIMARY KEY,
    admin_id     INT NOT NULL,
    action       VARCHAR(255) NOT NULL,
    target_type  VARCHAR(50) DEFAULT NULL,
    target_id    INT DEFAULT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;
