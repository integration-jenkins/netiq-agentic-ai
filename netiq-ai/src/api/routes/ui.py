"""Main page route. The local UI goes in ui/web/."""

from fastapi.responses import FileResponse, HTMLResponse

from src.settings.env import settings

UI_DIR = settings.project_root / "ui" / "web"
_PLACEHOLDER = "<!doctype html><title>NetIQ AI</title><h1>NetIQ AI</h1><p>UI not built yet.</p>"


async def main_page():
    index = UI_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(_PLACEHOLDER)
