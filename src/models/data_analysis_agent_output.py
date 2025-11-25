from pydantic import BaseModel, Field
from typing import List


class DataAnalysisOutput(BaseModel):
    """
    Final structured output returned by the Data Analysis Agent.

    This object is ALWAYS returned as the final JSON payload.
    The agent must not add fields or change structure. All arrays may be empty.
    """

    success: bool = Field(
        ...,
        description=(
            "Whether the data profiling/cleaning procedure completed successfully. "
            "True = all required computations executed and artifacts produced. "
            "False = agent requires further instructions or user clarifications."
        ),
    )

    additional_questions: List[str] = Field(
        default_factory=list,
        description=(
            "List of follow-up questions the agent needs to continue processing. "
            "Only populate if success=False. "
            "If empty, no additional user input is required."
        ),
    )

    additional_artifacts_path: List[str] = Field(
        default_factory=list,
        description=(
            "List of all relative file paths inside the Daytona sandbox that were created and are important for downstream use (additional calculations)"
            ". Each path must be relative to sandbox root "
            "(e.g. 'artifacts/data_analysis/cleaned.csv'). "
        ),
    )

    data_context: str = Field(
        "",
        description=(
            "Brief 2-3 sentence summary of the dataset and cleaning for the Planner Agent. "
            "Should include: (1) What the dataset represents and key dimensions, "
            "(2) Notable segments or patterns identified, "
            "(3) Data quality summary and any important caveats. "
            "Example: 'Customer transaction dataset with 15K records over 2 years. "
            "Identified 3 key segments: high-value/low-activity, new customers <6mo, at-risk. "
            "Data 95% complete after cleaning, minor date format issues resolved.'"
        ),
    )
