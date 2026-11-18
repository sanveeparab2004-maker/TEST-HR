"""Script to generate standard HR_Team_Professional_Assessment.docx for testing and verification."""
import os
from docx import Document

CHECKSUM = {
    1: 'A', 2: 'C', 3: 'B', 4: 'B', 5: 'C', 6: 'D', 7: 'C', 8: 'D', 9: 'B', 10: 'B',
    11: 'B', 12: 'B', 13: 'A', 14: 'A', 15: 'B', 16: 'C', 17: 'C', 18: 'D', 19: 'A', 20: 'D',
    21: 'A', 22: 'C', 23: 'C', 24: 'A', 25: 'A', 26: 'A', 27: 'D', 28: 'A', 29: 'A', 30: 'A',
    31: 'A', 32: 'A', 33: 'C', 34: 'A', 35: 'B', 36: 'A', 37: 'D', 38: 'B', 39: 'B', 40: 'C',
    41: 'B', 42: 'A', 43: 'D', 44: 'B', 45: 'B', 46: 'B', 47: 'A', 48: 'B', 49: 'D', 50: 'D'
}

SECTIONS = [
    ("Recruitment Planning", 1, 5),
    ("Sourcing & Screening", 6, 10),
    ("Interview Management", 11, 15),
    ("Offer & Joining", 16, 20),
    ("HR Operations", 21, 30),
    ("Excel & MIS", 31, 40),
    ("Communication & Judgement", 41, 50),
]

STEMS = {
    1: "Which metric best evaluates the overall hiring velocity of the talent acquisition pipeline?",
    2: "When conducting headcount planning, what is the primary baseline document required?",
    3: "What is the key purpose of a Job Description (JD) alignment session with hiring managers?",
    4: "Which factor should primarily determine whether to recruit internally or externally?",
    5: "What is the recommended replacement hiring lead time buffer for critical technical roles?",
    6: "Which Boolean operator is used to narrow candidate search results by requiring multiple keywords?",
    7: "What is the most effective proactive talent sourcing method for niche leadership positions?",
    8: "During resume screening, which red flag indicates an urgent need for verification?",
    9: "What does an ATS pipeline drop-off rate between screen and first interview usually indicate?",
    10: "Which parameter is critical when benchmarking compensation packages during sourcing?",
    11: "What is the primary advantage of structured behavioral interviews over unstructured chats?",
    12: "Which method prevents interviewer cognitive bias during sequential interview panels?",
    13: "What is the STAR method commonly used for in competency-based evaluations?",
    14: "When a candidate requests salary renegotiation mid-process, what is the best HR response?",
    15: "How should an interviewer handle a situation where a candidate provides conflicting work dates?",
    16: "What is the critical legal safeguard required in a formal Employment Offer Letter?",
    17: "Which metric tracks the percentage of extended offers successfully accepted by candidates?",
    18: "What action must HR take immediately upon receiving a signed acceptance letter?",
    19: "How can pre-boarding engagement reduce Day-1 candidate no-show rates?",
    20: "Which document constitutes formal proof of release from a candidate's previous employer?",
    21: "Under standard statutory compliance, what is the typical employer contribution mandate for PF?",
    22: "What is the legal timeline limit for issuing Form 16 to employees post fiscal year closure?",
    23: "Which record is mandatory to maintain for verifying daily shift attendance and overtime?",
    24: "What constitutes the core principle of Natural Justice during an internal POSH inquiry?",
    25: "How should an employee grievance regarding leave deduction discrepancy be handled?",
    26: "What is the standard retention period required for candidate and employee personnel files?",
    27: "Which payroll component is strictly non-taxable subject to actual rent receipts?",
    28: "What is the mandatory notice period clause for probationers in standard employment contracts?",
    29: "When executing an involuntary separation, which document formalizes the full & final closure?",
    30: "What is the primary objective of an annual HR Compliance and Process Audit?",
    31: "In Excel, which function searches for a value in the first column and returns a value in the same row?",
    32: "Which formula properly handles errors and displays a fallback value in modern Excel?",
    33: "What is the main analytical benefit of using a Pivot Table for HR attrition reporting?",
    34: "Which Excel feature ensures users enter valid employee codes conforming to a specific format?",
    35: "How do you freeze the header row in Excel so it remains visible while scrolling down?",
    36: "Which chart type is best suited to display monthly department-wise hiring vs target trends?",
    37: "In an HR MIS sheet, what does the formula =COUNTIF(Range, \"Active\") compute?",
    38: "Which shortcut key in Excel opens the format cells dialog box quickly?",
    39: "What is the best Excel practice to combine first name (A2) and last name (B2) with a space?",
    40: "Which function calculates the difference between joining date and resignation date in days?",
    41: "When conveying a sensitive rejection to an internal candidate, what is the optimal approach?",
    42: "An employee angrily confronts HR about salary calculation. What should the HR executive do first?",
    43: "How should HR balance strict policy adherence with genuine emergency medical leave requests?",
    44: "What is the most professional channel to announce an organizational leadership restructuring?",
    45: "During an exit interview, an employee alleges toxic manager behavior. What is the required next step?",
    46: "How should HR respond when a business stakeholder demands bypassing statutory background checks?",
    47: "What is the key principle when writing an all-hands internal email communication?",
    48: "If two department heads conflict over candidate ownership, how should Talent Acquisition resolve it?",
    49: "What is the ethical responsibility of HR regarding confidential employee salary records?",
    50: "When an employee discloses a medical disability requesting accommodation, what is the proper step?"
}

OPTIONS_POOL = {
    'A': "Time to Hire and Time to Fill tracking",
    'B': "Approved annual business budget and staffing plan",
    'C': "Competency alignment and scorecard calibration",
    'D': "Talent market supply and internal succession readiness"
}


def build_docx(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    doc = Document()
    doc.add_heading("HR TEAM – PROFESSIONAL ASSESSMENT", level=0)
    p = doc.add_paragraph()
    p.add_run("Duration: 75 Minutes | Total Marks: 100 | Level: Intermediate\n").bold = True
    p.add_run("Instructions: 50 Questions, 2 Marks each. Each question has four options (A, B, C, D) with only one correct answer. No negative marking. All questions are compulsory.")

    for s_name, start_q, end_q in SECTIONS:
        doc.add_heading(f"SECTION: {s_name.upper()}", level=1)
        for q_num in range(start_q, end_q + 1):
            stem = STEMS.get(q_num, f"Assessment question {q_num} covering {s_name} principles and best practices.")
            doc.add_paragraph(f"Q{q_num}. {stem}")
            
            # Add options A, B, C, D
            correct_opt = CHECKSUM[q_num]
            labels = ['A', 'B', 'C', 'D']
            for lbl in labels:
                prefix = f"({lbl})"
                desc = OPTIONS_POOL[lbl]
                if lbl == correct_opt:
                    text = f"{desc} (Key for Q{q_num})"
                else:
                    text = f"{desc} option variant {lbl}"
                doc.add_paragraph(f"{prefix} {text}")

    # Add Answer Key Table
    doc.add_heading("ANSWER KEY", level=1)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Q.No"
    hdr_cells[1].text = "Answer"
    hdr_cells[2].text = "Q.No"
    hdr_cells[3].text = "Answer"

    for i in range(1, 26):
        row_cells = table.add_row().cells
        row_cells[0].text = str(i)
        row_cells[1].text = CHECKSUM[i]
        q2 = i + 25
        row_cells[2].text = str(q2)
        row_cells[3].text = CHECKSUM[q2]

    doc.add_paragraph("\nPERFORMANCE BANDS:")
    doc.add_paragraph("85–100: Excellent (Strong practical understanding)")
    doc.add_paragraph("70–84: Good (Minor areas for improvement)")
    doc.add_paragraph("50–69: Needs Improvement (Further guidance recommended)")
    doc.add_paragraph("Below 50: Requires Training (Reassessment recommended)")

    doc.save(filepath)
    print(f"Generated sample assessment docx at: {filepath}")


if __name__ == "__main__":
    target = os.path.join("data", "HR_Team_Professional_Assessment.docx")
    build_docx(target)
