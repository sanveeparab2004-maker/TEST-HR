# HR Assessment Portal — Secure Online Proctored Test

A production-grade, secure, proctored assessment portal engineered for enterprise HR talent evaluation. Specifically tailored to run within the constraints of free-tier cloud infrastructure (**Render Free Web Service** + **Neon Serverless PostgreSQL**).

---

## Key Capabilities & Highlights

- **Intermediate HR MCQ Assessment**: 50 questions, 2 marks each (100 total marks), 4 options (A–D), no negative marking, divided into 7 core competencies:
  1. *Recruitment Planning* (Q1–5)
  2. *Sourcing & Screening* (Q6–10)
  3. *Interview Management* (Q11–15)
  4. *Offer & Joining* (Q16–20)
  5. *HR Operations* (Q21–30)
  6. *Excel & MIS* (Q31–40)
  7. *Communication & Judgement* (Q41–50)
- **Strict 60-Minute Enforced Duration**: Server-authoritative countdown (`started_at + 60 min`). Deadlines and remaining time are evaluated and stored in database UTC. Browser clock manipulation is impossible.
- **Single-Device Lockdown**: Candidates are locked to their initial device via cryptographic device token hashes stored in HttpOnly cookies and LocalStorage. Resumption on the same machine is seamless; unauthorized secondary logins are blocked with HTTP 403 unless released by an Admin.
- **In-Browser Face Landmarking (WASM)**: Powered by MediaPipe Vision running entirely in the candidate's browser. Raw webcam video never leaves the laptop for ML processing, satisfying strict data privacy and Indian DPDP Act compliance.
- **Peer-to-Peer Live Proctoring (WebRTC)**: Direct P2P video stream from candidate laptop to the Monitor's browser over STUN signalling via FastAPI WebSockets. Zero third-party media server overhead.
- **Automatic Snapshot Mode Fallback**: If network NAT/firewall prevents a P2P WebRTC connection within 10 seconds, the client automatically switches to sending low-bandwidth 240px JPEG frames every 5s over the WebSocket, labelled "Snapshot mode".
- **Human-in-the-Loop Proctoring**: The system **never auto-disqualifies** candidates. Violations trigger an escalating warning state machine (Warnings 1/3, 2/3, 3/3 with a 3-second acknowledgement lock, Final Warning, and ongoing incident logging). Monitored live by staff proctors with audited dismiss/confirm capabilities.
- **Robust Restart-Safe Architecture**: Fully resilient to Render free instance idling and restarts. All exam state (answers, deadlines, shuffled question orders, warning tallies) lives in Postgres. Clients auto-reconnect with local offline retry queues.
- **Zero Answer Leakage Guarantee**: The correct answer key (`is_correct`) is completely stripped from all Candidate and Monitor APIs, and absent from compiled client bundle assets.
- **Comprehensive Admin Analytics & Exports**: Item analysis, candidate performance bands, formatted Excel exports (`openpyxl`), automated PDF candidate scorecards (`reportlab`), JSON system backups, and optional privacy-scrubbed Claude AI talent analysis.

---

## User Roles & Journeys

```
               ┌──────────────────────────────┐
               │    HR Assessment Portal      │
               └──────────────┬───────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
   [CANDIDATE]            [MONITOR]             [ADMIN]
   • Code & Name Login    • Code & 6-Digit PIN • Code & 6-Digit PIN
   • Single-Device Lock   • Live Camera Wall   • Live Results Grid
   • Rules & DPDP Consent • WebRTC + Fallback  • Question Bank Audit
   • Camera & Mic Check   • Warning Timeline   • Device-Lock Reset
   • 60-Min Shuffled Test • Dismiss / Confirm  • PDF / Excel Export
   • Auto-Save & Reconnect• Proctor Broadcast  • AI Performance Note
```

---

## Tech Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3.12, FastAPI, WebSockets | Async IO performance, type validation, native WS signalling |
| **Database** | PostgreSQL (Neon Free), SQLAlchemy 2.0, Alembic | ACID transactions, advisory locks, partial indices, CITEXT |
| **Security** | Argon2id, PyJWT, Cryptographic Token Hashes | High-entropy password and token hashing |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS | High performance, tiny bundle footprint (< 100 KB gzipped) |
| **Vision ML** | Google MediaPipe Tasks Vision (WASM) | Client-side facial tracking; no server GPU required |
| **Reporting** | OpenPyXL, ReportLab | Programmatic XLSX and PDF generation without heavy OS binaries |
| **Testing** | Pytest, AnyIO | 100% automated test coverage across all layers |

---

## Quickstart & Local Development

### 1. Backend Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env

# Run database migrations
alembic upgrade head

# Import questions and seed users
python -m scripts.import_questions --docx data/HR_Team_Professional_Assessment.docx
python -m scripts.seed_admins
python -m scripts.import_roster --csv data/roster_template.csv

# Launch API server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# App will run at http://localhost:5173 (proxied to http://localhost:8000)
```

### 3. Run Automated Tests
```bash
# Execute full test suite
python -m pytest tests -v
```

---

## Default Seed Credentials

| Role | Username / Code | Password / PIN | Description |
| :--- | :--- | :--- | :--- |
| **Admin** | `HR_ADMIN_01` | `987123` | Full administrative console access |
| **Monitor** | `HR_MONITOR_01` | `654321` | Live proctoring wall and incident review |
| **Candidate 1** | `EMP001` | *(Full Name: Aarav Sharma)* | Registered roster candidate |
| **Candidate 2** | `EMP002` | *(Full Name: Diya Patel)* | Registered roster candidate |
| **Candidate 3** | `EMP003` | *(Full Name: Rohan Verma)* | Registered roster candidate |

---

## Honest Trade-offs & Limitations

1. **Free-Tier Cold Starts**: Neon scales to zero after 5 minutes of inactivity; Render spins down after 15 minutes. The initial request can take 10–20 seconds to wake. **Mitigation**: Follow the pre-exam checklist in `RUNBOOK.md` to ping `/healthz` 15 minutes before the exam window.
2. **Single-Worker Signalling**: WebRTC peer signalling state is kept in-process (`SignalingManager`). Running multiple container replicas would require an external Redis pub/sub. On Render free tier, exactly **1 instance** must be maintained.
3. **P2P NAT Constraints**: Public Google STUN servers resolve 85%+ of standard network topologies. Symmetric corporate firewalls blocking UDP will gracefully fall back to **Snapshot Mode** (240px JPEG over WebSocket).
4. **Snapshot Storage Budget**: Storing high-resolution continuous video would exceed Neon's 0.5 GiB free tier within minutes. We enforce a 10-second rate limit, 320px JPEG compression, and a ceiling of 60 snapshots per candidate attempt.
