/**
 * config.js
 * ---------
 * Central frontend configuration. Change API_BASE_URL if the Flask
 * backend runs on a different host/port, and set your own Google Maps
 * API key before using SOS/map features (Module 5).
 */

const CONFIG = {
  API_BASE_URL: "http://localhost:5000/api",
  GOOGLE_MAPS_API_KEY: "AIzaSyAddxjDOMXCqOVKB1VRrQC1NChCvmfqJYg", // replace before using map features
  TOKEN_STORAGE_KEY: "lifeline_token",
  USER_STORAGE_KEY: "lifeline_user",
};
