"""Learner model: Bayesian Knowledge Tracing + next-question policy (pure functions)."""
P_GUESS, P_SLIP, P_LEARN = 0.22, 0.10, 0.16


def bkt_update(p, correct):
    if correct:
        post = p * (1 - P_SLIP) / (p * (1 - P_SLIP) + (1 - p) * P_GUESS)
    else:
        post = p * P_SLIP / (p * P_SLIP + (1 - p) * (1 - P_GUESS))
    return min(0.99, max(0.01, post + (1 - post) * P_LEARN))


def target_difficulty(p):
    return 1 if p < 0.35 else 2 if p < 0.7 else 3


def level(p):
    return "mastered" if p >= 0.8 else "strong" if p >= 0.6 else "building" if p >= 0.4 else "weak"


def choose_topic(mastery, prereqs, has_questions):
    """mastery {tid: p}; prereqs {tid: [tid]}; returns topic id to practise next."""
    ordered = sorted((t for t in mastery if has_questions.get(t)), key=lambda t: mastery[t])
    if not ordered:
        return None
    t = ordered[0]
    for pre in prereqs.get(t, []):
        if has_questions.get(pre) and mastery.get(pre, 1) < 0.45:
            return pre
    return t


def choose_question(questions, p, seen_ids):
    """questions: [{"id","difficulty"}]. Prefer unseen, closest to target difficulty."""
    want = target_difficulty(p)
    pool = [q for q in questions if q["id"] not in seen_ids] or questions
    return min(pool, key=lambda q: (abs(q["difficulty"] - want), q["id"])) if pool else None
