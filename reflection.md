# PawPal+ Project Extension - Applied AI system

## Reflection

### Limitations and Biases

The RAG pipeline uses keyword matching, which means it only retrieves guidelines when a task name shares exact tokens with the indexed text. A task called "stroll" would not retrieve the walk duration guidelines even though the intent is identical, and a task called "meds" would not trigger the medication guidelines section. The knowledge base also covers dogs and cats in much more detail than other species — a rabbit or bird owner would get retrieval results pulled from the general sections, which are less specific and potentially less useful. The confidence scoring system has a structural bias toward high scores: it is entirely rule-based and will return 1.0 whenever no medical tasks are skipped, even if the plan is otherwise poor quality or leaves most low-priority tasks unscheduled. The scheduler also has no awareness of time of day, so a medication that must be given at a fixed hour looks identical to an optional grooming task in terms of how it is ranked and scheduled.

### Misuse Potential

The system is narrowly scoped to pet care scheduling, which limits its misuse potential considerably. That said, a user could add fake medical tasks to a schedule specifically to inflate the confidence score and make a weak plan appear reliable — the confidence penalty of 0.30 per skipped medical task means that including medical tasks and ensuring they fit the budget is an easy way to push confidence to 1.0 regardless of overall plan quality. A future fix would cross-reference task categories against the knowledge base to verify that tasks labelled as medical actually match known medication patterns. Gemini suggestions are displayed as informational text only and are never automatically added to the schedule, which is an intentional design choice: it prevents the AI from autonomously modifying a pet's care plan without the owner reviewing and adding the task themselves.

### Surprises During Reliability Testing

The guardrails caught more edge cases than expected, and most of them surfaced during normal use rather than adversarial testing. An empty task list and a task with zero duration both occurred naturally when a user submitted a form before filling it in completely, not through deliberate attempts to break the system. Confidence stayed at 1.0 more often than expected because most test inputs had enough time budget to fit all tasks, which meant the penalty system rarely activated. The most practically significant surprise was that the Gemini API quota ran out much faster than anticipated during iterative testing, which made the decision to treat the entire step as optional feel more like a necessity than a precaution.

### AI Collaboration

The most helpful suggestion from Claude during development was to use `id()` comparison instead of `==` for tracking which tasks had been scheduled versus skipped. The `Task` class defines `__eq__` based on name and pet name, which means two tasks for different pets that happen to share a name would incorrectly match. Using object identity via `id()` completely avoids that false-match problem and required no changes to the data model. One suggestion that was rejected was to use the walrus operator inside a list comprehension for the scheduling loop, which would have computed and assigned `task.last_scheduled` as a side effect inside the comprehension. This would have broken the explicit update logic in `generate_plan()`, violated Python style guidelines around side effects in comprehensions, and made the scheduling step much harder to read and debug — the explicit `for` loop was kept instead.

