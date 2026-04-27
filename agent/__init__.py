"""
agent/
======
Agentic workflow package for PawPal+.

Implements a multi-step plan-then-critique loop that turns an owner's raw
task list into a validated, prioritised daily care plan grounded in the
RAG-retrieved pet care guidelines.

The loop runs as follows:

1. **Planner** (``agent.planner``) proposes a schedule by consulting the RAG
   index and applying scheduling logic from the core PawPal+ system.
2. **Critic** (``agent.critic``) audits the proposed plan, flags concerns,
   and returns a confidence score.
3. The planner may revise the plan in response to critic feedback (future
   iteration).

Modules
-------
planner : Orchestrates the agentic loop and produces the final plan dict.
critic  : Audits the plan for safety, completeness, and medical compliance.
"""
