from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from uuid import uuid4

from app.api.routes.agent import router as agent_router
from app.api.routes.db import router as db_router
from app.api.routes.demo import router as demo_router
from app.api.routes.documents import router as documents_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.harness import router as harness_router
from app.api.routes.health import router as health_router
from app.api.routes.rag import router as rag_router
from app.api.routes.tools import router as tools_router
from app.api.routes.watchdog import router as watchdog_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import get_default_security_headers

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "application_starting",
        extra={
            "environment": settings.environment,
            "reasoner": "deterministic-mock-v2",
        },
    )
    yield
    logger.info("application_stopping")


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.project_name,
        description=settings.project_description,
        version=settings.project_version,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic error inputs/context can echo entire credential-bearing bodies.
        return JSONResponse(status_code=422, content={"detail": [
            {key: item[key] for key in ("loc", "type", "msg") if key in item}
            for item in exc.errors()
        ]})

    @application.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log classification/correlation only: exception text can contain SQL,
            # credentials or request bodies. Never return a traceback to clients.
            logger.error("request_failed", extra={"request_id": request_id, "exception_type": type(exc).__name__})
            response = JSONResponse(status_code=500, content={"detail": "Internal server error.", "request_id": request_id})
        response.headers["X-Request-ID"] = request_id
        for header_name, header_value in get_default_security_headers().items():
            response.headers.setdefault(header_name, header_value)
        return response

    application.include_router(health_router, prefix=settings.api_v1_prefix)
    application.include_router(db_router, prefix=settings.api_v1_prefix)
    application.include_router(demo_router, prefix=settings.api_v1_prefix)
    application.include_router(agent_router, prefix=settings.api_v1_prefix)
    application.include_router(documents_router, prefix=settings.api_v1_prefix)
    application.include_router(rag_router, prefix=settings.api_v1_prefix)
    application.include_router(tools_router, prefix=settings.api_v1_prefix)
    application.include_router(watchdog_router, prefix=settings.api_v1_prefix)
    application.include_router(harness_router, prefix=settings.api_v1_prefix)
    application.include_router(evaluation_router, prefix=settings.api_v1_prefix)
    return application


app = create_application()
