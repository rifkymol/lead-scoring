"""FastAPI entrypoint (Vercel detects `app` in app/main.py)."""

import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config
from app.errors import AppError, ProviderTimeout, TranscriptTooLarge
from app.evidence import validate_extraction
from app.extraction import extract
from app.models import ErrorDetail, ErrorResponse, ScoreRequest, ScoreResponse
from app.rationale import build_rationale
from app.scoring import score_extraction

logger = logging.getLogger("lead_scoring")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

app = FastAPI(title="Northern Coast lead-scoring API", version="1.0.0")


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if rid is None:
        rid = uuid.uuid4().hex
        request.state.request_id = rid
    return rid


def _error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    rid = _request_id(request)
    request.state.outcome = code
    body = ErrorResponse(error=ErrorDetail(code=code, message=message), request_id=rid)
    return JSONResponse(status_code=status, content=body.model_dump(), headers={"X-Request-ID": rid})


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = _request_id(request)
    started = time.perf_counter()
    response = await call_next(request)
    response.headers.setdefault("X-Request-ID", rid)
    # Minimal log line: no transcript text, no credentials.
    logger.info(
        "request_id=%s method=%s path=%s status=%s outcome=%s duration_ms=%d model=%s",
        rid,
        request.method,
        request.url.path,
        response.status_code,
        getattr(request.state, "outcome", "ok"),
        (time.perf_counter() - started) * 1000,
        getattr(request.state, "model", "-"),
    )
    return response


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Report locations and messages only; never echo submitted values.
    parts = []
    for err in exc.errors()[:5]:
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
        parts.append(f"{loc or 'body'}: {err.get('msg', 'invalid')}")
    return _error(request, 422, "invalid_request", "Invalid request. " + "; ".join(parts))


@app.exception_handler(StarletteHTTPException)
async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return _error(request, exc.status_code, code, str(exc.detail))


@app.exception_handler(AppError)
async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error(request, exc.status_code, exc.code, exc.message)


@app.exception_handler(Exception)
async def _unexpected_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("request_id=%s unexpected_error=%s", _request_id(request), type(exc).__name__)
    return _error(request, 500, "internal_error", "Unexpected server error.")


@app.get("/health")
async def health() -> dict:
    # Never calls the model.
    return {"status": "ok"}


async def _score(body: ScoreRequest) -> ScoreResponse:
    extraction = await extract(body.conversation)
    validate_extraction(extraction, body.conversation)
    result = score_extraction(extraction)
    return ScoreResponse(
        lead_id=body.lead_id,
        score=result.score,
        tier=result.tier,
        routing=result.routing,
        reasoning=build_rationale(extraction, result),
    )


@app.post("/score", response_model=ScoreResponse)
async def score(body: ScoreRequest, request: Request) -> JSONResponse:
    _request_id(request)
    request.state.model = config.openai_model()
    if body.transcript_chars() > config.MAX_TRANSCRIPT_CHARS:
        raise TranscriptTooLarge(
            f"Transcript exceeds the {config.MAX_TRANSCRIPT_CHARS}-character limit."
        )
    try:
        async with asyncio.timeout(config.HANDLER_DEADLINE_SECONDS):
            response = await _score(body)
    except TimeoutError as exc:
        raise ProviderTimeout("Scoring exceeded the request deadline.") from exc
    except AppError:
        raise
    except Exception as exc:  # unexpected application failure -> 500, never a fabricated score
        logger.error("request_id=%s unexpected_error=%s", request.state.request_id, type(exc).__name__)
        raise AppError("Unexpected server error.") from exc
    request.state.outcome = response.tier.lower()
    return JSONResponse(content=response.model_dump(), headers={"X-Request-ID": request.state.request_id})
