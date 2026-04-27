"""
agent/planner.py
================
Orchestrates the multi-step agentic loop for PawPal+.

The planner is the entry-point for agentic execution.  It retrieves relevant
guidelines from the RAG index, validates the incoming task list, invokes the
core PawPal+ scheduler, consults the critic, and assembles the final result
dict returned to the caller (e.g. the Streamlit UI or a reliability evaluator).

Gemini integration
------------------
If a ``GEMINI_API_KEY`` is present in ``.env`` (or the shell environment),
:func:`get_ai_suggestions` calls the Gemini 1.5 Flash model to surface any
tasks that might be missing and flag broad concerns.  The call is entirely
optional: a missing or invalid key causes the function to return an empty
string and log a warning without raising an exception.

Result dict schema
------------------
::

    {
        "plan":                list[Task],  # ordered scheduled tasks
        "skipped":             list[Task],  # tasks excluded from the plan
        "warnings":            list[str],   # merged warnings (validation + critic)
        "validation_warnings": list[str],   # guideline-based warnings only
        "confidence":          float,       # critic confidence in [0.0, 1.0]
        "concerns":            list[str],   # critic concern strings
        "trace":               list[str],   # step-by-step reasoning log
        "retrieved_guidelines":list[dict],  # RAG sections used to ground decisions
        "ai_suggestions":      str,         # Gemini suggestions (empty if unavailable)
    }

Functions
---------
run_agent(owner, task_list)
    Run the full agentic loop and return the result dict.

validate_tasks(task_list, retrieved_guidelines)
    Cross-check tasks against retrieved guidelines and return warnings.

get_ai_suggestions(task_list, retrieved_guidelines, owner)
    Call the Gemini API for missing-task suggestions and concerns.
"""

from __future__ import annotations

import os
from typing import Any

from logger import logger
from pawpal_system import Priority, Scheduler
from rag.indexer import build_index
from rag.retriever import retrieve
from reliability import guardrails
from agent import critic

# Path to docs/ relative to this file (agent/planner.py → project_root/docs/).
_DOCS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

# Keywords that identify a task as medication-related.
_MEDICAL_KEYWORDS = frozenset({"medication", "med", "medicine", "insulin", "antibiotic"})


# ---------------------------------------------------------------------------
# Task validation
# ---------------------------------------------------------------------------

def validate_tasks(task_list: list, retrieved_guidelines: list) -> list[str]:
    """Cross-check *task_list* against *retrieved_guidelines* and return warnings.

    Checks performed
    ~~~~~~~~~~~~~~~~
    1. **Suspiciously short duration** — any task with ``duration < 5`` minutes
       is flagged regardless of type.
    2. **Under-scheduled walks / exercise** — tasks whose name contains
       ``"walk"`` or ``"exercise"`` with ``duration < 20`` minutes are flagged;
       the most relevant retrieved guideline snippet is included in the message.
    3. **Medication priority** — tasks whose name contains any medical keyword
       but whose ``priority`` is not ``Priority.HIGH`` are flagged.

    Parameters
    ----------
    task_list:
        List of :class:`~pawpal_system.Task` objects to validate.
    retrieved_guidelines:
        List of section dicts returned by :func:`rag.retriever.retrieve`.
        Each dict has keys ``section_title``, ``filename``, ``content``,
        ``score``.

    Returns
    -------
    list[str]
        A (possibly empty) list of human-readable warning strings.
    """
    warnings: list[str] = []

    # Pre-build a snippet from guidelines mentioning walks/exercise for reuse.
    walk_snippet = ""
    for guideline in retrieved_guidelines:
        content_lower = guideline.get("content", "").lower()
        if "walk" in content_lower or "exercise" in content_lower:
            walk_snippet = guideline["content"][:200].replace("\n", " ")
            break

    for task in task_list:
        name_lower = task.name.lower()

        # --- Check 1: suspiciously short duration ---
        if task.duration < 5:
            warnings.append(
                f"Task '{task.name}' for {task.pet.name} has a very short duration "
                f"({task.duration} min) — may be too brief to complete properly."
            )

        # --- Check 2: walk/exercise under 20 minutes ---
        if any(kw in name_lower for kw in ("walk", "exercise")):
            if task.duration < 20:
                msg = (
                    f"Task '{task.name}' for {task.pet.name} is only {task.duration} min "
                    f"— guidelines recommend at least 20 min for walks/exercise."
                )
                if walk_snippet:
                    msg += f' Guideline reference: "{walk_snippet}..."'
                warnings.append(msg)

        # --- Check 3: medical task not set to HIGH priority ---
        if any(kw in name_lower for kw in _MEDICAL_KEYWORDS):
            if task.priority != Priority.HIGH:
                warnings.append(
                    f"Task '{task.name}' for {task.pet.name} appears to be a medication "
                    f"task but is set to '{task.priority.value}' priority — medication "
                    f"tasks should always be HIGH priority."
                )

    return warnings


# ---------------------------------------------------------------------------
# Gemini AI suggestions
# ---------------------------------------------------------------------------

def get_ai_suggestions(
    task_list: list,
    retrieved_guidelines: list,
    owner: Any,
) -> str:
    """Call Gemini 1.5 Flash to suggest missing tasks or flag broad concerns.

    Loads ``GEMINI_API_KEY`` from the environment (or ``.env`` via
    ``python-dotenv``).  If the key is absent or the API call fails for any
    reason, the function logs a warning/error and returns an empty string so
    the agent loop continues uninterrupted.

    The prompt instructs the model to act as a pet care expert and respond in
    3–5 bullet points, keeping output short and actionable.

    Parameters
    ----------
    task_list:
        The current list of :class:`~pawpal_system.Task` objects.
    retrieved_guidelines:
        Top RAG sections (up to 3 used for the prompt context).
    owner:
        The :class:`~pawpal_system.Owner` instance (provides name and pets).

    Returns
    -------
    str
        Gemini's suggestion text, or an empty string if unavailable.
    """
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv()

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            logger.warning(
                "get_ai_suggestions: GEMINI_API_KEY is not set — skipping AI suggestions"
            )
            return ""

        from google import genai  # noqa: PLC0415

        # Build a concise prompt from the owner's context.
        pet_names = (
            ", ".join(p.name for p in owner.pets) if owner.pets else "unknown"
        )
        task_summary = ", ".join(
            f"{t.name} ({t.duration} min)" for t in task_list
        )
        guideline_snippets = "\n".join(
            f"- {g['section_title']}: {g['content'][:150].replace(chr(10), ' ')}"
            for g in retrieved_guidelines[:3]
        )

        prompt = (
            "You are a pet care expert assistant. "
            "Given this owner's task list and pet care guidelines, suggest any important "
            "tasks that might be missing or flag any concerns. "
            "Be concise and specific. "
            f"Owner: {owner.name}. "
            f"Pets: {pet_names}. "
            f"Tasks: {task_summary}. "
            f"Guidelines:\n{guideline_snippets}\n"
            "Respond in 3-5 bullet points max."
        )

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt,
        )

        logger.info(
            "get_ai_suggestions: received suggestions for owner %s", owner.name
        )
        return response.text

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("get_ai_suggestions: API call failed — %s", str(exc))
        return ""


# ---------------------------------------------------------------------------
# Main agent entry-point
# ---------------------------------------------------------------------------

def run_agent(owner: Any, task_list: list) -> dict:
    """Run the full multi-step agentic loop and return a result dict.

    Execution steps
    ~~~~~~~~~~~~~~~
    1. Log agent start.
    2. Build RAG index from ``docs/``.
    3. Retrieve guidelines relevant to the task list.
    4. Validate tasks against retrieved guidelines.
    4b. Call :func:`get_ai_suggestions` for Gemini-backed recommendations.
    5. Run input guardrails — abort early on critical input errors.
    6. Run the PawPal+ scheduler to generate a plan.
    7. Critique the plan with :func:`~agent.critic.critique_plan`.
    8. Run output guardrails.
    9. Assemble and return the result dict.

    Every step appends a line to the ``trace`` list so callers can inspect
    the agent's reasoning.  The entire function is wrapped in a broad
    ``try/except`` so that unexpected errors return a safe error result
    rather than crashing the caller.

    Parameters
    ----------
    owner:
        A :class:`~pawpal_system.Owner` instance.
    task_list:
        List of :class:`~pawpal_system.Task` objects to schedule.

    Returns
    -------
    dict
        Result dict — see module docstring for the full schema.
    """
    trace: list[str] = []

    try:
        # ------------------------------------------------------------------
        # Step 1: Log start
        # ------------------------------------------------------------------
        logger.info("Agent starting for owner %s", owner.name)
        trace.append(f"Step 1: Agent starting for owner {owner.name}")

        # ------------------------------------------------------------------
        # Step 2: Build RAG index
        # ------------------------------------------------------------------
        trace.append("Step 2: Building RAG index from docs/")
        docs_path = os.path.normpath(_DOCS_FOLDER)
        index = build_index(docs_path)
        trace.append(f"  Indexed {index['doc_count']} section(s) from {docs_path}")

        # ------------------------------------------------------------------
        # Step 3: Retrieve relevant guidelines
        # ------------------------------------------------------------------
        trace.append("Step 3: Retrieving relevant guidelines")
        query = " ".join(task.name for task in task_list)
        retrieved = retrieve(query, index, top_k=5)
        trace.append(f"  Retrieved {len(retrieved)} relevant section(s)")
        if retrieved:
            trace.append(
                f"  Top section: '{retrieved[0]['section_title']}' "
                f"(score={retrieved[0]['score']:.4f})"
            )

        # ------------------------------------------------------------------
        # Step 4: Validate tasks against guidelines
        # ------------------------------------------------------------------
        trace.append("Step 4: Validating tasks against guidelines")
        validation_warnings = validate_tasks(task_list, retrieved)
        trace.append(f"  Found {len(validation_warnings)} validation warning(s)")
        for w in validation_warnings:
            logger.warning("validate_tasks: %s", w)

        # ------------------------------------------------------------------
        # Step 4b: Gemini AI suggestions
        # ------------------------------------------------------------------
        trace.append("Step 4b: Requesting AI suggestions from Gemini")
        ai_suggestions = get_ai_suggestions(task_list, retrieved, owner)
        if ai_suggestions:
            trace.append("  AI suggestions retrieved")
            logger.info("get_ai_suggestions: suggestions added to result")
        else:
            trace.append("  AI suggestions unavailable (no API key or call failed)")

        # ------------------------------------------------------------------
        # Step 5: Input guardrails — abort on errors
        # ------------------------------------------------------------------
        trace.append("Step 5: Running input guardrails")
        input_errors = guardrails.validate_input(owner, task_list)
        if input_errors:
            for err in input_errors:
                logger.warning("validate_input: %s", err)
            trace.append(
                f"  Input validation FAILED with {len(input_errors)} error(s): "
                f"{input_errors}"
            )
            return {
                "plan": [],
                "skipped": list(task_list),
                "warnings": input_errors,
                "validation_warnings": validation_warnings,
                "confidence": 0.0,
                "concerns": [],
                "trace": trace,
                "retrieved_guidelines": retrieved,
                "ai_suggestions": ai_suggestions,
            }
        trace.append("  Input validation passed")

        # ------------------------------------------------------------------
        # Step 6: Generate plan via Scheduler
        # ------------------------------------------------------------------
        trace.append("Step 6: Running scheduler to generate plan")
        scheduler = Scheduler(task_list=list(task_list), owner=owner)
        plan = scheduler.generate_plan()
        scheduled_ids = {id(t) for t in plan}
        skipped = [t for t in task_list if id(t) not in scheduled_ids]
        trace.append(f"  Scheduled {len(plan)} task(s), skipped {len(skipped)}")

        # ------------------------------------------------------------------
        # Step 7: Critique the plan
        # ------------------------------------------------------------------
        trace.append("Step 7: Running critic on proposed plan")
        critique_result = critic.critique_plan(plan, task_list)
        confidence = critique_result["confidence"]
        concerns = critique_result["concerns"]
        trace.append(
            f"  Confidence: {confidence:.2f} | "
            f"Coverage: {critique_result['coverage']:.0%} | "
            f"Medical tasks skipped: {critique_result['medical_tasks_skipped']}"
        )
        for c in concerns:
            logger.warning("critic: %s", c)

        # ------------------------------------------------------------------
        # Step 8: Output guardrails
        # ------------------------------------------------------------------
        trace.append("Step 8: Running output guardrails")
        all_warnings = validation_warnings + concerns
        output_check = guardrails.check_output(plan, all_warnings)
        trace.append(f"  Output status: {output_check['status']}")
        if output_check["flags"]:
            trace.append(f"  Output flags: {output_check['flags']}")

        # ------------------------------------------------------------------
        # Step 9: Assemble and return result
        # ------------------------------------------------------------------
        trace.append("Step 9: Assembling final result")
        logger.info(
            "Agent completed for owner %s — scheduled: %d, skipped: %d, "
            "confidence: %.2f, ai_suggestions: %s",
            owner.name,
            len(plan),
            len(skipped),
            confidence,
            "yes" if ai_suggestions else "none",
        )

        return {
            "plan": plan,
            "skipped": skipped,
            "warnings": all_warnings,
            "validation_warnings": validation_warnings,
            "confidence": confidence,
            "concerns": concerns,
            "trace": trace,
            "retrieved_guidelines": retrieved,
            "ai_suggestions": ai_suggestions,
        }

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Agent encountered an unhandled error for owner %s: %s",
            getattr(owner, "name", "unknown"),
            str(exc),
            exc_info=True,
        )
        trace.append(f"ERROR: {exc}")
        return {
            "plan": [],
            "skipped": list(task_list) if isinstance(task_list, list) else [],
            "warnings": [f"Agent encountered an error: {exc}"],
            "validation_warnings": [],
            "confidence": 0.0,
            "concerns": [],
            "trace": trace,
            "retrieved_guidelines": [],
            "ai_suggestions": "",
        }
