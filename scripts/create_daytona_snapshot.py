"""
Daytona Snapshot Creation Script

This script creates a Daytona snapshot with all necessary Python packages
for the Data Analysis Agent.

Run this once to set up the sandbox environment:
    python scripts/create_daytona_snapshot.py
"""

import os
from daytona import CreateSnapshotParams, Daytona, DaytonaConfig, Image

config = DaytonaConfig(api_key=os.getenv("DAYTONA_API_KEY"))

# Initialize the Daytona client
daytona = Daytona(config)

# Snapshot name for reuse
snapshot_name = "data-analysis-agent-snapshot"

# Define the base image
image = (
    Image.debian_slim("3.13")
    .pip_install([
        "numpy",
        "pandas",
        "polars",
        "pyarrow",
        "duckdb",
        "scipy",
        "scikit-learn",
        "python-dateutil",
        "matplotlib",
        "seaborn",
    ])
    .workdir("/home/daytona")
)

# Create the snapshot and stream build logs
daytona.snapshot.create(
    CreateSnapshotParams(
        name=snapshot_name,
        image=image,
    ),
    on_logs=print,
)

print(f"\n✓ Snapshot '{snapshot_name}' created successfully!")
