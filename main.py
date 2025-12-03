"""
Entrypoint for local REPL testing.
This wrapper allows running `python main.py` directly for the console chat interface.
"""

import json
from src.app.main import main
from src.tools.llm_client import Summarizer, get_snippet_summary_prompt

if __name__ == "__main__":
    main()
    