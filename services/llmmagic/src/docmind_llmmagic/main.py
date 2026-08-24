"""FastAPI entrypoint for the DocMind.ai LLM Magic service."""

from docmind_llmmagic.bootstrap.app import create_app

app = create_app()
