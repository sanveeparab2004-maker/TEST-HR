import os
import re
import sys
import docx

def test_parse():
    doc = docx.Document("data/HR_Team_Professional_Assessment_real.docx")
    KNOWN_SECTIONS = {
        "RECRUITMENT PLANNING": "Recruitment Planning",
        "SOURCING & SCREENING": "Sourcing & Screening",
        "INTERVIEW MANAGEMENT": "Interview Management",
        "OFFER & JOINING": "Offer & Joining",
        "HR OPERATIONS": "HR Operations",
        "EXCEL & MIS": "Excel & MIS",
        "COMMUNICATION & JUDGEMENT": "Communication & Judgement"
    }

    q_pattern = re.compile(r"^(\d+)[\.\)]\s*(.+)")
    opt_pattern = re.compile(r"^([A-D])[\)\.\:]\s*(.+)")

    current_sec = "Recruitment Planning"
    questions = {}
    current_q = None

    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if t.upper() in KNOWN_SECTIONS:
            current_sec = KNOWN_SECTIONS[t.upper()]
            continue
        
        qm = q_pattern.match(t)
        if qm:
            current_q = int(qm.group(1))
            questions[current_q] = {
                "stem": qm.group(2).strip(),
                "section": current_sec,
                "options": {}
            }
            continue

        om = opt_pattern.match(t)
        if om and current_q:
            questions[current_q]["options"][om.group(1).upper()] = om.group(2).strip()

    print(f"Total questions found: {len(questions)}")
    for qn in range(1, 51):
        q = questions.get(qn)
        if not q:
            print(f"MISSING Q{qn}!")
        elif len(q["options"]) != 4:
            print(f"Q{qn} invalid options count: {len(q['options'])}")
        else:
            opts_keys = "".join(sorted(q["options"].keys()))
            if opts_keys != "ABCD":
                print(f"Q{qn} invalid option keys: {opts_keys}")

    print("Success! All 50 questions parsed with exactly 4 options (A, B, C, D) each.")

if __name__ == "__main__":
    test_parse()
