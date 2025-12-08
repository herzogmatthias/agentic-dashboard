"""
Core utility functions for data operations.

These are NOT agent tools - they are helper functions for callbacks and orchestration.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)

# Base path to the sample-dashboard project
SAMPLE_DASHBOARD_ROOT = Path("C:/Users/darks/Documents/agentic-dashboard/sample-dashboard")


def copy_data_to_project(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Copy all cleaned data files from run artifacts to the Next.js project's data/ folder.
    
    This is a callback helper function, NOT a tool. It should be called from the
    Dev Orchestrator's before_agent_callback to ensure data is copied before the
    Backend Dev Agent starts creating API routes.
    
    Copies all files from `{run_dir}/cleaned/` to `sample-dashboard/data/`.
    Creates the `data/` directory if it doesn't exist.
    
    Args:
        state: Session state dictionary containing 'run_dir' or 'cleaned_data_path'.
        
    Returns:
        Dictionary with:
        - copied_files: List of dictionaries with source and destination paths
        - destination_dir: Path to the destination data directory
        - total_files: Number of files copied
        - error: Error message if operation failed
    """
    if state is None:
        return {"error": "State not provided"}
    
    # Determine source directory
    cleaned_data_path = state.get("cleaned_data_path")
    run_dir = state.get("run_dir")
    
    if cleaned_data_path:
        # If a specific file path is given, use its parent directory
        source_path = Path(cleaned_data_path)
        if source_path.is_file():
            source_dir = source_path.parent
        else:
            source_dir = source_path
    elif run_dir:
        # Cleaned data is at {run_dir}/cleaned/
        source_dir = Path(run_dir) / "cleaned"
    else:
        return {"error": "Neither 'cleaned_data_path' nor 'run_dir' found in session state"}
    
    if not source_dir.exists():
        return {"error": f"Source directory not found: {source_dir}", "source": str(source_dir)}
    
    if not source_dir.is_dir():
        return {"error": f"Source is not a directory: {source_dir}", "source": str(source_dir)}
    
    # Destination directory in sample-dashboard
    dest_dir = SAMPLE_DASHBOARD_ROOT / "data"
    
    try:
        # Create destination directory if it doesn't exist
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        copied_files: list[dict[str, str]] = []
        
        # Copy all files from source to destination
        for source_file in source_dir.iterdir():
            if source_file.is_file():
                dest_file = dest_dir / source_file.name
                shutil.copy2(source_file, dest_file)
                
                copied_files.append({
                    "source": str(source_file),
                    "destination": str(dest_file),
                    "filename": source_file.name,
                })
        
        if not copied_files:
            return {
                "warning": "No files found in source directory",
                "source": str(source_dir),
                "destination_dir": str(dest_dir),
                "copied_files": [],
                "total_files": 0,
            }
        
        logger.info(
            "copy_data_to_project success",
            extra={
                "source": str(source_dir),
                "destination": str(dest_dir),
                "files": len(copied_files),
            },
        )
        
        return {
            "copied_files": copied_files,
            "destination_dir": str(dest_dir),
            "total_files": len(copied_files),
        }
        
    except Exception as exc:
        logger.error(
            "copy_data_to_project failed",
            extra={"source": str(source_dir), "error": str(exc)},
        )
        return {"error": f"Failed to copy data files: {exc}", "source": str(source_dir)}
