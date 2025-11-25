def build_planner_handoff_message(
    goal_description: str,
    audience: str,
    use_case: str,
    constraints: list[str],
    data_profile_md: str,
    cleaning_summary_md: str,
    summary_artifacts_json: str = "{}",
) -> str:
    """
    Build the orchestrator → planner handoff message exactly as required by the Planner Agent.

    All sections are wrapped in triple quotes so you can feed the whole string
    directly as the LLM user message when testing the Planner node.
    """
    constraints_text = "\n".join(f"- {c}" for c in constraints)

    return f"""
You are being called by the Orchestrator to plan a dashboard.

## User goal
- High-level goal: {goal_description}
- Target audience: {audience}
- Primary use case: {use_case}
- Constraints:
{constraints_text}

## Data context

### Data profile
```markdown
{data_profile_md.strip()}
```
Cleaning summary
```markdown
{cleaning_summary_md.strip()}
```
Additional summary artifacts (optional)
```json
{summary_artifacts_json.strip()}
```
"""