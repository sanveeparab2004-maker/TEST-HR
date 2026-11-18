import os
import pytest
from scripts.import_questions import parse_assessment_docx, INDEPENDENT_CHECKSUM
from scripts.import_roster import validate_roster_csv


def test_parse_valid_docx():
    docx_path = os.path.join("data", "HR_Team_Professional_Assessment.docx")
    assert os.path.exists(docx_path), "Sample docx must exist for testing"

    parsed = parse_assessment_docx(docx_path)
    assert len(parsed["questions"]) == 50
    assert len(parsed["answer_key"]) == 50

    # Every question must have options A, B, C, D
    for q_num, q_data in parsed["questions"].items():
        assert len(q_data["options"]) == 4
        assert set(q_data["options"].keys()) == {'A', 'B', 'C', 'D'}

    # Every answer key matches the independent checksum
    for q_num, expected_key in INDEPENDENT_CHECKSUM.items():
        assert parsed["answer_key"][q_num] == expected_key


def test_validate_roster_csv_success():
    csv_path = os.path.join("data", "sample_roster.csv")
    rows, errors = validate_roster_csv(csv_path)
    assert len(errors) == 0
    assert len(rows) == 10
    assert rows[0]["employee_code"] == "EMP001"
    assert rows[0]["role"] == "CANDIDATE"


def test_validate_roster_csv_errors(tmp_path):
    bad_csv = tmp_path / "bad_roster.csv"
    bad_csv.write_text(
        "employee_code,full_name,department,role\n"
        ",No Code Person,Dept,CANDIDATE\n"
        "EMP099,,Dept,CANDIDATE\n"
        "EMP098,Valid Name,Dept,INVALID_ROLE\n"
        "EMP097,Person 1,Dept,CANDIDATE\n"
        "EMP097,Person Duplicate,Dept,CANDIDATE\n"
    )

    rows, errors = validate_roster_csv(str(bad_csv))
    assert len(errors) == 4
    assert any("Empty employee_code" in e for e in errors)
    assert any("Empty full_name" in e for e in errors)
    assert any("Invalid role" in e for e in errors)
    assert any("Duplicate employee_code" in e for e in errors)
