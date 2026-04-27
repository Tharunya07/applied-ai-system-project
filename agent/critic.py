"""
agent/critic.py
===============
Audits a proposed PawPal+ plan before it is shown to the owner.

The critic is the second step in the plan-then-critique loop.  It receives
the plan produced by the scheduler (inside ``agent.planner``) along with the
original task list and returns a structured assessment containing:

* A **confidence score** in ``[0.0, 1.0]`` — how likely the plan is to meet
  the owner's actual pet care needs.
* A **list of concerns** — specific issues the planner or UI layer should
  surface to the user.
* **Coverage** — the fraction of the original task list that was scheduled.
* **medical_tasks_skipped** — count of medication/medical tasks dropped.

Confidence-penalty table
------------------------
+----------------------------------------------+----------+
| Condition                                    | Penalty  |
+==============================================+==========+
| Each missed medical task                     | −0.30    |
+----------------------------------------------+----------+
| Coverage below 50 %                          | −0.10    |
+----------------------------------------------+----------+
| Each non-medical skipped task (max −0.20)    | −0.05    |
+----------------------------------------------+----------+
| Empty plan with non-empty task list          | set → 0.0|
+----------------------------------------------+----------+

Final score is clamped to ``[0.0, 1.0]``.

Functions
---------
check_medical_tasks(plan, task_list)
    Return concern strings for every medical task dropped from the plan.

critique_plan(plan, task_list)
    Full audit; return dict with confidence, concerns, coverage,
    medical_tasks_skipped.
"""

from __future__ import annotations

# Keywords that identify a task as medication/medical in nature.
_MEDICAL_KEYWORDS: frozenset[str] = frozenset({
    "medication", "med", "medicine", "insulin", "antibiotic",
})


def _is_medical(task_name: str) -> bool:
    """Return True if *task_name* contains any medical keyword."""
    name_lower = task_name.lower()
    return any(kw in name_lower for kw in _MEDICAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_medical_tasks(plan: list, task_list: list) -> list[str]:
    """Return concern strings for every medical task in *task_list* absent from *plan*.

    A task is considered medical if its ``name`` contains any of the keywords:
    ``medication``, ``med``, ``medicine``, ``insulin``, ``antibiotic``.

    Parameters
    ----------
    plan:
        Ordered list of :class:`~pawpal_system.Task` objects selected by the
        scheduler.
    task_list:
        Complete original task list before scheduling.

    Returns
    -------
    list[str]
        One concern string per skipped medical task, in the form:
        ``"Medical task '<name>' for <pet> was skipped — this may be unsafe"``.
        Returns an empty list if all medical tasks were scheduled or if there
        are no medical tasks.
    """
    concerns: list[str] = []
    plan_ids = {id(t) for t in plan}

    for task in task_list:
        if _is_medical(task.name) and id(task) not in plan_ids:
            concerns.append(
                f"Medical task '{task.name}' for {task.pet.name} "
                f"was skipped — this may be unsafe"
            )

    return concerns


def critique_plan(plan: list, task_list: list) -> dict:
    """Audit *plan* against *task_list* and return a confidence assessment.

    Parameters
    ----------
    plan:
        Proposed ordered schedule (list of Task objects).
    task_list:
        Full original task list before scheduling.

    Returns
    -------
    dict
        ``"confidence"`` (float)
            Score in ``[0.0, 1.0]`` after applying penalties.
        ``"concerns"`` (list[str])
            Human-readable concern strings.
        ``"coverage"`` (float)
            ``len(plan) / len(task_list)`` (``0.0`` if *task_list* is empty).
        ``"medical_tasks_skipped"`` (int)
            Number of medical tasks absent from *plan*.
    """
    concerns: list[str] = []

    # Edge case: no tasks at all.
    if not task_list:
        return {
            "confidence": 0.0,
            "concerns": ["No tasks were provided for scheduling."],
            "coverage": 0.0,
            "medical_tasks_skipped": 0,
        }

    # Edge case: empty plan with non-empty task list.
    if not plan:
        return {
            "confidence": 0.0,
            "concerns": ["No tasks were scheduled — all tasks may have been skipped."],
            "coverage": 0.0,
            "medical_tasks_skipped": sum(1 for t in task_list if _is_medical(t.name)),
        }

    confidence = 1.0

    # ------------------------------------------------------------------
    # Penalty 1: missed medical tasks (−0.30 each)
    # ------------------------------------------------------------------
    medical_concerns = check_medical_tasks(plan, task_list)
    medical_tasks_skipped = len(medical_concerns)
    concerns.extend(medical_concerns)
    confidence -= 0.30 * medical_tasks_skipped

    # ------------------------------------------------------------------
    # Penalty 2: low coverage (−0.10 if < 50 %)
    # ------------------------------------------------------------------
    coverage = len(plan) / len(task_list)
    if coverage < 0.5:
        concerns.append(
            f"Low schedule coverage: only {len(plan)}/{len(task_list)} tasks "
            f"were scheduled ({coverage:.0%})."
        )
        confidence -= 0.10

    # ------------------------------------------------------------------
    # Penalty 3: non-medical skipped tasks (−0.05 each, capped at −0.20)
    # ------------------------------------------------------------------
    plan_ids = {id(t) for t in plan}
    non_medical_skipped = sum(
        1 for t in task_list
        if id(t) not in plan_ids and not _is_medical(t.name)
    )
    confidence -= min(0.05 * non_medical_skipped, 0.20)

    # ------------------------------------------------------------------
    # Clamp and return
    # ------------------------------------------------------------------
    confidence = max(0.0, min(1.0, confidence))

    return {
        "confidence": confidence,
        "concerns": concerns,
        "coverage": coverage,
        "medical_tasks_skipped": medical_tasks_skipped,
    }
