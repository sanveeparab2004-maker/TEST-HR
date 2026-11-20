import secrets
from typing import List, Dict, Any, Tuple

# Options that should not be shuffled because their meaning depends on letter order
FIXED_OPTION_PATTERNS = [
    "all of the above",
    "none of the above",
    "both a and b",
    "both b and c",
    "both a and c",
    "either a or b",
    "all the above",
    "none of these",
    "all of these"
]


def should_keep_options_fixed(options_text_list: List[str]) -> bool:
    """Returns True if any option in the question depends on position (e.g. All of the above)."""
    for text in options_text_list:
        lower = text.strip().lower()
        for pat in FIXED_OPTION_PATTERNS:
            if pat in lower:
                return True
    return False


def generate_attempt_shuffle(
    questions: List[Any],
    options_by_q: Dict[int, List[Any]]
) -> Tuple[List[int], Dict[str, List[int]]]:
    """Generates a cryptographically secure random order for questions and options.
    
    Uses secrets.SystemRandom() (Fisher-Yates shuffle) seeded per attempt.
    Option order is shuffled unless options contain 'All of the above' / 'None of the above'.
    """
    rng = secrets.SystemRandom()

    # 1. Shuffle question IDs
    q_ids = [q.id for q in questions]
    rng.shuffle(q_ids)

    # 2. Shuffle option IDs for each question unless position-dependent
    option_order: Dict[str, List[int]] = {}
    for q_id, opt_list in options_by_q.items():
        opt_texts = [o.text for o in opt_list]
        opt_ids = [o.id for o in opt_list]
        if should_keep_options_fixed(opt_texts):
            option_order[str(q_id)] = list(opt_ids)
        else:
            shuffled = list(opt_ids)
            rng.shuffle(shuffled)
            option_order[str(q_id)] = shuffled

    return q_ids, option_order
