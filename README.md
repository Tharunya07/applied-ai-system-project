# PawPal+ Applied AI System

PawPal+ is a pet care scheduling application extended with a full applied AI pipeline. It uses Retrieval-Augmented Generation (RAG) to ground scheduling decisions in curated pet care guidelines, an agentic plan-validate-critique loop to produce and audit daily care plans, and the Gemini API to surface tasks that may be missing from a pet owner's schedule.

## Original Base Project

The original PawPal+ project was a Streamlit app that let pet owners add pets and tasks, generate a daily care schedule using a priority and duration based greedy scheduler, and detect conflicts like duplicate tasks or budget overflow. It had pytest tests covering priority ordering, recurrence logic, and conflict detection, and a weighted scoring system that combined priority level, recurrence type, urgency, and task efficiency into a single numeric rank. It had no AI integration of any kind.

---

## New AI Features Added

**RAG (Retrieval-Augmented Generation)**
Before scheduling runs, the system indexes three markdown knowledge files in `docs/` — covering general pet care, breed-specific needs, and medical task guidelines. It uses a TF-IDF retriever to find the sections most relevant to the current task list and passes those sections to the planner as grounding context. This means scheduling decisions are informed by factual pet care recommendations, not just user input.

**Agentic Workflow**
`agent/planner.py` runs a multi-step loop: retrieve guidelines, validate tasks against those guidelines, run input guardrails, schedule with the core planner, critique the result, run output guardrails, and assemble a result dict with a full reasoning trace. A separate critic module (`agent/critic.py`) audits the proposed plan for missed medical tasks, low coverage, and priority inversions, and returns a confidence score.

**Gemini Integration**
After task validation, the planner optionally calls Gemini 1.5 Flash with a prompt that includes the owner's name, their pets, the current task list, and the top retrieved guideline snippets. The model is asked to flag missing tasks or concerns in 3-5 bullet points. The response is surfaced in the UI as an informational block. If no API key is present the step is skipped silently.

**Reliability Layer**
`reliability/guardrails.py` validates inputs before the agent runs (checking for null owners, empty task lists, and out-of-range durations) and validates output before it reaches the user (flagging empty plans and critical warnings). `reliability/evaluator.py` provides a batch evaluation harness that runs test cases through the full agent pipeline, scores each result against expected behaviours, and prints a pass/fail report.

---

## System Architecture

See `assets/architecture.png` for the system diagram.

When a user clicks "Generate Today's Plan" in the Streamlit UI, the app passes the owner object and task list to `run_agent` in `agent/planner.py`, which runs a 9-step loop. First, the RAG indexer reads the markdown files in `docs/` and the retriever scores each section against the current task names, returning the most relevant pet care guidelines as context. The planner then validates the tasks against those guidelines and optionally calls the Gemini API to suggest any tasks the owner may have missed. The core `Scheduler` from `pawpal_system.py` generates the greedy plan, and the critic in `agent/critic.py` scores it for confidence based on medical task coverage and overall task coverage. The final result dict — containing the plan, skipped tasks, warnings, confidence score, retrieved guidelines, AI suggestions, and a step-by-step trace — is stored in session state and rendered back in the UI.

---

## Design Decisions

The greedy scheduler was kept instead of a backtracking or exhaustive search approach because daily pet care tasks do not need globally optimal packing — they need predictable, priority-respecting results that an owner can understand at a glance. RAG uses TF-IDF keyword scoring rather than embeddings because the knowledge base is small (three files, 16 sections) and keyword overlap between task names and guideline headings is already high enough for useful retrieval without the added dependency and latency of an embedding model. Gemini suggestions are entirely optional and the agent continues normally if the API call fails, times out, or returns nothing, because the core scheduling logic should never depend on an external service that can hit quota limits or go down. Confidence scoring deducts heavily (0.30 per instance) for skipped medical tasks specifically because medication is the one task category where missing a scheduled occurrence can have real health consequences, and the penalty needs to be large enough to push the score below the 0.7 warning threshold even when everything else looks fine.

---

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd applied-ai-system-final
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

5. Add your Gemini API key to `.env`:
   ```
   GEMINI_API_KEY=your_actual_key_here
   ```
   The app runs without a key — Gemini suggestions will simply be skipped.

6. Start the app:
   ```bash
   streamlit run app.py
   ```

---

## How to Run the Evaluator

```bash
python -c "from reliability.evaluator import run_evaluation; print('evaluator ready')"
```

To run a full evaluation, pass a list of test-case dicts to `run_evaluation()`. Each test case needs `name`, `owner`, `task_list`, and `expected_behaviors`. The evaluator prints a `[PASS]` / `[FAIL]` report to the terminal and returns a summary dict with `total`, `passed`, `failed`, `scores`, and `summary`.

Supported behavior tags: `medical_tasks_included`, `high_priority_first`, `fits_budget`.

---

## Sample Input and Output

**Input**

```python
owner = Owner(
    name="Jamie",
    available_time_per_day=60,
    preferences=[],
    pets=[
        Pet(name="Biscuit", species="Dog", age=3, notes="Lab mix, energetic"),
        Pet(name="Mochi",   species="Cat", age=5, notes="Indoor, calm"),
    ],
)

tasks = [
    Task("Morning Walk",       duration=30, priority=Priority.HIGH,   category="Exercise",  pet=biscuit),
    Task("Insulin Medication", duration=5,  priority=Priority.HIGH,   category="Medical",   pet=biscuit),
    Task("Brush Mochi",        duration=15, priority=Priority.MEDIUM, category="Grooming",  pet=mochi),
]
```

**Output (result dict from `run_agent`)**

```
plan:       [Insulin Medication, Morning Walk, Brush Mochi]
skipped:    []
confidence: 1.0
warnings:   []
concerns:   []

retrieved_guidelines:
  - "Recommended Frequency for Common Pet Medications"  (medical_task_guidelines.md)
  - "Daily Walk Duration by Pet Size"                   (pet_care_guidelines.md)
  - "General Grooming Frequency Guidelines"             (pet_care_guidelines.md)

ai_suggestions:
  - Consider adding a dental brushing task for Biscuit — dental disease is common in Labs by age 3.
  - Mochi's grooming session is appropriate for a short-haired cat; weekly is sufficient.
  - Ensure Insulin Medication is administered at consistent 12-hour intervals.

trace:
  Step 1: Agent starting for owner Jamie
  Step 2: Building RAG index from docs/ — 16 section(s) indexed
  Step 3: Retrieved 5 relevant section(s)
  Step 4: Validating tasks — 0 warning(s)
  Step 4b: AI suggestions retrieved
  Step 5: Input validation passed
  Step 6: Scheduled 3 task(s), skipped 0
  Step 7: Confidence 1.00 | Coverage 100% | Medical tasks skipped: 0
  Step 8: Output status: ok
  Step 9: Assembling final result
```

---

## Sample Interactions

**Example 1 — Standard case**

- **Input:** Owner Jamie, 90 min budget, pet Biscuit (dog), tasks: Morning Walk (30 min HIGH), Feeding (10 min HIGH), Grooming (20 min MEDIUM)
- **Output:** All 3 tasks scheduled, confidence 1.00, RAG retrieved walk duration guidelines, no warnings

**Example 2 — Medical task present**

- **Input:** Owner Sara, 60 min budget, pet Mochi (cat), tasks: Thyroid Medication (5 min HIGH), Feeding (10 min HIGH), Playtime (60 min LOW)
- **Output:** Medication and Feeding scheduled, Playtime skipped (time ran out), confidence 1.00, medical task safety checked

**Example 3 — Budget overflow conflict**

- **Input:** Owner Alex, 30 min budget, pet Rex (dog), tasks: Morning Walk (30 min HIGH), Bath Time (45 min MEDIUM)
- **Output:** `validate()` flags budget overflow warning, only Morning Walk scheduled, confidence 0.95, skipped tasks shown in UI

---

## Testing Summary

The project has 10 pytest tests covering task completion, priority ordering, duration tiebreaking within the same priority tier, recurrence logic for daily and weekly tasks, duplicate conflict detection, and budget overflow handling. The reliability evaluator runs each test case against three behaviour tags — `medical_tasks_included`, `high_priority_first`, and `fits_budget` — and requires a score of 0.8 or higher to pass. Guardrails catch empty task lists, null owners, invalid durations under 1 minute or over 480 minutes, and empty output plans before they are ever shown to the user. Confidence averaged 1.0 on standard inputs with all tasks scheduled, and dropped to 0.7 when a single medical task was skipped due to a tight time budget.

---

## Project Structure

```
applied-ai-system-final/
|
├── app.py                      # Streamlit UI — all four sections including agentic plan display
├── pawpal_system.py            # Core data model: Pet, Owner, Task, Scheduler, Priority
├── main.py                     # Standalone demo script
├── logger.py                   # Centralised rotating file + console logger
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
|
├── agent/
│   ├── planner.py              # Agentic loop: RAG → validate → schedule → critique → output
│   └── critic.py               # Plan auditor: confidence score, medical task checks
|
├── rag/
│   ├── indexer.py              # Loads docs/, builds TF-IDF word-frequency index
│   └── retriever.py            # Scores and ranks index sections against a query
|
├── reliability/
│   ├── guardrails.py           # Input and output validation around the agent loop
│   └── evaluator.py            # Batch test harness: run cases, score, print pass/fail report
|
├── docs/
│   ├── pet_care_guidelines.md      # Walk duration, feeding frequency, grooming, hydration
│   ├── breed_specific_care.md      # Exercise and grooming needs for 5 dog and 3 cat breeds
│   └── medical_task_guidelines.md  # Medication frequency, skipping risks, vet visit schedule
|
├── tests/
│   └── test_pawpal.py          # 9 pytest tests covering the core scheduling logic
|
├── logs/
│   └── pawpal_agent.log        # Runtime log written by logger.py (auto-created)
|
├── assets/                     # Architecture diagram and static assets
├── Images/                     # UI screenshots
└── UML/                        # UML diagrams from the base project
```

---
## Stretch Features

### RAG Enhancement (+2pts)
The retrieval system uses three custom knowledge files across different domains:
`pet_care_guidelines.md` (walk duration, feeding, grooming, hydration), `breed_specific_care.md` (exercise and grooming needs for 5 dog breeds and 3 cat breeds), and `medical_task_guidelines.md` (medication frequency, skipping risks, vet visit schedules). Retrieved sections are actively used to validate tasks before scheduling and to ground the Gemini prompt — they are not just printed alongside the answer.

### Agentic Workflow Enhancement (+2pts)
The agent runs a 9-step reasoning loop with fully observable intermediate steps. Each step is logged to a trace list and displayed in the Agent Trace expander in the UI. The decision chain is: retrieve guidelines → validate tasks → get AI suggestions → run input guardrails → schedule → critique plan → run output guardrails → assemble result. Every decision point is visible and inspectable without reading log files.

### Test Harness (+2pts)
`reliability/evaluator.py` runs predefined test cases through the full agent pipeline and prints a pass/fail report to the terminal. Each case is scored against behaviour tags (medical_tasks_included, high_priority_first, fits_budget) with a pass threshold of 0.8.
The harness returns a summary dict with total, passed, failed, individual scores, and a human-readable summary string.