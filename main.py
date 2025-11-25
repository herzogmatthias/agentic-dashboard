"""
Entrypoint for local REPL testing.
This wrapper allows running `python main.py` directly for the console chat interface.
"""

import json
from src.app.main import main
from src.prompts.system_prompts import build_snippet_summary_prompt
from src.tools.llm_client import Summarizer

if __name__ == "__main__":
    main()
    