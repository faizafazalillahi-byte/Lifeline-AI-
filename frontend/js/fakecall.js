/**
 * fakecall.js
 * -----------
 * Safety feature: lets a user discreetly trigger a realistic fake
 * incoming call to help them exit an uncomfortable or unsafe situation.
 * Entirely client-side — no real telephony, no backend call needed.
 */

let _fakeCallVibrateInterval = null;
let _fakeCallAudioCtx = null;
let _fakeCallRingInterval = null;
let _fakeCallTimerInterval = null;
let _fakeCallSeconds = 0;

const FAKE_CALLERS = [
  { name: "Mom", initials: "M" },
  { name: "Dad", initials: "D" },
  { name: "Boss", initials: "B" },
  { name: "Police Dept.", initials: "P" },
];

document.addEventListener("DOMContentLoaded", () => {
  injectFakeCallMarkup();
  wireFakeCallEvents();
});

/* ---------------------------------------------------------------------
   Inject the trigger button + picker sheet + call overlay into the page
   (kept in JS so any page can just include this one script to get it).
   --------------------------------------------------------------------- */
function injectFakeCallMarkup() {
  const trigger = document.createElement("button");
  trigger.className = "fakecall-trigger";
  trigger.id = "fakecall-trigger-btn";
  trigger.innerHTML = `
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
    <span class="label-text">Fake Call</span>
  `;
  document.body.appendChild(trigger);

  const pickerOverlay = document.createElement("div");
  pickerOverlay.className = "fakecall-picker-overlay";
  pickerOverlay.id = "fakecall-picker-overlay";
  pickerOverlay.innerHTML = `
    <div class="fakecall-picker-box">
      <h3>Trigger a Fake Call</h3>
      <p>A realistic incoming call will appear after the delay you choose — useful for exiting an uncomfortable situation discreetly.</p>
      <div class="fakecall-option-list" id="fakecall-option-list"></div>
      <div class="fakecall-delay-row">
        Ring after:
        <select id="fakecall-delay-select">
          <option value="3">3 seconds</option>
          <option value="10" selected>10 seconds</option>
          <option value="30">30 seconds</option>
          <option value="60">1 minute</option>
        </select>
      </div>
      <button type="button" class="btn btn-outline btn-block" id="fakecall-cancel-btn">Cancel</button>
    </div>
  `;
  document.body.appendChild(pickerOverlay);

  const callOverlay = document.createElement("div");
  callOverlay.className = "fakecall-overlay";
  callOverlay.id = "fakecall-overlay";
  callOverlay.innerHTML = `
    <div class="fakecall-status" id="fakecall-status-text">Incoming call</div>
    <div>
      <div class="fakecall-avatar" id="fakecall-avatar-initials">M</div>
      <div class="fakecall-name" id="fakecall-name-text">Mom</div>
      <div class="fakecall-sub">Mobile</div>
      <div class="fakecall-timer" id="fakecall-timer" style="display:none;">00:00</div>
    </div>
    <div>
      <div class="fakecall-actions" id="fakecall-ringing-actions">
        <button class="fakecall-btn decline" id="fakecall-decline-btn">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="#fff" stroke="none"><path d="M21.71 5.29a1 1 0 0 0-1.42 0L12 13.59 3.71 5.29a1 1 0 0 0-1.42 1.42L10.59 15l-8.3 8.29a1 1 0 1 0 1.42 1.42L12 16.41l8.29 8.3a1 1 0 0 0 1.42-1.42L13.41 15l8.3-8.29a1 1 0 0 0 0-1.42z"/></svg>
        </button>
        <button class="fakecall-btn answer" id="fakecall-answer-btn">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="#fff" stroke="none"><path d="M6.62 10.79a15.05 15.05 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.01-.24 11.36 11.36 0 0 0 3.57.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11.36 11.36 0 0 0 .57 3.57 1 1 0 0 1-.25 1l-2.2 2.22z"/></svg>
        </button>
      </div>
      <div class="fakecall-actions-label"><span>Decline</span><span>Answer</span></div>

      <div class="fakecall-actions" id="fakecall-incall-actions" style="display:none;">
        <button class="fakecall-btn end" id="fakecall-end-btn">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="#fff" stroke="none"><path d="M21.71 5.29a1 1 0 0 0-1.42 0L12 13.59 3.71 5.29a1 1 0 0 0-1.42 1.42L10.59 15l-8.3 8.29a1 1 0 1 0 1.42 1.42L12 16.41l8.29 8.3a1 1 0 0 0 1.42-1.42L13.41 15l8.3-8.29a1 1 0 0 0 0-1.42z"/></svg>
        </button>
      </div>
      <div class="fakecall-actions-label" id="fakecall-incall-label" style="display:none;"><span>End</span></div>
    </div>
  `;
  document.body.appendChild(callOverlay);

  document.getElementById("fakecall-option-list").innerHTML = FAKE_CALLERS.map((c, i) => `
    <button type="button" class="fakecall-option" data-index="${i}">
      <span class="avatar-dot">${c.initials}</span> ${c.name}
    </button>
  `).join("");
}

/* ---------------------------------------------------------------------
   Wiring
   --------------------------------------------------------------------- */
function wireFakeCallEvents() {
  document.getElementById("fakecall-trigger-btn").addEventListener("click", () => {
    document.getElementById("fakecall-picker-overlay").classList.add("show");
  });
  document.getElementById("fakecall-cancel-btn").addEventListener("click", () => {
    document.getElementById("fakecall-picker-overlay").classList.remove("show");
  });

  document.querySelectorAll(".fakecall-option").forEach((btn) => {
    btn.addEventListener("click", () => {
      const caller = FAKE_CALLERS[parseInt(btn.dataset.index, 10)];
      const delaySeconds = parseInt(document.getElementById("fakecall-delay-select").value, 10);
      document.getElementById("fakecall-picker-overlay").classList.remove("show");
      showToast(`Fake call from ${caller.name} scheduled in ${delaySeconds}s`, "success");
      setTimeout(() => startFakeCall(caller), delaySeconds * 1000);
    });
  });

  document.getElementById("fakecall-decline-btn").addEventListener("click", endFakeCall);
  document.getElementById("fakecall-end-btn").addEventListener("click", endFakeCall);
  document.getElementById("fakecall-answer-btn").addEventListener("click", answerFakeCall);
}

/* ---------------------------------------------------------------------
   Call lifecycle
   --------------------------------------------------------------------- */
function startFakeCall(caller) {
  document.getElementById("fakecall-name-text").innerText = caller.name;
  document.getElementById("fakecall-avatar-initials").innerText = caller.initials;
  document.getElementById("fakecall-status-text").innerText = "Incoming call";
  document.getElementById("fakecall-ringing-actions").style.display = "flex";
  document.getElementById("fakecall-incall-actions").style.display = "none";
  document.getElementById("fakecall-incall-label").style.display = "none";
  document.getElementById("fakecall-timer").style.display = "none";
  document.querySelectorAll(".fakecall-actions-label")[0].style.display = "flex";

  document.getElementById("fakecall-overlay").classList.add("show");

  _startVibration();
  _startRingtone();
}

function answerFakeCall() {
  _stopVibration();
  _stopRingtone();

  document.getElementById("fakecall-status-text").innerText = "";
  document.getElementById("fakecall-ringing-actions").style.display = "none";
  document.querySelectorAll(".fakecall-actions-label")[0].style.display = "none";
  document.getElementById("fakecall-incall-actions").style.display = "flex";
  document.getElementById("fakecall-incall-label").style.display = "flex";
  document.getElementById("fakecall-timer").style.display = "block";

  _fakeCallSeconds = 0;
  _fakeCallTimerInterval = setInterval(() => {
    _fakeCallSeconds++;
    const mins = String(Math.floor(_fakeCallSeconds / 60)).padStart(2, "0");
    const secs = String(_fakeCallSeconds % 60).padStart(2, "0");
    document.getElementById("fakecall-timer").innerText = `${mins}:${secs}`;
  }, 1000);
}

function endFakeCall() {
  _stopVibration();
  _stopRingtone();
  clearInterval(_fakeCallTimerInterval);
  document.getElementById("fakecall-overlay").classList.remove("show");
}

/* ---------------------------------------------------------------------
   Vibration + ringtone (best-effort — silently no-ops where unsupported)
   --------------------------------------------------------------------- */
function _startVibration() {
  if (!("vibrate" in navigator)) return;
  navigator.vibrate([600, 400]);
  _fakeCallVibrateInterval = setInterval(() => navigator.vibrate([600, 400]), 1800);
}
function _stopVibration() {
  clearInterval(_fakeCallVibrateInterval);
  if ("vibrate" in navigator) navigator.vibrate(0);
}

function _startRingtone() {
  try {
    _fakeCallAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const playTone = () => {
      const osc = _fakeCallAudioCtx.createOscillator();
      const gain = _fakeCallAudioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(950, _fakeCallAudioCtx.currentTime);
      gain.gain.setValueAtTime(0.18, _fakeCallAudioCtx.currentTime);
      osc.connect(gain);
      gain.connect(_fakeCallAudioCtx.destination);
      osc.start();
      osc.stop(_fakeCallAudioCtx.currentTime + 0.4);
    };
    playTone();
    _fakeCallRingInterval = setInterval(playTone, 1800);
  } catch (e) {
    // Audio blocked/unavailable — vibration + visual overlay still work.
  }
}
function _stopRingtone() {
  clearInterval(_fakeCallRingInterval);
  if (_fakeCallAudioCtx) {
    _fakeCallAudioCtx.close();
    _fakeCallAudioCtx = null;
  }
}
