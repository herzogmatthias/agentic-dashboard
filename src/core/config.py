import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "data_analysis_agent_app"
USER_ID = "local-user"

# Daytona
DAYTONA_TARGET = os.getenv("DAYTONA_TARGET", "us")
DAYTONA_SNAPSHOT_NAME = os.getenv("DAYTONA_SNAPSHOT_NAME", "data-analysis-agent-snapshot")

# Local CSV source (optional auto-upload)
LOCAL_CSV_PATH = Path(os.getenv("LOCAL_CSV_PATH", "data/data.csv"))

# Paths inside the sandbox
SANDBOX_CSV_PATH = "workspace/original/data.csv"
SANDBOX_CLEANED_CSV_PATH = "workspace/cleaned/cleaned.csv"


ClEANED_DATA_FOLDER = "cleaned"

# Where to store artifacts on the host
ARTIFACTS_DIR = Path("artifacts")
RUNS_DIR = Path("runs")

# OpenRouter summarizer
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
SUMMARIZER_MODEL = "google/gemma-3-4b-it:free"

SLICE_LIMIT = 50

# Agent execution limits
MAX_TOOL_CALLS_ORCHESTRATOR = int(os.getenv("MAX_TOOL_CALLS_ORCHESTRATOR", "15"))
MAX_TOOL_CALLS_DATA_ANALYSIS = int(os.getenv("MAX_TOOL_CALLS_DATA_ANALYSIS", "20"))
MAX_TOOL_CALLS_PLANNER = int(os.getenv("MAX_TOOL_CALLS_PLANNER", "12"))

# Timeout and retry configuration
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "600"))  # 10 minutes
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
RETRY_BACKOFF_SECONDS = float(os.getenv("RETRY_BACKOFF_SECONDS", "2.0"))  # Initial backoff
