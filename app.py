import streamlit as st
from pawpal_system import Pet, Owner, Task, Scheduler, Priority
from agent.planner import run_agent

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# --- Session state init ---
if "owner" not in st.session_state:
    st.session_state.owner = None
if "scheduler" not in st.session_state:
    st.session_state.scheduler = None
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "agent_result" not in st.session_state:
    st.session_state.agent_result = None

st.title("🐾 PawPal+")
st.caption("A daily pet care scheduler for busy owners.")
st.divider()

# ─────────────────────────────────────────────
# SECTION 1 — Owner + Pet Setup
# ─────────────────────────────────────────────
st.subheader("1. Owner & Pet Setup")

with st.form("owner_form"):
    st.markdown("**Owner details**")
    owner_name = st.text_input("Owner name", value="Jamie")
    available_time = st.number_input("Available time per day (minutes)", min_value=10, max_value=480, value=90)

    st.markdown("**Pet details**")
    pet_name = st.text_input("Pet name", value="Biscuit")
    species = st.selectbox("Species", ["Dog", "Cat", "Rabbit", "Bird", "Other"])
    age = st.number_input("Age (years)", min_value=0, max_value=30, value=3)
    notes = st.text_area("Notes (health, behaviour, etc.)", value="Energetic, needs daily walks")

    submitted = st.form_submit_button("Save Owner & Pet")

if submitted:
    pet = Pet(name=pet_name, species=species, age=age, notes=notes)
    owner = Owner(name=owner_name, available_time_per_day=available_time, preferences=[], pets=[pet])
    scheduler = Scheduler(task_list=[], owner=owner)
    st.session_state.owner = owner
    st.session_state.scheduler = scheduler
    st.session_state.tasks = []
    st.success(f"Saved! Owner **{owner_name}** with pet **{pet_name}** ({species}).")

if st.session_state.owner:
    owner = st.session_state.owner
    st.info(
        f"Current owner: **{owner.name}** — "
        f"{owner.get_available_time()} min/day — "
        f"Pets: {', '.join(p.name for p in owner.pets)}"
    )

st.divider()

# ─────────────────────────────────────────────
# SECTION 2 — Add a Task
# ─────────────────────────────────────────────
st.subheader("2. Add a Task")

if st.session_state.owner is None:
    st.warning("Complete Section 1 first to set up an owner and pet.")
else:
    owner = st.session_state.owner
    scheduler = st.session_state.scheduler
    pet_map = {pet.name: pet for pet in owner.pets}

    with st.form("task_form"):
        pet_choice = st.selectbox("Pet", list(pet_map.keys()))
        task_name = st.text_input("Task name", value="Morning Walk")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=30)
        priority_choice = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
        category = st.text_input("Category", value="Exercise")
        recurrence_choice = st.selectbox("Recurrence", ["none", "daily", "weekly"])

        task_submitted = st.form_submit_button("Add Task")

    if task_submitted:
        selected_pet = pet_map[pet_choice]
        task = Task(
            name=task_name,
            duration=int(duration),
            priority=Priority[priority_choice],
            category=category,
            pet=selected_pet,
            recurrence=None if recurrence_choice == "none" else recurrence_choice,
        )
        scheduler.add_task(task)
        selected_pet.tasks.append(task)
        st.session_state.scheduler = scheduler
        st.session_state.tasks = scheduler.task_list
        st.success(f"Added: **{task_name}** for {selected_pet.name} ({priority_choice}, {int(duration)} min)")

    if st.session_state.tasks:
        st.markdown("**Current task list:**")
        st.dataframe(
            [
                {
                    "Task": t.name,
                    "Pet": t.pet.name,
                    "Priority": t.priority.value.upper(),
                    "Duration (min)": t.duration,
                    "Category": t.category,
                    "Recurring": t.recurrence or "—",
                }
                for t in st.session_state.tasks
            ],
            use_container_width=True,
        )
    else:
        st.info("No tasks added yet.")

st.divider()

# ─────────────────────────────────────────────
# SECTION 3 — Filter Tasks
# ─────────────────────────────────────────────
st.subheader("3. Filter Tasks")

if st.session_state.owner is None:
    st.warning("Complete Section 1 first to set up an owner and pet.")
elif not st.session_state.tasks:
    st.info("Add tasks in Section 2 to use filters.")
else:
    owner = st.session_state.owner
    scheduler = st.session_state.scheduler
    pet_names = ["All Pets"] + [p.name for p in owner.pets]

    col1, col2 = st.columns(2)
    with col1:
        filter_pet = st.selectbox("Filter by pet", pet_names)
    with col2:
        incomplete_only = st.checkbox("Show incomplete tasks only")

    pet_name_arg = None if filter_pet == "All Pets" else filter_pet
    filtered = scheduler.filter_tasks(pet_name=pet_name_arg, incomplete_only=incomplete_only)

    if filtered:
        st.dataframe(
            [
                {
                    "Task": t.name,
                    "Pet": t.pet.name,
                    "Priority": t.priority.value.upper(),
                    "Duration (min)": t.duration,
                    "Completed": t.completed,
                    "Recurring": t.recurrence or "—",
                }
                for t in filtered
            ],
            use_container_width=True,
        )
    else:
        st.info("No tasks match the current filters.")

st.divider()

# ─────────────────────────────────────────────
# SECTION 4 — Generate Plan
# ─────────────────────────────────────────────
st.subheader("4. Generate Today's Plan")

if st.session_state.owner is None:
    st.warning("Complete Section 1 first to set up an owner and pet.")
elif not st.session_state.tasks:
    st.warning("Add at least one task in Section 2 before generating a plan.")
else:
    if st.button("Generate Today's Plan"):
        owner = st.session_state.owner

        with st.spinner("Running agentic planner..."):
            result = run_agent(owner, st.session_state.tasks)

        st.session_state.agent_result = result

        plan    = result["plan"]
        skipped = result["skipped"]

        # ── AI Suggestions ────────────────────────────────────────────
        if result["ai_suggestions"]:
            st.markdown("#### 💡 AI Suggestions")
            st.info(result["ai_suggestions"])

        # ── Validation Warnings ───────────────────────────────────────
        if result["validation_warnings"]:
            for w in result["validation_warnings"]:
                st.warning(w)

        # ── Confidence Score ──────────────────────────────────────────
        confidence = result["confidence"]
        col_conf, col_sched, col_skip = st.columns(3)
        col_conf.metric("Plan Confidence", f"{confidence:.0%}")
        col_sched.metric("Tasks Scheduled", len(plan))
        col_skip.metric("Tasks Skipped", len(skipped))

        if confidence < 0.7:
            st.warning("Low confidence plan — review concerns below.")
        else:
            st.success("High confidence plan")

        # ── Concerns ──────────────────────────────────────────────────
        if result["concerns"]:
            for c in result["concerns"]:
                st.error(c)

        # ── Plan tables ───────────────────────────────────────────────
        if not plan:
            st.error(
                "No tasks fit within the available time budget. "
                "Try reducing task durations or increasing available time."
            )
        else:
            time_used   = sum(t.duration for t in plan)
            time_budget = owner.get_available_time()

            col1, col2, col3 = st.columns(3)
            col1.metric("Time Used (min)", time_used)
            col2.metric("Time Budget (min)", time_budget)
            col3.metric("Time Remaining (min)", time_budget - time_used)

            st.markdown("#### Scheduled Tasks")
            st.table(
                [
                    {
                        "Task": t.name,
                        "Pet": t.pet.name,
                        "Priority": t.priority.value.upper(),
                        "Duration (min)": t.duration,
                        "Recurring": t.recurrence or "—",
                    }
                    for t in plan
                ]
            )

            if skipped:
                st.markdown("#### Skipped Tasks")
                st.table(
                    [
                        {
                            "Task": t.name,
                            "Pet": t.pet.name,
                            "Priority": t.priority.value.upper(),
                            "Duration (min)": t.duration,
                            "Reason": "Time ran out",
                        }
                        for t in skipped
                    ]
                )

        # ── Retrieved Guidelines ──────────────────────────────────────
        with st.expander("📚 Guidelines Used"):
            guidelines = result["retrieved_guidelines"]
            if guidelines:
                for g in guidelines:
                    st.markdown(f"**{g['section_title']}**  `{g['filename']}`")
                    preview = g["content"][:200].replace("\n", " ")
                    st.caption(f"{preview}{'…' if len(g['content']) > 200 else ''}")
                    st.divider()
            else:
                st.info("No guidelines were retrieved for this task list.")

        # ── Agent Trace ───────────────────────────────────────────────
        with st.expander("🔍 Agent Trace"):
            for step in result["trace"]:
                st.text(step)
