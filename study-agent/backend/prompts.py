"""
Prompt configuration for the Study Assistant Agent.

The current agent works offline using rule-based study responses.
This module is kept separate so prompt/AI logic can be expanded later
without coupling it to the API server.
"""

STUDY_AGENT_INSTRUCTION = """
You are a helpful study assistant.
Help students create study plans, revise effectively,
understand study techniques, and find common academic formulas.
"""
