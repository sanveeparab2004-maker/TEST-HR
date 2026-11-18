# System Architecture & Technical Specifications

This document outlines the architectural blueprints, data flow diagrams, security boundaries, and state machines governing the HR Assessment Portal.

---

## 1. High-Level System Architecture

```mermaid
graph TD
    subgraph Client Tier
        CandBrowser["Candidate Laptop<br/>(React + Vite + MediaPipe WASM)"]
        MonBrowser["Monitor Workstation<br/>(React Live Camera Wall)"]
        AdminBrowser["Admin Console<br/>(Dashboard & Exports)"]
    end

    subgraph Free-Tier Cloud Infrastructure
        subgraph Render Free Web Service
            FastAPI["FastAPI Application Server"]
            WSHandler["WebSocket Signalling & Heartbeat Hub"]
            StaticServer["SPA Static File Delivery"]
        end

        subgraph Neon Free Database
            Postgres[("Neon Serverless PostgreSQL<br/>Schema: assess")]
        end
    end

    subgraph External
        Claude["Anthropic Claude API<br/>(Optional AI Advisory)"]
    end

    CandBrowser -->|"HTTPS REST (Autosave, Violations)"| FastAPI
    CandBrowser <-->|"WebSocket Signalling (/ws/signaling)"| WSHandler
    MonBrowser -->|"HTTPS REST (Audited Actions)"| FastAPI
    MonBrowser <-->|"WebSocket Candidate Feeds"| WSHandler
    AdminBrowser -->|"HTTPS REST (Dashboard, PDF/Excel)"| FastAPI
    FastAPI <-->|"Async SQLAlchemy / Connection Pool"| Postgres
    FastAPI -.->|"De-identified Prompts (Code only)"| Claude

    CandBrowser ===|"P2P WebRTC Direct Video Stream (STUN)"| MonBrowser
```

---

## 2. WebRTC Peer-to-Peer Signalling & Automatic Fallback

Live video monitoring connects candidate webcams directly to the monitor's workstation without burdening the server or exceeding free-tier bandwidth caps.

```mermaid
sequenceDiagram
    autonumber
    actor Candidate as Candidate Laptop
    participant Server as FastAPI WebSocket Signalling
    actor Monitor as Staff Monitor Wall

    Candidate->>Server: Connect WS (/ws/signaling?role=CANDIDATE&attempt_id=X)
    Monitor->>Server: Connect WS (/ws/signaling?role=MONITOR)
    Server-->>Monitor: Candidate Online Notification (Attempt X)
    Monitor->>Server: Send WebRTC Offer (SDP)
    Server->>Candidate: Relay Offer
    Candidate->>Server: Send WebRTC Answer (SDP)
    Server->>Monitor: Relay Answer
    Candidate->>Server: Exchange ICE Candidates
    Server->>Monitor: Relay ICE Candidates
    Candidate==>>Monitor: Direct P2P Video Track Established (STUN)

    Note over Candidate,Monitor: If P2P connection fails within 10s (e.g. Symmetric NAT/Firewall)
    Candidate->>Server: Fallback: Send 240px JPEG Snapshot (every 5s)
    Server->>Monitor: Relay Snapshot Frame (Tagged: 'Snapshot Mode')
```

---

## 3. Proctoring Warning State Machine

The proctoring system implements a human-in-the-loop, non-disqualifying model:

```mermaid
stateDiagram-v2
    [*] --> Clean: Candidate Starts Exam
    Clean --> Warning1: 1st Counted Violation
    Warning1 --> Warning2: 2nd Counted Violation
    Warning2 --> Warning3: 3rd Counted Violation
    Warning3 --> FinalWarning: 4th Counted Violation
    FinalWarning --> PostFinalNoted: 5th+ Counted Violations

    state Warning1 {
        [*] --> Modal1: Blocking Modal Displayed
        Modal1 --> Dismissed1: 3-Second Delay -> 'I Understand' Clicked
    }

    state Warning2 {
        [*] --> Modal2: Blocking Modal Displayed
        Modal2 --> Dismissed2: 3-Second Delay -> 'I Understand' Clicked
    }

    state Warning3 {
        [*] --> Modal3: Severe Warning Modal
        Modal3 --> Dismissed3: 3-Second Delay -> 'I Understand' Clicked
    }

    state FinalWarning {
        [*] --> ModalFinal: Final Warning Modal (Tile Marked Red)
    }

    state PostFinalNoted {
        [*] --> BannerLogged: Persistent Non-Blocking Banner
        BannerLogged --> ProctorReview: Flagged for Human Staff Review
    }

    note right of PostFinalNoted
        CRITICAL RULE:
        Candidate is NEVER auto-disqualified.
        Staff Monitor reviews incidents live.
    end note
```

---

## 4. Database Entity-Relationship Model (Schema: `assess`)

```mermaid
erDiagram
    roster ||--o{ attempts : "has"
    assessments ||--o{ sections : "contains"
    assessments ||--o{ questions : "contains"
    assessments ||--o{ attempts : "evaluated_in"
    sections ||--o{ questions : "groups"
    questions ||--o{ options : "offers"
    attempts ||--o{ answers : "records"
    attempts ||--o{ violations : "incurs"
    attempts ||--o{ snapshots : "captures"
    attempts ||--o{ events : "logs"

    roster {
        citext employee_code PK
        text full_name
        text department
        text role
        text pin_hash
        boolean is_active
    }

    assessments {
        smallint id PK
        text title
        smallint duration_minutes
        smallint total_marks
        smallint marks_per_question
        boolean negative_marking
        text status
        timestamptz opens_at
        timestamptz closes_at
    }

    attempts {
        bigint id PK
        smallint assessment_id FK
        citext employee_code FK
        text entered_name
        text device_token_hash
        jsonb device_info
        text status
        timestamptz started_at
        timestamptz deadline_at
        timestamptz submitted_at
        int[] question_order
        jsonb option_order
        smallint warning_count
        smallint violation_count
        smallint score
        numeric percentage
        text band
        jsonb section_scores
    }

    questions {
        int id PK
        smallint assessment_id FK
        smallint section_id FK
        smallint source_number
        text stem
        smallint marks
    }

    options {
        int id PK
        int question_id FK
        char label
        text text
        boolean is_correct
    }

    answers {
        bigint id PK
        bigint attempt_id FK
        int question_id FK
        int option_id FK
        boolean flagged
        timestamptz saved_at
    }

    violations {
        bigint id PK
        bigint attempt_id FK
        timestamptz at
        text kind
        jsonb details
        boolean counted
        smallint warning_number
        text review_status
        text reviewed_by
        timestamptz reviewed_at
    }

    snapshots {
        bigint id PK
        bigint attempt_id FK
        timestamptz taken_at
        bytea image_data
        text trigger_kind
    }

    audit_log {
        bigint id PK
        timestamptz at
        citext actor
        text action
        text entity
        jsonb detail
    }
```

---

## 5. Free-Tier Optimization & Durability Invariants

1. **Deterministic Question Randomization**:
   When an attempt is initialized, questions and options are randomized once and the resulting permutation arrays (`question_order: int[]` and `option_order: jsonb`) are written to Postgres. On subsequent fetches (e.g. after browser refresh or server reboot), questions are returned in the exact stored order.
2. **Immutable Audit Trail**:
   PostgreSQL trigger `trg_prevent_audit_tampering` raises an exception on any `UPDATE` or `DELETE` attempt against `assess.audit_log`.
3. **Submission State Lock**:
   PostgreSQL trigger `trg_lock_answers_on_submit` rejects any `INSERT` or `UPDATE` on `assess.answers` once the associated attempt's status transitions away from `IN_PROGRESS`.
4. **Neon Scale-to-Zero Connection Resilience**:
   `engine = create_engine(..., pool_size=5, max_overflow=2, pool_pre_ping=True, pool_recycle=300)`. A custom retry wrapper handles cold-start latency transparently.
