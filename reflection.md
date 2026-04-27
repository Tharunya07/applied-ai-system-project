# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**
- Briefly describe your initial UML design.
- A: I started with three core classes: Pet (stores name, species, age), Task (stores what needs to be done, how long it takes, and how urgent it is), and Scheduler (takes the task list and time budget and figures out what fits in the day). The idea was to keep data separate from logic that the Pet and Task just hold info, Scheduler does the thinking.
The three core actions a user can perform:
1. Add a pet: enter name, type, and basic info.
2. Add care tasks: add tasks like "morning walk" with duration and priority.
3. Generate a daily plan: app schedules tasks based on time available and priority.
I mapped this in a mermaid diagram.

- What classes did you include, and what responsibilities did you assign to each?
- A:  Pet stores the animal's basic info (name, species, age, notes). Task stores what needs to be done, how long it takes, its priority, and whether it is done. Owner stores the person's name, available time per day, and preferences. Scheduler is responsible for taking the task list, fitting tasks within the time budget, sorting by priority, and explaining why each task was included or skipped.

**b. Design changes**

- Did your design change during implementation?
A: Yes, after running the skeleton through Claude for a review, several structural issues came up that needed fixing before writing any real logic. Claude helped me understand the missing relationships and logic bottlenecks.

- If yes, describe at least one change and why you made it.
A: Yes. After AI review, I made two changes. First, changed Owner.pet to pets: List[Pet] so the app can support more than one pet. Second, replaced priority: str in Task with an enum (HIGH, MEDIUM, LOW) so sorting in generate_plan is reliable and not based on raw string comparison.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- A: The scheduler considers two main constraints i.e available time per day (the owner's total minute budget) and task priority (HIGH, MEDIUM, LOW). It also considers recurrence status, meaning a task only enters the plan if it is actually due today based on its daily or weekly schedule.
- How did you decide which constraints mattered most?
- A: Time budget and priority were the obvious starting point was without those two, the scheduler has no way to make decisions. Recurrence came later when I realized marking a weekly grooming task the same way as a daily feeding task made no sense. Preferences stayed as a placeholder because the app scope did not need it yet.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- A: The scheduler uses a greedy approach. It picks tasks one by one in priority and duration order and stops when time runs out. It never backtracks to check if skipping a long task would free up space for two shorter ones.
- Why is that tradeoff reasonable for this scenario?
- A: For a daily pet care app with a small task list, greedy is good enough. Owners care more about high priority tasks being done first than squeezing the maximum number of tasks into a day. A backtracking algorithm would add complexity with no real benefit for this use case.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- A:  I used AI across every phase, starting with design brainstorming to identify missing relationships in my class skeletons, then for implementing method bodies, adding algorithms like recurring task logic and conflict detection, generating test cases, and cleaning up docstrings. I also used it to review my own code before moving to the next phase rather than waiting until something broke.
- What kinds of prompts or questions were most helpful?
- A: The most useful prompts were specific and constrained telling AI exactly what to implement, what not to touch, and what format to return. Open-ended prompts like "improve my code" were less useful than "add filter_tasks() to Scheduler, read-only, these two parameters, return a list." Asking for feedback before writing code also saved a lot of rework.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- A: In Phase 3, AI suggested replacing the scheduling loop with a walrus operator list comprehension to make it more "Pythonic." I rejected it. It relied on side effects inside a comprehension which Python style guides explicitly discourage, it would have broken task.last_scheduled which recurring tasks depend on, and it would have been harder to debug. The explicit for loop was cleaner for this use case.
- How did you evaluate or verify what the AI suggested?
- A: I read the suggestion against what the method was actually supposed to do. The walrus version looked clever but skipped a required side effect. I also ran main.py after every change to verify terminal output matched expected behavior before moving on.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- A:  Nine behaviors total, task completion status flipping correctly, task addition increasing pet task count, scheduled tasks fitting within budget, priority ordering being respected, duration tiebreaking within same priority, pet with no tasks returning empty list without crashing, budget overflow handling at least one task, weekly recurrence exclusion when not due, and duplicate detection in validate().
- Why were these tests important?
- A: The scheduler makes decisions automatically so bugs would be silent, a wrong sort order or a missed recurrence check would not crash anything, it would just produce a wrong plan. Tests made those invisible failures visible before they reached the UI.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- A: 4 out of 5. The core scheduling logic is solid and all edge cases around priority, duration, recurrence, and conflict detection are covered. The gap is around filter_tasks() combinations, explain_plan() output content, and anything involving the UI directly, those are untested.
- What edge cases would you test next if you had more time?
- A: Filter combinations (pet name + incomplete only together), daily recurrence specifically, explain_plan() output format, and what happens when an owner has no pets at all.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
- A: The recurring task logic. Adding is_due() as a clean pre-filter inside generate_plan() without breaking the existing dataclass structure was a good design call. It meant the scheduler got smarter without the rest of the system changing.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
- A: Owner.preferences. It exists as a List[str] but does nothing, it was flagged as a gap in Phase 1 and never got wired into scheduling logic. I would either define what it controls (preferred categories, time of day) and actually use it in generate_plan(), or remove it entirely. Dead attributes in a design are just noise.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
- A: AI is fast at generating code but it does not know what you are building. The most useful thing I did was give AI a constrained problem with clear inputs and outputs instead of asking it to figure out the design. The human job is staying the architect everytime : deciding what gets built, what gets skipped, and what gets rejected even when the suggestion looks clever.
