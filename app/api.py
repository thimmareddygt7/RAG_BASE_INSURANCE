"""FastAPI app: health, login, document list, ask, and admin reindex.

The caller's group always comes from the verified JWT. Request bodies cannot set it.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.auth import (AuthError, User, authenticate, create_token, decode_token,
                      load_users)
from app.config import ROOT, ConfigError, Settings, load_settings
from app.dataset import get_dataset, sync_dataset
from app.pipeline import RagPipeline, build_pipeline

log = logging.getLogger("insurance_rag")


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    stage: str | None
    mode: str
    disclaimer: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    group: str
    display_name: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    version_scope: Literal["latest", "all"] = "latest"


class CitationOut(BaseModel):
    doc_id: str
    page: int
    verified: bool


class SourceOut(BaseModel):
    doc_id: str
    title: str
    version: str
    page: int
    section: str
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    refused: bool
    refusal_reason: str
    citations: list[CitationOut]
    sources: list[SourceOut]
    timings_ms: dict[str, float]
    disclaimer: str


@dataclass
class Runtime:
    settings: Settings
    offline: bool
    dataset: str
    pipeline: RagPipeline | None = None
    users: dict[str, Any] = field(default_factory=dict)
    manifest: Path | None = None

    def get_pipeline(self) -> RagPipeline:
        """Built on first use so /health stays fast and model downloads happen once."""
        if self.pipeline is None:
            self.pipeline = build_pipeline(self.settings, offline=self.offline)
            if self.offline:  # in-memory store starts empty, so index the bundled demo data
                self.manifest = Path(tempfile.mkdtemp()) / "manifest.json"
                sync_dataset(self.pipeline, self.settings,
                             get_dataset(self.settings, self.dataset), True, self.manifest)
        return self.pipeline


def create_app(settings: Settings | None = None, offline: bool | None = None,
               pipeline_factory: Callable[[], RagPipeline] | None = None) -> FastAPI:
    import os

    settings = settings or load_settings()
    if offline is None:
        offline = os.environ.get("RAG_OFFLINE", "") == "1"
    runtime = Runtime(settings, offline, "synthetic" if offline else "real")
    if pipeline_factory is not None:
        runtime.pipeline = pipeline_factory()
    runtime.users = load_users(ROOT / settings.get("auth.users_file"))
    groups = settings.get("auth.groups")
    algorithm = settings.get("auth.algorithm")
    disclaimer = settings.get("app.disclaimer")

    app = FastAPI(title=settings.get("app.name"), version=settings.get("app.version"),
                  description=f"RAG over health insurance policies. {disclaimer}")
    app.add_middleware(CORSMiddleware, allow_origins=settings.get("server.cors_origins", []),
                       allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type"])
    bearer = HTTPBearer(auto_error=False)

    def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
        if creds is None:
            raise HTTPException(401, "Missing bearer token")
        try:
            return decode_token(creds.credentials, settings.require_auth_secret(), algorithm,
                                groups)
        except AuthError as exc:
            raise HTTPException(401, str(exc)) from exc
        except ConfigError as exc:
            log.error("auth misconfigured: %s", exc)
            raise HTTPException(500, "Server authentication is not configured") from exc

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.get("app.name"),
                              version=settings.get("app.version"), stage=settings.stage,
                              mode="offline-demo" if offline else "live", disclaimer=disclaimer)

    @app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
    def login(body: LoginRequest) -> TokenResponse:
        try:
            user = authenticate(runtime.users, body.username, body.password)
            token = create_token(user, settings.require_auth_secret(), algorithm,
                                 int(settings.get("auth.access_token_expire_minutes")))
        except AuthError as exc:
            raise HTTPException(401, str(exc)) from exc
        except ConfigError as exc:
            log.error("auth misconfigured: %s", exc)
            raise HTTPException(500, "Server authentication is not configured") from exc
        return TokenResponse(access_token=token, username=user.username, group=user.group,
                             display_name=user.display_name)

    @app.get("/documents", tags=["rag"])
    def documents(user: User = Depends(current_user)) -> list[dict]:
        return runtime.get_pipeline().store.list_docs([user.group])

    @app.post("/ask", response_model=AskResponse, tags=["rag"])
    def ask(body: AskRequest, user: User = Depends(current_user)) -> AskResponse:
        result = runtime.get_pipeline().ask(body.question, user.group, body.version_scope)
        sources = [SourceOut(doc_id=h.chunk.doc_id, title=h.chunk.title, version=h.chunk.version,
                             page=h.chunk.page, section=h.chunk.section, score=h.score,
                             text=h.chunk.text) for h in result.context_hits]
        return AskResponse(
            answer=result.answer, refused=result.refused, refusal_reason=result.refusal_reason,
            citations=[CitationOut(doc_id=c.doc_id, page=c.page, verified=c.verified)
                       for c in result.citations],
            sources=sources, timings_ms=result.timings_ms, disclaimer=disclaimer)

    @app.post("/admin/reindex", tags=["admin"])
    def reindex(user: User = Depends(current_user)) -> dict:
        if user.group != "admin":
            raise HTTPException(403, "Admin only")
        pipeline = runtime.get_pipeline()
        report = sync_dataset(pipeline, settings, get_dataset(settings, runtime.dataset),
                              runtime.offline, runtime.manifest)
        return report.as_dict()

    return app


app = create_app()
