# Model Card - PawPal+ Applied AI System

## 1. Model Name and Purpose

**Name:** PawPal+ Applied AI System

**Purpose:** A pet care scheduling assistant that uses RAG, an agentic workflow, and Gemini AI to generate grounded, reliable daily care plans for pet owners.

---

## 2. Base Project

The original PawPal+ was a Streamlit app with a greedy priority scheduler, conflict detection, recurrence logic, and pytest tests. It had no AI integration of any kind.

---

## 3. AI Components Used

**RAG (Retrieval-Augmented Generation)**
TF-IDF retrieval over three pet care knowledge files in `docs/`: `pet_care_guidelines.md`, `breed_specific_care.md`, and `medical_task_guidelines.md`. Retrieved sections are used to validate tasks before scheduling and to ground the Gemini prompt.

**Agentic Workflow**
A 9-step plan-validate-critique loop in `agent/planner.py`. Steps: retrieve guidelines → validate tasks → get AI suggestions → run input guardrails → schedule → critique plan → run output guardrails → assemble result. Every step is logged to a trace list visible in the UI.

**Gemini API**
Optional missing task suggestions via `get_ai_suggestions()` in `agent/planner.py`. Calls Gemini 1.5 Flash 8B with a prompt built from the owner's task list and top retrieved guidelines. Skipped silently if no API key is present or if the call fails.

**Reliability Layer**
Input guardrails validate owner and task list before the agent runs. Output guardrails check for empty plans and critical warnings before results reach the user. A batch evaluator in `reliability/evaluator.py` scores test cases against expected behaviour tags and prints a pass/fail report.

---

## 4. Intended Use

**Intended for:**
- Pet owners planning daily care schedules for dogs, cats, and other companion animals
- Students and developers exploring applied AI system design patterns

**Not intended for:**
- Medical advice or veterinary diagnosis
- Commercial pet care services
- Species outside the scope of the knowledge base (exotic or farm animals)

---

## 5. Limitations and Biases

The RAG pipeline uses keyword matching, which means it only retrieves guidelines when a task name shares exact tokens with the indexed text. A task called stroll would not retrieve the walk duration guidelines even though the intent is identical. The knowledge base covers dogs and cats in much more detail than other species. The confidence scoring system has a structural bias toward high scores and will return 1.0 whenever no medical tasks are skipped even if the plan is otherwise poor quality. The scheduler has no awareness of time of day.

---

## 6. Misuse Potential

A user could add fake medical tasks to inflate the confidence score. A future fix would cross-reference task categories against the knowledge base. Gemini suggestions are displayed as informational text only and never automatically added to the schedule.

---

## 7. Testing and Reliability

- 10 pytest tests covering priority ordering, recurrence logic, conflict detection, and budget overflow handling
- Evaluator scores test cases against three behaviour tags: `medical_tasks_included`, `high_priority_first`, `fits_budget`
- Pass threshold is 0.8; confidence averaged 1.0 on standard inputs with all tasks scheduled
- Guardrails caught edge cases during normal use, not just adversarial testing , empty task lists and zero-duration tasks both occurred naturally
- Gemini API quota ran out faster than expected during iterative testing, which validated the decision to make the step entirely optional

---

## 8. AI Collaboration

The most helpful suggestion from Claude was to use `id()` comparison instead of `==` for tracking scheduled vs skipped tasks. One suggestion that was rejected was to use the walrus operator inside a list comprehension for the scheduling loop which would have broken `task.last_scheduled` updates and violated Python style guidelines.

---

## 9. Future Improvements

- Replace TF-IDF with embedding-based retrieval to handle synonyms and paraphrased task names
- Add time-of-day awareness to the scheduler so fixed-time medications are treated differently from flexible tasks
- Cross-reference task categories against the knowledge base to prevent confidence score inflation from fake medical tasks
