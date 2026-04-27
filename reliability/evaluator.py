"""
reliability/evaluator.py
========================
Automated evaluation harness for the PawPal+ agentic system.

The evaluator runs a predefined suite of test cases through the full agent
pipeline and scores the results against expected behaviours.  It is designed
to be called:

* During development to catch regressions after changes.
* As part of CI via ``pytest`` (a thin wrapper in ``tests/`` calls
  :func:`run_evaluation`).
* On demand from the Streamlit UI to give the owner a live confidence report.

Test-case format
----------------
Each test case passed to :func:`run_evaluation` is a dict with the keys:

``name``            : str   — unique human-readable identifier.
``owner``           : Owner — the owner object to pass to the agent.
``task_list``       : list  — the Task list to schedule.
``expected_behaviors``: list[str] — behaviour tags to check (see below).

Expected behaviour tags
-----------------------
``"medical_tasks_included"``
    No task whose name contains ``"med"`` or ``"medication"`` appears in
    ``result["skipped"]`` (i.e. all medical tasks were scheduled).
``"high_priority_first"``
    The first task in ``result["plan"]`` has ``priority == Priority.HIGH``.
``"fits_budget"``
    The total duration of all scheduled tasks is greater than zero.

Unknown tags are treated as failures so that typos surface immediately.

Functions
---------
score_plan(plan, expected_behaviors)
    Score a plan (or full run_agent result dict) against behaviour tags.

run_evaluation(test_cases)
    Run every test case, print a pass/fail report, and return a summary dict.
"""

from __future__ import annotations

from logger import logger
from pawpal_system import Priority

# Threshold: a test case passes if its score meets or exceeds this value.
_PASS_THRESHOLD = 0.8

# Keywords that mark a task as medical/medication.
_MEDICAL_KEYWORDS = frozenset({"med", "medication"})


def _is_medical(task_name: str) -> bool:
    """Return True if *task_name* contains any medical keyword."""
    name_lower = task_name.lower()
    return any(kw in name_lower for kw in _MEDICAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_plan(plan, expected_behaviors: list) -> float:
    """Score *plan* against *expected_behaviors* and return a fraction in [0, 1].

    *plan* may be either:

    * A plain ``list`` of :class:`~pawpal_system.Task` objects (the scheduled
      tasks only).
    * The full ``dict`` returned by :func:`~agent.planner.run_agent`, which
      also exposes ``"skipped"`` — enabling richer checks such as
      ``"medical_tasks_included"``.

    Supported behaviour tags
    ~~~~~~~~~~~~~~~~~~~~~~~~
    ``"medical_tasks_included"``
        Passes when no task with ``"med"``/``"medication"`` in its name is
        present in ``skipped``.  When only a plain list is provided the check
        passes trivially (no skipped list available to falsify it).
    ``"high_priority_first"``
        Passes when the first task in the plan has ``priority == Priority.HIGH``.
    ``"fits_budget"``
        Passes when the sum of durations in the plan is greater than zero.

    Any tag not in the set above is counted as a **failure** so that typos in
    test-case definitions surface immediately instead of silently inflating
    scores.

    Parameters
    ----------
    plan:
        Either a ``list[Task]`` or the full ``dict`` from
        :func:`~agent.planner.run_agent`.
    expected_behaviors:
        List of behaviour tag strings to evaluate.

    Returns
    -------
    float
        ``passed_checks / len(expected_behaviors)``.
        Returns ``0.0`` if *expected_behaviors* is empty.
    """
    if not expected_behaviors:
        return 0.0

    # Normalise: accept either a plain plan list or a full result dict.
    if isinstance(plan, dict):
        plan_list = plan.get("plan", [])
        skipped_list = plan.get("skipped", [])
    else:
        plan_list = plan if isinstance(plan, list) else []
        skipped_list = []  # no skipped data available from a bare list

    passed = 0

    for behavior in expected_behaviors:

        if behavior == "medical_tasks_included":
            # Pass if no medical task appears in skipped.
            medical_skipped = any(_is_medical(t.name) for t in skipped_list)
            if not medical_skipped:
                passed += 1

        elif behavior == "high_priority_first":
            # Pass if the first scheduled task has HIGH priority.
            if plan_list and plan_list[0].priority == Priority.HIGH:
                passed += 1

        elif behavior == "fits_budget":
            # Pass if at least some time was scheduled (plan is non-trivial).
            total_duration = sum(getattr(t, "duration", 0) for t in plan_list)
            if total_duration > 0:
                passed += 1

        else:
            # Unknown tag → failure (keeps score honest).
            logger.warning(
                "score_plan: unknown behaviour tag '%s' — counted as failure", behavior
            )

    return passed / len(expected_behaviors)


def run_evaluation(test_cases: list) -> dict:
    """Run every test case through the agent, print a report, and return a summary.

    For each test case the function:

    1. Calls :func:`~agent.planner.run_agent` with ``case["owner"]`` and
       ``case["task_list"]``.
    2. Passes the full result dict to :func:`score_plan` with
       ``case["expected_behaviors"]``.
    3. Records pass (score >= 0.8) or fail.
    4. Prints a ``[PASS]`` / ``[FAIL]`` line to the terminal for each case.

    Individual test-case exceptions are caught, logged, and recorded as
    score ``0.0`` so one broken case does not abort the whole run.

    Parameters
    ----------
    test_cases:
        List of test-case dicts.  See module docstring for required keys.

    Returns
    -------
    dict
        ``"total"``    (int)         — number of test cases run.
        ``"passed"``   (int)         — cases where score >= 0.8.
        ``"failed"``   (int)         — cases where score < 0.8.
        ``"scores"``   (list[dict])  — per-case ``{name, score, passed}`` dicts.
        ``"summary"``  (str)         — human-readable pass-rate string.
    """
    # Import here to avoid a circular import at module load time.
    from agent.planner import run_agent  # noqa: PLC0415

    total = len(test_cases)
    n_passed = 0
    n_failed = 0
    scores: list[dict] = []

    print()
    print("=" * 55)
    print("  PawPal+ Evaluation Run")
    print("=" * 55)

    for case in test_cases:
        name = case.get("name", case.get("id", "unnamed"))
        owner = case["owner"]
        task_list = case["task_list"]
        expected = case.get("expected_behaviors", [])

        try:
            result = run_agent(owner, task_list)
            score = score_plan(result, expected)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "run_evaluation: test case '%s' raised an unexpected error: %s",
                name, exc, exc_info=True,
            )
            score = 0.0

        case_passed = score >= _PASS_THRESHOLD
        if case_passed:
            n_passed += 1
            status_label = "PASS"
        else:
            n_failed += 1
            status_label = "FAIL"

        scores.append({"name": name, "score": round(score, 4), "passed": case_passed})

        # Terminal report line.
        print(f"  [{status_label}]  {name:<35}  score={score:.2f}")
        logger.info(
            "run_evaluation: [%s] '%s'  score=%.2f", status_label, name, score
        )

    # Summary line.
    pass_rate = n_passed / total if total > 0 else 0.0
    summary = (
        f"{n_passed}/{total} test case(s) passed "
        f"({pass_rate:.0%} pass rate)"
    )
    print("-" * 55)
    print(f"  {summary}")
    print("=" * 55)
    print()

    logger.info("run_evaluation complete: %s", summary)

    return {
        "total": total,
        "passed": n_passed,
        "failed": n_failed,
        "scores": scores,
        "summary": summary,
    }
