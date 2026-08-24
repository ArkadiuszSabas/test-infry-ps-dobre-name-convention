"""FastAPI entrypoint for the DocMind.ai API service."""

from docmind_api.bootstrap.app import create_app

app = create_app()
