import pytest
from backend.app.services.grading import grade_attempt, determine_band


@pytest.fixture
def sample_test_setup():
    """Create a mock 50-question test setup matching the 7 sections."""
    sections = {
        1: "Recruitment Planning",
        2: "Sourcing & Screening",
        3: "Interview Management",
        4: "Offer & Joining",
        5: "HR Operations",
        6: "Excel & MIS",
        7: "Communication & Judgement"
    }

    # 50 questions, 2 marks each
    # Sections distribution: 5, 5, 5, 5, 10, 10, 10
    sec_counts = [(1, 5), (2, 5), (3, 5), (4, 5), (5, 10), (6, 10), (7, 10)]
    questions_map = {}
    q_counter = 1

    for s_id, count in sec_counts:
        for _ in range(count):
            opt_a_id = q_counter * 10 + 1
            opt_b_id = q_counter * 10 + 2
            opt_c_id = q_counter * 10 + 3
            opt_d_id = q_counter * 10 + 4
            questions_map[q_counter] = {
                "source_number": q_counter,
                "stem": f"Question {q_counter}",
                "marks": 2,
                "section_id": s_id,
                "correct_option_id": opt_a_id,  # Assume A is correct for this test fixture
                "options": {
                    opt_a_id: {"label": "A", "text": "Option A"},
                    opt_b_id: {"label": "B", "text": "Option B"},
                    opt_c_id: {"label": "C", "text": "Option C"},
                    opt_d_id: {"label": "D", "text": "Option D"},
                }
            }
            q_counter += 1

    return questions_map, sections


def test_all_correct_scores_100(sample_test_setup):
    questions_map, sections = sample_test_setup
    # Candidate answered all questions correctly (selected opt A)
    answers = {q_id: q["correct_option_id"] for q_id, q in questions_map.items()}

    result = grade_attempt(answers, questions_map, sections)
    assert result["score"] == 100
    assert result["max_score"] == 100
    assert result["percentage"] == 100.0
    assert result["band"] == "Excellent (Strong practical understanding)"
    assert len(result["missed_questions"]) == 0

    # Section totals check
    sum_sections = sum(s["score"] for s in result["section_scores"].values())
    assert sum_sections == 100


def test_all_wrong_scores_zero(sample_test_setup):
    questions_map, sections = sample_test_setup
    # Candidate answered B for all (wrong)
    answers = {q_id: q_id * 10 + 2 for q_id in questions_map.keys()}

    result = grade_attempt(answers, questions_map, sections)
    assert result["score"] == 0
    assert result["percentage"] == 0.0
    assert result["band"] == "Requires Training (Reassessment recommended)"
    assert len(result["missed_questions"]) == 50


def test_all_blank_scores_zero(sample_test_setup):
    questions_map, sections = sample_test_setup
    # Candidate left all questions unanswered
    answers = {q_id: None for q_id in questions_map.keys()}

    result = grade_attempt(answers, questions_map, sections)
    assert result["score"] == 0
    assert result["percentage"] == 0.0
    assert result["band"] == "Requires Training (Reassessment recommended)"
    assert len(result["missed_questions"]) == 50
    assert all(m["is_unanswered"] for m in result["missed_questions"])


def test_band_boundaries():
    assert determine_band(85.0) == "Excellent (Strong practical understanding)"
    assert determine_band(84.9) == "Good (Minor areas for improvement)"
    assert determine_band(70.0) == "Good (Minor areas for improvement)"
    assert determine_band(69.9) == "Needs Improvement (Further guidance recommended)"
    assert determine_band(50.0) == "Needs Improvement (Further guidance recommended)"
    assert determine_band(49.9) == "Requires Training (Reassessment recommended)"
    assert determine_band(0.0) == "Requires Training (Reassessment recommended)"


def test_shuffled_options_marking(sample_test_setup):
    """Marks are based strictly on selected option id matching correct option id, independent of UI display order."""
    questions_map, sections = sample_test_setup
    # Pick correct option IDs regardless of their label or position
    answers = {}
    for q_id, q_data in questions_map.items():
        if q_id % 2 == 0:
            answers[q_id] = q_data["correct_option_id"]
        else:
            answers[q_id] = q_id * 10 + 3  # Wrong option C

    result = grade_attempt(answers, questions_map, sections)
    assert result["score"] == 50
    assert result["percentage"] == 50.0
    assert result["band"] == "Needs Improvement (Further guidance recommended)"


def test_recompute_gives_identical_score(sample_test_setup):
    """Pure function guarantee: same input always produces identical output."""
    questions_map, sections = sample_test_setup
    answers = {q_id: (q_id * 10 + 1 if q_id <= 35 else None) for q_id in questions_map.keys()}

    result1 = grade_attempt(answers, questions_map, sections)
    result2 = grade_attempt(answers, questions_map, sections)
    assert result1 == result2
