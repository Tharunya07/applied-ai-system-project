"""
reliability/guardrails.py
=========================
Pre- and post-execution validation for the PawPal+ agentic workflow.

Guardrails are stateless, synchronous functions that run at the boundary of
the agent loop.  They are called *before* the agent does expensive work
(input validation) and *after* the agent produces its output (output check)
to catch issues that should never reach the user.

Design principles
-----------------
* **Fail fast on input** — return errors immediately so no compute is wasted.
* **Soft flags on output** — the output check returns a status dict rather
  than raising exceptions, letting the UI decide how to handle each flag.
* **No side effects** — guardrails do not modify the owner, task list, or plan.

Functions
---------
validate_input(owner, task_list)
    Validate owner and task list before the agent runs.  Returns a list of
    error strings; empty list means all checks passed.

check_output(plan, warnings)
    Validate agent output before it is shown to the user.  Returns a dict
    with keys ``status`` and ``flags``.
"""

from __future__ import annotations

from typing import Any

# Maximum single-task duration considered realistic (8 hours).
_MAX_TASK_DURATION_MINUTES = 480


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_input(owner: Any, task_list: list) -> list[str]:
    """Validate *owner* and *task_list* before the agent runs.

    Checks
    ~~~~~~
    1. *owner* is not ``None``.
    2. *task_list* is a non-empty list.
    3. ``owner.available_time_per_day`` exists and is >= 1.
    4. Every task has ``duration >= 1`` minute.
    5. Every task has ``duration <= 480`` minutes (8 hours).

    Parameters
    ----------
    owner:
        The :class:`~pawpal_system.Owner` instance to validate.
    task_list:
        The list of :class:`~pawpal_system.Task` objects to validate.

    Returns
    -------
    list[str]
        Error strings describing each failed check.  Empty list means all
        checks passed.  The caller should abort the agent run if this list
        is non-empty.
    """
    errors: list[str] = []

    # Check 1: owner must not be None.
    if owner is None:
        errors.append("Owner must not be None.")
        # Cannot proceed with further owner checks.
        return errors

    # Check 2: task_list must be a non-empty list.
    if not isinstance(task_list, list):
        errors.append(
            f"task_list must be a list, got {type(task_list).__name__}."
        )
    elif len(task_list) == 0:
        errors.append("task_list must not be empty.")

    # Check 3: owner must have a valid available_time_per_day.
    if not hasattr(owner, "available_time_per_day"):
        errors.append("Owner is missing the 'available_time_per_day' attribute.")
    elif owner.available_time_per_day < 1:
        errors.append(
            f"owner.available_time_per_day is {owner.available_time_per_day} — "
            f"must be at least 1 minute."
        )

    # Check 4 & 5: per-task duration bounds.
    if isinstance(task_list, list):
        for task in task_list:
            duration = getattr(task, "duration", None)
            name = getattr(task, "name", repr(task))
            if duration is None:
                errors.append(f"Task '{name}' is missing a 'duration' attribute.")
                continue
            if duration < 1:
                errors.append(
                    f"Task '{name}' has invalid duration: {duration} min "
                    f"(must be >= 1 min)."
                )
            if duration > _MAX_TASK_DURATION_MINUTES:
                errors.append(
                    f"Task '{name}' has unrealistic duration: {duration} min "
                    f"(maximum is {_MAX_TASK_DURATION_MINUTES} min / 8 hours)."
                )

    return errors


def check_output(plan: list, warnings: list) -> dict:
    """Validate the agent's output before it is shown to the user.

    Status levels
    ~~~~~~~~~~~~~
    ``"empty"``
        *plan* is an empty list — no tasks were scheduled.
    ``"warning"``
        *plan* is non-empty but *warnings* contains one or more strings.
    ``"ok"``
        *plan* is non-empty and *warnings* is empty.

    Parameters
    ----------
    plan:
        The ordered list of scheduled tasks produced by the agent.
    warnings:
        The merged list of warning strings collected during the agent run
        (validation warnings + critic concerns).

    Returns
    -------
    dict
        ``"status"`` (str)
            One of ``"ok"``, ``"warning"``, ``"empty"``.
        ``"flags"`` (list[str])
            Additional flags raised by this check.  Empty when status is
            ``"ok"``.  When status is ``"warning"``, contains the warnings
            list verbatim so the UI has a single place to read them from.
    """
    flags: list[str] = []

    # Guard: plan must be a list (not None or another type).
    if plan is None:
        return {
            "status": "empty",
            "flags": ["Plan is None — the agent may have failed unexpectedly."],
        }

    if not isinstance(plan, list):
        return {
            "status": "empty",
            "flags": [f"Plan has unexpected type '{type(plan).__name__}' — expected a list."],
        }

    # Status: empty plan.
    if len(plan) == 0:
        flags.append("No tasks were scheduled — all tasks may have been skipped.")
        return {"status": "empty", "flags": flags}

    # Status: warnings present.
    active_warnings = [w for w in (warnings or []) if isinstance(w, str) and w.strip()]
    if active_warnings:
        return {"status": "warning", "flags": active_warnings}

    # Status: all good.
    return {"status": "ok", "flags": []}
