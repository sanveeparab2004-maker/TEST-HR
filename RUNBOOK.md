# Exam Day Operations Runbook

This operational runbook provides step-by-step procedures for the HR assessment coordinator, exam monitors, and system administrators on test day.

---

## 1. Exam Timeline Checklist

```
  T - 24 Hours       T - 15 Minutes      T - 5 Minutes          T = 0              T + 60 Minutes      T + 65 Minutes
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐   ┌────────────────┐
│ Roster Freeze│──>│ Service Wake │──>│ Monitor Ready│──>│ Exam Kickoff │──>│ Hard Submission │──>│ Export Archive │
│ & Pilot Test │   │ & DB Pre-warm│   │ & Tile Check │   │ & Live Feed  │   │ & Grade Finalize│   │ Excel, PDF, DB │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └─────────────────┘   └────────────────┘
```

---

## 2. Pre-Exam Procedures (T - 24 Hours to T - 15 Minutes)

### T - 24 Hours: Roster Freeze & Dry Run
1. Obtain the final employee roster CSV from HR Operations.
2. Verify format matching `data/roster_template.csv`:
   - `employee_code` (e.g. `EMP101`)
   - `full_name` (e.g. `Ananya Sen`)
   - `department` (e.g. `HR Talent Acquisition`)
3. Upload roster via terminal or Admin Console:
   ```bash
   python -m scripts.import_roster --csv data/final_roster.csv
   ```
4. Verify question count is exactly 50 and duration is 60 minutes.

### T - 15 Minutes: Instance Wake-Up & DB Warm-Up
Render free tier and Neon Postgres both spin down during inactivity.
1. Open a browser and load the health check endpoint:
   `https://<your-app>.onrender.com/healthz`
2. Wait for the JSON response:
   ```json
   { "status": "healthy", "database": "connected" }
   ```
   *(Note: The first cold load after idle may take 10–20 seconds. This ensures subsequent candidate logins are instantaneous.)*

---

## 3. Exam In-Progress Monitoring (T = 0 to T + 60 Minutes)

### Staff Monitor Station Setup (T - 5 Minutes)
1. Staff member navigates to the portal URL and selects **Admin / Proctor Login**.
2. Authenticate as Monitor:
   - **Code**: `HR_MONITOR_01`
   - **PIN**: `654321`
3. The **Live Camera Wall** will load. As candidates complete system checks, their live video tiles appear automatically.

### Live Tile Color Indicators
- **Green Ring**: Healthy candidate, answering questions, video active, 0 warnings.
- **Amber Ring**: Candidate has incurred 1 to 3 warnings. Monitor should check the incident feed.
- **Red Ring**: Candidate has reached **Final Warning** (4+ violations). Keep tile open and observe behavior.
- **Grey Ring**: Candidate offline or camera disconnected.

### Standard Incident Handling Procedures

#### Incident A: Candidate Accidental Tab-Out / System Notification
- Candidate will see Warning Modal (Warning 1/3 or 2/3).
- 3-second acknowledgement timer prevents rage-clicking.
- Candidate clicks "I Understand" and resumes exam.
- **Action**: Monitor reviews incident in drawer. If confirmed benign, click **Dismiss**.

#### Incident B: Candidate Laptop Dies / Battery Exhaustion
1. Candidate contacts HR Admin on emergency office phone/chat.
2. Candidate moves to backup laptop.
3. Candidate attempts login with their code and name, and sees:
   *"Active session detected on another device."*
4. **Action (Admin Only)**:
   - In **Admin Console** > **Results & Candidate Roster**, find the candidate.
   - Click **Release Device Lock**.
   - Input mandatory reason: *"Laptop battery failure, switched to spare laptop."*
   - Click **Confirm Release**.
5. Candidate refreshes page on new laptop, logs in immediately, and resumes from their exact saved state.

#### Incident C: Webcam Connection Lost / Black Screen
- Candidate screen displays the **Camera-Off Curtain** obscuring questions.
- **Action**: Candidate should check physical camera slider, refresh browser, and allow camera permission. As soon as video track re-engages, curtain lifts automatically.

---

## 4. Post-Exam Procedures (T + 60 Minutes to T + 65 Minutes)

### Hard Submission & Finalization
- At the 60-minute mark, remaining candidate exams are automatically submitted by the server.
- The grading engine scores all 50 questions deterministically and assigns performance bands:
  - **85 – 100**: *Excellent (Strong practical understanding)*
  - **70 – 84**: *Good (Minor areas for improvement)*
  - **50 – 69**: *Needs Improvement (Further guidance recommended)*
  - **Below 50**: *Requires Training (Reassessment recommended)*

### Data Archive & Export (Admin Station)
1. In the **Admin Console**, click the three export actions:
   - **Export Results (Excel)**: Downloads `HR_Assessment_Results_<timestamp>.xlsx` containing complete candidate scores, section breakdowns, and integrity classifications.
   - **Download Backup Dump**: Downloads full JSON database dump for permanent offline retention.
   - For specific candidates requiring detailed talent reviews, click **Download PDF Scorecard**.
2. Securely copy the exported archives to corporate HR SharePoint / Google Drive.
