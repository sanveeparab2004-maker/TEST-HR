from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP


def determine_band(percentage: float) -> str:
    """Determine performance band based on percentage score.
    
    85–100: Excellent (Strong practical understanding)
    70–84: Good (Minor areas for improvement)
    50–69: Needs Improvement (Further guidance recommended)
    Below 50: Requires Training (Reassessment recommended)
    """
    if percentage >= 85.0:
        return "Excellent (Strong practical understanding)"
    elif percentage >= 70.0:
        return "Good (Minor areas for improvement)"
    elif percentage >= 50.0:
        return "Needs Improvement (Further guidance recommended)"
    else:
        return "Requires Training (Reassessment recommended)"


def grade_attempt(
    answers_map: Dict[int, Optional[int]],
    question_key_map: Dict[int, Dict[str, Any]],
    section_map: Dict[int, str],
    negative_marking: bool = False,
    negative_mark_value: float = 0.5
) -> Dict[str, Any]:
    """Pure grading function.
    
    Args:
        answers_map: {question_id: selected_option_id} (or None if unselected)
        question_key_map: {
            question_id: {
                "correct_option_id": int,
                "marks": int,
                "section_id": int,
                "source_number": int,
                "stem": str,
                "options": {opt_id: {"label": str, "text": str}}
            }
        }
        section_map: {section_id: section_name}
        negative_marking: bool
        negative_mark_value: float deductions per wrong answer if negative marking is enabled
        
    Returns:
        dict with total_score, max_score, percentage, band, section_scores, missed_questions
    """
    total_score = 0
    max_score = 0
    section_breakdown: Dict[str, Dict[str, Any]] = {}
    missed_questions: List[Dict[str, Any]] = []

    # Initialize section breakdown
    for s_id, s_name in section_map.items():
        section_breakdown[s_name] = {
            "score": 0,
            "max_score": 0,
            "percentage": 0.0,
            "correct_count": 0,
            "total_questions": 0
        }

    for q_id, q_info in question_key_map.items():
        q_marks = q_info.get("marks", 2)
        s_id = q_info.get("section_id")
        s_name = section_map.get(s_id, "General")
        correct_opt_id = q_info.get("correct_option_id")
        selected_opt_id = answers_map.get(q_id)

        max_score += q_marks
        section_breakdown[s_name]["max_score"] += q_marks
        section_breakdown[s_name]["total_questions"] += 1

        if selected_opt_id is not None and selected_opt_id == correct_opt_id:
            total_score += q_marks
            section_breakdown[s_name]["score"] += q_marks
            section_breakdown[s_name]["correct_count"] += 1
        else:
            # Unanswered or Wrong
            if selected_opt_id is not None and negative_marking:
                total_score = max(0, total_score - negative_mark_value)
                section_breakdown[s_name]["score"] = max(0, section_breakdown[s_name]["score"] - negative_mark_value)

            # Record missed question detail
            missed_questions.append({
                "question_id": q_id,
                "source_number": q_info.get("source_number"),
                "stem": q_info.get("stem"),
                "section": s_name,
                "selected_option_id": selected_opt_id,
                "selected_label": q_info["options"].get(selected_opt_id, {}).get("label") if selected_opt_id else None,
                "correct_option_id": correct_opt_id,
                "correct_label": q_info["options"].get(correct_opt_id, {}).get("label"),
                "is_unanswered": selected_opt_id is None
            })

    # Compute percentages
    percentage = float(
        Decimal(str((total_score / max_score) * 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    ) if max_score > 0 else 0.0

    for s_name, data in section_breakdown.items():
        if data["max_score"] > 0:
            data["percentage"] = float(
                Decimal(str((data["score"] / data["max_score"]) * 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )

    band = determine_band(percentage)

    return {
        "score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "band": band,
        "section_scores": section_breakdown,
        "missed_questions": missed_questions
    }
