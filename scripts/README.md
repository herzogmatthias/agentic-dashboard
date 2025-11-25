# Scripts Directory

This directory contains setup and maintenance scripts for the agentic-dashboard project.

## Scripts

### `create_daytona_snapshot.py`

Creates a Daytona snapshot with all required Python packages for the Data Analysis Agent.

**Usage:**

```bash
python scripts/create_daytona_snapshot.py
```

**Requirements:**

- `DAYTONA_API_KEY` environment variable must be set
- Daytona Python SDK installed

This script needs to be run once to set up the sandbox environment before using the agent.
