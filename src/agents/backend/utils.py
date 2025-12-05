"""
Backend Agent utilities.

Helper functions for state management, file operations, and data handling.
"""

from pathlib import Path
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


def get_cleaned_data_files(run_dir: Path) -> list[str]:
    """
    Get list of all cleaned data files from the run directory.
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        List of file paths relative to sample-dashboard/data/
    """
    cleaned_dir = run_dir / "cleaned"
    
    if not cleaned_dir.exists():
        return []
    
    files = []
    for f in cleaned_dir.iterdir():
        if f.is_file():
            # Return path as it will appear in sample-dashboard/data/
            files.append(f"sample-dashboard/data/{f.name}")
    
    return sorted(files)



def format_cleaned_files_for_prompt(cleaned_files: list[str] | str | None) -> str:
    """
    Format cleaned files list for inclusion in a prompt.
    
    Args:
        cleaned_files: List of file paths, a single string, or None
        
    Returns:
        Formatted string for prompt
    """
    if isinstance(cleaned_files, list):
        return ", ".join(cleaned_files) if cleaned_files else "(none found)"
    elif cleaned_files:
        return str(cleaned_files)
    else:
        return "(none found)"
