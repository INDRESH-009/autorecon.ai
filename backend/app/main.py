"""FastAPI entrypoint — wires up routers, CORS, and a global JSON error handler.

The error handler is the one we learned to never skip: without it, unhandled
exceptions bypass CORS and the browser shows the useless "Failed to fetch"
instead of the real error.
"""
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import Base, engine
from app.db import models  # noqa: F401 — ensure models are registered before create_all

from app.api import jobs, master, reports, snapshots, vendors


log = logging.getLogger("recon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception):
        log.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": exc.__class__.__name__,
                "trace": traceback.format_exc().splitlines()[-6:],
            },
        )

    app.include_router(master.router)
    app.include_router(vendors.router)
    app.include_router(snapshots.router)
    app.include_router(jobs.router)
    app.include_router(reports.router)

    @app.get("/")
    def root():
        return {"app": settings.app_name, "ok": True}

    return app


app = create_app()
