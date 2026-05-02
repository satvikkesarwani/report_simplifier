import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.db.report_store import get_report_store
from app.utils.auth import decode_access_token

settings = get_settings()


class InMemoryRateLimiter:
    def __init__(self):
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        now = time.time()
        window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS
        request_times = self._requests[key]

        while request_times and request_times[0] < window_start:
            request_times.popleft()

        if len(request_times) >= settings.RATE_LIMIT_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait and try again.",
            )

        request_times.append(now)


rate_limiter = InMemoryRateLimiter()


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown-client"


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "", 1).strip()

    query_token = request.query_params.get("access_token")
    if query_token:
        return query_token.strip()

    return None


def enforce_optional_auth(request: Request) -> None:
    if not settings.AUTH_ENABLED:
        return

    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    expected_token = settings.APP_API_TOKEN
    if expected_token and token == expected_token:
        return
    if decode_access_token(token):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid bearer token.",
    )


def get_authenticated_user(request: Request) -> Optional[dict]:
    token = _extract_bearer_token(request)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    subject = payload.get("sub")
    if not subject:
        return None

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None

    return get_report_store().get_user(user_id)


def require_authenticated_user(request: Request) -> dict:
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
