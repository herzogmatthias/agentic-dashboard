"""
Tests for the search_content tool.
"""
from pathlib import Path

from src.tools.backend.filesystem import search_content


class TestSearchContent:
    """Tests for the search_content tool."""
    
    def test_search_simple_string(self, sample_dashboard_path: Path):
        """Should find simple string matches."""
        result = search_content("NextResponse", tool_context=None)
        
        assert "error" not in result
        assert result["total_matches"] > 0
        assert len(result["matches"]) > 0
    
    def test_search_regex_pattern(self, sample_dashboard_path: Path):
        """Should support regex patterns."""
        # Search for common TypeScript patterns
        result = search_content(r"import\s+", tool_context=None)
        
        assert "error" not in result
        # Should find import statements
        assert result["total_matches"] > 0
    
    def test_search_with_file_pattern(self, sample_dashboard_path: Path):
        """Should filter by file pattern."""
        result = search_content("import", file_pattern="*.ts", tool_context=None)
        
        assert "error" not in result
        # All matches should be in .ts files
        for match in result["matches"]:
            assert match["file"].endswith(".ts")
    
    def test_search_no_matches(self, sample_dashboard_path: Path):
        """Should return empty matches for non-existent patterns."""
        result = search_content("xyznonexistentpattern123", tool_context=None)
        
        assert "error" not in result
        assert result["total_matches"] == 0
        assert len(result["matches"]) == 0
    
    def test_search_invalid_regex(self):
        """Should return error for invalid regex patterns."""
        result = search_content("[invalid(regex", tool_context=None)
        
        assert "error" in result
        assert "Invalid regex" in result["error"]
    
    def test_search_respects_max_results(self, sample_dashboard_path: Path):
        """Should respect max_results parameter."""
        result = search_content("import", max_results=3, tool_context=None)
        
        assert len(result["matches"]) <= 3
        if result["total_matches"] > 3:
            assert result["truncated"] is True
