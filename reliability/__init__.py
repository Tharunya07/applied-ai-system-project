"""
reliability/
============
Reliability layer for PawPal+.

Provides pre- and post-execution guardrails around the agentic workflow plus
an automated evaluation harness for regression testing and continuous quality
monitoring.

This package is designed to be thin and fast — every function must be safe to
call on every agent invocation without adding meaningful latency.

Modules
-------
guardrails : Input validation and output safety checks.
evaluator  : Batch evaluation harness for test-case scoring and reporting.
"""
