"""Main Agentic AI application startup entry point.

Run:  uvicorn app.main:app --reload --port 8000
"""

from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
