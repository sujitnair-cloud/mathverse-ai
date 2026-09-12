"""
Phase 5: the learning journey's skill map, evidence, and recommendation
engine. The prerequisite graph itself already existed in MathTopic
(seeded in app/data/seed_data.py) — this module is what turns raw
SkillAttempt evidence into an explainable "what should this learner do
next" decision, and what a wrong answer should trigger.

Every recommendation returned here carries a `reason` string built from
the actual evidence it used (accuracy, attempt count, which prerequisite
is unmastered) — never a canned message — because the release condition
for this phase is that recommendations are explainable, not just present.
"""
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import MathTopic, SkillAttempt

MASTERY_WINDOW = 8          # only the most recent N attempts count toward mastery
MASTERY_THRESHOLD = 0.7     # accuracy over that window needed to call a skill "mastered"
MIN_ATTEMPTS_FOR_MASTERY = 4  # can't claim mastery from a lucky streak of 1-2 answers
STRUGGLING_THRESHOLD = 0.5  # accuracy below this (with enough attempts) triggers remediation
STRUGGLING_MIN_ATTEMPTS = 3


async def _all_topics(db: AsyncSession) -> Dict[str, MathTopic]:
    result = await db.execute(select(MathTopic))
    return {t.slug: t for t in result.scalars().all()}


async def compute_mastery(db: AsyncSession, session_id: str) -> Dict[str, dict]:
    """
    Evidence summary per attempted topic: accuracy over the recent window,
    whether that clears the mastery bar, and which specific misconceptions
    (not just "wrong") have recurred — this is the "repeated misconceptions"
    and "performance across time" tracking the phase asks for.
    """
    # Order by id as well as created_at: SQLite's CURRENT_TIMESTAMP only has
    # second resolution, so a burst of attempts within the same second would
    # otherwise tie on created_at and sort arbitrarily, silently breaking
    # "the most recent window" (id is a reliable insertion-order tiebreaker).
    result = await db.execute(
        select(SkillAttempt)
        .where(SkillAttempt.session_id == session_id)
        .order_by(SkillAttempt.created_at.desc(), SkillAttempt.id.desc())
    )
    by_topic: Dict[str, list] = defaultdict(list)
    for attempt in result.scalars().all():
        by_topic[attempt.topic].append(attempt)

    mastery = {}
    for topic, items in by_topic.items():
        window = items[:MASTERY_WINDOW]
        n = len(window)
        correct_n = sum(1 for a in window if a.correct)
        accuracy = correct_n / n if n else 0.0
        misconceptions = Counter(a.misconception for a in window if not a.correct and a.misconception)
        mastery[topic] = {
            "attempts_in_window": n,
            "total_attempts": len(items),
            "accuracy": round(accuracy, 2),
            "mastered": n >= MIN_ATTEMPTS_FOR_MASTERY and accuracy >= MASTERY_THRESHOLD,
            "top_misconceptions": [m for m, _ in misconceptions.most_common(2)],
            "hints_used_total": sum(a.hints_used or 0 for a in items),
            "last_attempt_at": items[0].created_at.isoformat() if items[0].created_at else None,
        }
    return mastery


async def skill_map_with_progress(db: AsyncSession, session_id: str) -> List[dict]:
    """The full skill map (every topic, its prerequisites) annotated with
    this learner's evidence and a derived unlock state — 'locked' means at
    least one prerequisite isn't mastered yet."""
    topics = await _all_topics(db)
    mastery = await compute_mastery(db, session_id)

    def is_mastered(slug: str) -> bool:
        return mastery.get(slug, {}).get("mastered", False)

    out = []
    for slug, topic in topics.items():
        prereqs = topic.prerequisites or []
        unlocked = all(is_mastered(p) for p in prereqs)
        info = mastery.get(slug)
        status = "mastered" if info and info["mastered"] else (
            "in_progress" if info else ("ready" if unlocked else "locked")
        )
        out.append({
            "slug": slug, "name": topic.name, "category": topic.category,
            "prerequisites": prereqs, "status": status,
            "has_practice": slug in PRACTICE_ENABLED_TOPICS,
            "evidence": info,
        })
    return out


async def recommend_next(db: AsyncSession, session_id: str) -> dict:
    """
    The single "what should this learner do next" decision, and why.
    Checked in order:
      1. A struggling topic whose prerequisite isn't mastered -> revisit that prerequisite.
      2. A struggling topic whose prerequisites ARE mastered -> more focused practice on it.
      3. An unattempted/incomplete topic whose prerequisites are all mastered -> the frontier.
      4. Everything reachable is mastered -> spaced review of the topic practiced longest ago.
      5. Nothing attempted at all -> start at a topic with no prerequisites.
    """
    topics = await _all_topics(db)
    mastery = await compute_mastery(db, session_id)

    def is_mastered(slug: str) -> bool:
        return mastery.get(slug, {}).get("mastered", False)

    def name(slug: str) -> str:
        t = topics.get(slug)
        return t.name if t else slug

    # 1 & 2: struggling topics, checked in the order they were last attempted
    struggling = [
        (slug, info) for slug, info in mastery.items()
        if slug in topics and info["attempts_in_window"] >= STRUGGLING_MIN_ATTEMPTS
        and info["accuracy"] < STRUGGLING_THRESHOLD
    ]
    struggling.sort(key=lambda si: si[1]["last_attempt_at"] or "", reverse=True)
    for slug, info in struggling:
        for prereq in (topics[slug].prerequisites or []):
            if not is_mastered(prereq):
                return {
                    "topic": prereq, "stage": "guided",
                    "reason": (
                        f"Your accuracy on {name(slug)} is {int(info['accuracy'] * 100)}% over your last "
                        f"{info['attempts_in_window']} attempts, and {name(slug)} builds on {name(prereq)}, "
                        f"which isn't mastered yet. Strengthening {name(prereq)} first should make "
                        f"{name(slug)} click."
                    ),
                    "evidence": info,
                }
        misconception_note = (
            f" You've repeated the same mistake ({info['top_misconceptions'][0].replace('_', ' ')}) more than once — "
            f"worth a different explanation this time." if info["top_misconceptions"] else ""
        )
        return {
            "topic": slug, "stage": "guided",
            "reason": (
                f"Your accuracy on {name(slug)} is {int(info['accuracy'] * 100)}% over your last "
                f"{info['attempts_in_window']} attempts, even though its prerequisites are solid."
                + misconception_note
            ),
            "evidence": info,
        }

    # 3: frontier — prerequisites cleared, topic itself not yet mastered
    for slug, topic in topics.items():
        info = mastery.get(slug)
        if info and info["mastered"]:
            continue
        prereqs = topic.prerequisites or []
        if all(is_mastered(p) for p in prereqs):
            if info:
                reason = (
                    f"You've attempted {name(slug)} {info['total_attempts']} time(s) with "
                    f"{int(info['accuracy'] * 100)}% recent accuracy — a bit more practice should get you to mastery."
                )
                stage = "guided"
            elif prereqs:
                reason = f"You've mastered {', '.join(name(p) for p in prereqs)} — {name(slug)} builds directly on that and you haven't tried it yet."
                stage = "diagnostic"
            else:
                reason = f"{name(slug)} has no prerequisites and you haven't started it yet — a good place to begin."
                stage = "diagnostic"
            return {"topic": slug, "stage": stage, "reason": reason, "evidence": info}

    # 4: everything reachable is mastered — spaced review of the stalest one
    mastered_slugs = [s for s, i in mastery.items() if i["mastered"] and s in topics]
    if mastered_slugs:
        oldest = min(mastered_slugs, key=lambda s: mastery[s]["last_attempt_at"] or "")
        return {
            "topic": oldest, "stage": "review",
            "reason": f"You've mastered {name(oldest)} — it's been the longest since you last practiced it, so a quick review keeps it fresh.",
            "evidence": mastery[oldest],
        }

    # 5: nothing attempted yet — start at a root topic
    roots = [s for s, t in topics.items() if not (t.prerequisites or [])]
    chosen = roots[0] if roots else next(iter(topics), None)
    return {
        "topic": chosen, "stage": "diagnostic",
        "reason": f"Let's start with {name(chosen)} — it has no prerequisites, so it's a natural first step." if chosen else "No topics configured yet.",
        "evidence": None,
    }


async def remediate_wrong_answer(db: AsyncSession, session_id: str, topic_slug: str, misconception: Optional[str]) -> dict:
    """
    What happens right after a specific wrong answer — the roadmap's "a
    wrong answer should trigger a useful response," evaluated fresh for
    this one attempt rather than only the next multi-step recommendation:
      - An unmastered prerequisite exists -> revisit it.
      - This exact misconception has now recurred -> flag for a different explanation.
      - Otherwise -> more focused practice on the same skill.
    """
    topics = await _all_topics(db)
    topic = topics.get(topic_slug)
    mastery = await compute_mastery(db, session_id)

    def name(slug: str) -> str:
        t = topics.get(slug)
        return t.name if t else slug

    if topic:
        for prereq in (topic.prerequisites or []):
            info = mastery.get(prereq)
            if not info or not info["mastered"]:
                return {
                    "action": "revisit_prerequisite", "target_topic": prereq,
                    "reason": f"{name(topic_slug)} depends on {name(prereq)}. Revisiting {name(prereq)} first will likely make this click.",
                }

    info = mastery.get(topic_slug)
    if info and misconception and misconception in info["top_misconceptions"]:
        return {
            "action": "different_explanation", "target_topic": topic_slug, "misconception": misconception,
            "reason": f"This is the same kind of mistake ({misconception.replace('_', ' ')}) more than once — a different explanation may help more than another similar question.",
        }

    return {
        "action": "focused_practice", "target_topic": topic_slug,
        "reason": f"Let's try a couple more {name(topic_slug)} questions of the same kind to lock it in.",
    }


# Topics with a real SymPy-verified question generator (see quiz_generator.py) —
# the others appear in the skill map with lesson content, but honestly show
# "practice not yet available" rather than silently substituting an unrelated
# topic's questions.
PRACTICE_ENABLED_TOPICS = {
    "arithmetic", "algebra", "geometry", "trigonometry",
    "calculus", "statistics", "probability", "linear-algebra",
}
