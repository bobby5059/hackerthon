"""구조화 JSON 로깅 + request_id + 민감정보 마스킹 (C3, SECURITY-03/07/13).

- 모든 로그 레코드에 request_id(contextvar) 부착.
- password/token/PIN 등 민감 필드는 메시지·extra에서 마스킹.
- 보안 이벤트(로그인 성공/실패, rate limit, 인가 거부)는 `security_event` 헬퍼로 기록.
"""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from typing import Any

# 요청 상관관계 ID. RequestIdMiddleware가 요청마다 set 한다.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# 마스킹 대상 키(부분 일치, 소문자 비교)
_SENSITIVE_KEYS = ("password", "token", "secret", "pin", "authorization", "access_token")

# 값 안에 노출될 수 있는 민감 패턴(예: "password": "xxx", table_password=1234)
_SENSITIVE_VALUE_RE = re.compile(
    r'("?(?:password|token|secret|pin|access_token)"?\s*[:=]\s*)("?)([^",}\s]+)(\2)',
    re.IGNORECASE,
)


def mask_sensitive(value: Any) -> Any:
    """민감정보 마스킹. dict/list/str 재귀 처리."""
    if isinstance(value, dict):
        return {
            k: ("***" if any(s in str(k).lower() for s in _SENSITIVE_KEYS) else mask_sensitive(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [mask_sensitive(v) for v in value]
    if isinstance(value, str):
        return _SENSITIVE_VALUE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}***{m.group(4)}", value)
    return value


class JsonFormatter(logging.Formatter):
    """로그 레코드를 JSON 한 줄로 직렬화."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_ctx.get(),
            "message": mask_sensitive(record.getMessage()),
        }
        # 구조화 extra(dict) 병합 + 마스킹
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(mask_sensitive(extra))
        if record.exc_info:
            # 스택은 서버 로그에만 기록(응답에는 미노출, SECURITY-15)
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """루트 로거에 JSON 포맷터 부착(중복 핸들러 방지)."""
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def get_logger(name: str = "table-order") -> logging.Logger:
    return logging.getLogger(name)


def security_event(event: str, **fields: Any) -> None:
    """보안 이벤트 로깅(로그인 성공/실패, rate limit, 인가 거부 등).

    민감 필드는 포맷터에서 마스킹되지만, 호출부에서도 비밀 값 자체는 전달하지 않는다.
    """
    logger = get_logger("table-order.security")
    logger.info(event, extra={"extra_fields": {"security_event": event, **fields}})
