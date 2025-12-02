from langchain_core.tools import tool
from typing import Annotated
from langgraph.prebuilt import InjectedState
from langchain_core.tools import InjectedToolCallId

# Test 1: With Returns section
@tool('test_with_returns', parse_docstring=True)
def test_with_returns(
    x: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId] = ""
) -> str:
    """Test tool with Returns.
    
    Args:
        x: The input.
        
    Returns:
        The output.
    """
    return x

# Test 2: Without Returns section
@tool('test_without_returns', parse_docstring=True)
def test_without_returns(
    x: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId] = ""
) -> str:
    """Test tool without Returns.
    
    Args:
        x: The input.
    """
    return x

print("Test 1 (with Returns):")
try:
    print(f"  Schema: {test_with_returns.args_schema.model_fields}")
    print("  SUCCESS")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 2 (without Returns):")
try:
    print(f"  Schema: {test_without_returns.args_schema.model_fields}")
    print("  SUCCESS")
except Exception as e:
    print(f"  FAILED: {e}")
