"""
Test script to verify _run_validation() works correctly.
"""

import subprocess
from pathlib import Path


def _run_validation(workspace_root: str) -> tuple[bool, str]:
    """
    Run npm run lint and npm run type-check in the sample-dashboard workspace.
    
    Returns:
        (success: bool, error_message: str)
        - success=True if both pass
        - success=False and error_message contains lint/type-check output if either fails
    """
    if not workspace_root or not Path(workspace_root).exists():
        return False, f"Invalid workspace root: {workspace_root}"
    
    errors = []
    
    # Run lint (shell=True required on Windows for npm to be found)
    try:
        result = subprocess.run(
            "npm run lint",
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )
        if result.returncode != 0:
            errors.append(f"LINT ERRORS:\n{result.stdout}\n{result.stderr}")
    except subprocess.TimeoutExpired:
        errors.append("LINT TIMEOUT (120s)")
    except Exception as e:
        errors.append(f"LINT ERROR: {e}")
    
    # Run type-check (shell=True required on Windows for npm to be found)
    try:
        result = subprocess.run(
            "npm run type-check",
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )
        if result.returncode != 0:
            errors.append(f"TYPE-CHECK ERRORS:\n{result.stdout}\n{result.stderr}")
    except subprocess.TimeoutExpired:
        errors.append("TYPE-CHECK TIMEOUT (120s)")
    except Exception as e:
        errors.append(f"TYPE-CHECK ERROR: {e}")
    
    if errors:
        return False, "\n---\n".join(errors)
    return True, ""


if __name__ == "__main__":
    # Test with actual sample-dashboard path
    workspace_root = r"C:\Users\darks\Documents\agentic-dashboard\sample-dashboard"
    
    print(f"Testing _run_validation with workspace: {workspace_root}")
    print(f"Workspace exists: {Path(workspace_root).exists()}")
    print("-" * 80)
    
    success, error_msg = _run_validation(workspace_root)
    
    print(f"Validation Success: {success}")
    print(f"\nError/Output:\n{error_msg if error_msg else '(no errors)'}")
    print("-" * 80)
    
    if success:
        print("[OK] Validation PASSED")
    else:
        print("[FAIL] Validation FAILED")
        print("\nFirst 1000 chars of error:")
        print(error_msg[:1000])
