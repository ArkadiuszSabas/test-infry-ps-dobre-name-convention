"""FastAPI entrypoint for the DocMind.ai worker service."""

from docmind_worker.bootstrap.app import create_app

app = create_app()
