# Proctoring Engine & Privacy Compliance Specification

This document details the event detection rules, warning mechanics, false-positive mitigations, and Indian Digital Personal Data Protection (DPDP) Act compliance measures implemented in the HR Assessment Portal.

---

## 1. Proctoring Violation Matrix

| Violation Type | Severity | Counted Towards Warning? | Trigger Criteria | Candidate Experience | Monitor Display |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `TAB_SWITCH` | High | **Yes** | Tab visibility transitions to hidden (`visibilitychange`) | Warning modal appears immediately | Amber/Red ring; timestamped incident in feed |
| `WINDOW_BLUR` | Medium | **Yes** *(After 3s)* | Window loses OS focus (`window.onblur`) for > 3.0 seconds | Warning modal after grace period expires | Timestamped blur duration logged |
| `FULLSCREEN_EXIT` | High | **Yes** | User exits fullscreen (`fullscreenchange`) | Blocking dialog forcing re-entry to fullscreen | Logged with timestamp |
| `SHORTCUT_ATTEMPT` | High | **Yes** | Blocked shortcuts: `Ctrl+C`, `Ctrl+V`, `Alt+Tab`, `F12`, `Ctrl+Shift+I` | Shortcut blocked; warning modal | Logged key combination |
| `MULTIPLE_FACES` | High | **Yes** | MediaPipe WASM detects > 1 face for > 3 consecutive seconds | Warning modal: "Multiple faces detected" | Thumbnail snapshot stored; live tile flagged |
| `FACE_ABSENT` | Medium | **Yes** *(After 5s)* | MediaPipe WASM detects 0 faces for > 5 consecutive seconds | Warning modal: "No face detected in frame" | Thumbnail snapshot stored; live tile flagged |
| `CAMERA_LOST` | High | **No** *(Curtain)* | Webcam track ends, device disconnects, or permission revoked | **Camera-Off Curtain**: Test questions completely obscured | Live tile displays grey disconnected state |
| `HEARTBEAT_TIMEOUT`| High | **No** *(Network)* | No heartbeat received from client for > 30 seconds | "Reconnecting..." status bar banner | Live tile turns grey: "Offline (X s ago)" |

---

## 2. False-Positive Mitigations

To prevent penalizing candidates due to operating system notifications, accidental cursor slips, or brief lighting shifts, the following mitigations are strictly enforced:

1. **Window Blur Grace Period (3 Seconds)**:
   A brief OS notification (e.g. system battery alert or antivirus popup) that steals focus for less than 3 seconds is ignored. Only sustained blurs (> 3.0s) trigger a counted violation.
2. **Face Tracking Debounce (3–5 Seconds)**:
   A momentary sneeze, lighting flicker, or head turn does not raise an alert. Face absence must persist continuously for 5.0 seconds before a violation is logged.
3. **Camera-Off Curtain vs. Disqualification**:
   If the candidate's camera fails or permissions are dropped, the system **does not void or fail** the exam. Instead, a full-screen overlay (the "Curtain") conceals the questions. The candidate can re-enable the camera or reload the page to resume without loss of answers.
4. **Human-in-the-Loop Review**:
   The monitor wall allows human staff to review any flagged incident, inspect the attached snapshot, and toggle the status between `CONFIRMED` or `DISMISSED`. Dismissed violations are marked in the audit log and factored into the candidate's final integrity classification.

---

## 3. Data Privacy & DPDP Act Compliance

The system is designed with Privacy-by-Design principles aligning with the Indian Digital Personal Data Protection (DPDP) Act:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRIVACY BY DESIGN                               │
├────────────────────────────────┬───────────────────────────────────────┤
│ Principle                      │ Technical Implementation              │
├────────────────────────────────┼───────────────────────────────────────┤
│ Edge-Only Biometric Processing │ MediaPipe Face Landmarker runs in     │
│                                │ browser WASM. Raw video never sent to  │
│                                │ server for AI analysis.               │
├────────────────────────────────┼───────────────────────────────────────┤
│ Informed Explicit Consent      │ Candidate cannot enter exam without   │
│                                │ reading rules and checking consent.   │
├────────────────────────────────┼───────────────────────────────────────┤
│ Purpose & Storage Limitation   │ Snapshots limited to max 60 per exam, │
│                                │ rate-limited to 1 per 10s, compressed │
│                                │ to 320px JPEG. No continuous recording│
├────────────────────────────────┼───────────────────────────────────────┤
│ Data Minimization in AI Audits │ AI summaries send only employee code, │
│                                │ score bands, and missed topic strings.│
│                                │ Full names are scrubbed.              │
├────────────────────────────────┼───────────────────────────────────────┤
│ Configurable Retention Purge   │ Automated 90-day retention purge via   │
│                                │ POST /api/admin/purge-retention.       │
└────────────────────────────────┴───────────────────────────────────────┘
```

---

## 4. Free-Tier Storage & Bandwidth Budget

To ensure the system operates reliably within Neon Postgres's 0.5 GiB free storage ceiling:

- **Snapshot File Size**: 320x240 JPEG at quality 60 consumes ~8 KB per frame.
- **Per-Candidate Maximum**: Hard cap of 60 snapshots per attempt = **~480 KB total storage per candidate**.
- **100 Candidates Full Run**: 100 × 480 KB = **~48 MB**, representing less than 10% of Neon's 500 MB allocation.
- **Relayed Snapshot Mode**: When WebRTC fails, 240px snapshots sent every 5 seconds over the WebSocket are relayed in memory to the monitor wall and **never written to the database**.
