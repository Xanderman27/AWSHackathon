"""Production entry point: one origin serving both the API and the built web app.

    uvicorn app.serve:root --host 0.0.0.0 --port 8000

Why one origin rather than a static bucket plus a separate API host: the collaborative games
open a WebSocket, and a page served over HTTPS cannot open a `ws://` connection to somewhere
else. Same origin means same scheme, no CORS, and no mixed-content rule to fall foul of.

`app.main:app` stays exactly what it was — the API, mounted here at /api, which is the path
the front end already calls in development through the Vite proxy. Tests keep importing it
directly and are unaffected.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from .main import app as api

DIST = Path(__file__).resolve().parents[3] / "apps" / "web" / "dist"


class SinglePageApp(StaticFiles):
    """Serve built assets, and hand every unknown path to index.html.

    The front end routes on the client, so /teacher/learners/student-01 is a real page with no
    file behind it. Without this, a refresh on any route but / returns 404.
    """

    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as problem:
            if problem.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


root = FastAPI(title="Dori", docs_url=None, redoc_url=None)
root.mount("/api", api)

if DIST.is_dir():
    root.mount("/", SinglePageApp(directory=DIST, html=True), name="web")
else:  # the API still runs; you just have not built the front end yet
    @root.get("/")
    def _no_build():
        return {"error": "No web build found. Run: npm run build --prefix apps/web"}
