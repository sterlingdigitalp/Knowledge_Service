"""Native xAI Responses API provider with graceful fallback."""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from .accounting import (
    RequestTimer,
    UsageRecord,
    cost_from_xai_usage,
    estimate_token_cost,
    get_llm_accounting,
)
from .analyst_provider import AnalystLLMProvider
from .config import LLMConfig, load_llm_config
from .parse import parse_brief_item_response
from .prompts import (
    brief_item_enhancement_input,
    brief_item_enhancement_instructions,
    deep_dive_input,
    deep_dive_instructions,
    executive_summary_input,
    executive_summary_instructions,
    followup_input,
    followup_instructions,
    morning_brief_wording_input,
    morning_brief_wording_instructions,
    theme_naming_input,
    theme_naming_instructions,
)
from .provider import (
    BriefItemEnhancementRequest,
    BriefItemEnhancementResult,
    BriefPolishRequest,
    ConversationRequest,
    ConversationResult,
    LLMProvider,
    SummaryRequest,
    ThemeNamingRequest,
)


class XAIResponsesProvider(LLMProvider):
    """Production xAI/Grok provider using POST /v1/responses."""

    name = "xai_responses"

    def __init__(
        self,
        config: LLMConfig | None = None,
        fallback: LLMProvider | None = None,
        api_key: str | None = None,
    ):
        import os

        self.config = config or load_llm_config()
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        self._fallback = fallback or AnalystLLMProvider()
        self._accounting = get_llm_accounting()
        self._failure_count = 0
        self._retry_count = 0
        self._last_latency_ms = 0.0
        self._status = "ready" if self._available() else "unconfigured"

    def _available(self) -> bool:
        return bool(self.api_key)

    def runtime_metrics(self) -> Dict[str, Any]:
        usage = self._accounting.summary()
        return {
            "provider": self.name,
            "status": self._status,
            "model": self.config.model,
            "api_key_configured": self._available(),
            "last_latency_ms": round(self._last_latency_ms, 2),
            "failure_count": self._failure_count,
            "retry_count": self._retry_count,
            "fallback_provider": self._fallback.name,
            **usage,
        }

    def name_theme(self, request: ThemeNamingRequest) -> str:
        if not self._available():
            return self._fallback_with_record("name_theme", lambda: self._fallback.name_theme(request))
        text = self._generate(
            operation="name_theme",
            instructions=theme_naming_instructions(),
            user_input=theme_naming_input(request),
            max_output_tokens=32,
        )
        cleaned = _clean_title(text)
        if cleaned:
            return cleaned
        return self._fallback_with_record("name_theme", lambda: self._fallback.name_theme(request), forced=True)

    def executive_summary(self, request: SummaryRequest) -> str:
        if not self._available():
            return self._fallback_with_record("executive_summary", lambda: self._fallback.executive_summary(request))
        text = self._generate(
            operation="executive_summary",
            instructions=executive_summary_instructions(),
            user_input=executive_summary_input(request),
            max_output_tokens=280,
        )
        if text and len(text.split()) >= 20:
            return text
        return self._fallback_with_record(
            "executive_summary",
            lambda: self._fallback.executive_summary(request),
            forced=True,
        )

    def enhance_brief_item(self, request: BriefItemEnhancementRequest) -> BriefItemEnhancementResult:
        if not self._available():
            fallback = self._fallback.enhance_brief_item(request)
            return BriefItemEnhancementResult(
                title=fallback.title,
                executive_summary=fallback.executive_summary,
                why_it_matters=fallback.why_it_matters,
                provider=self._fallback.name,
            )
        text = self._generate(
            operation="enhance_brief_item",
            instructions=brief_item_enhancement_instructions(),
            user_input=brief_item_enhancement_input(request),
            max_output_tokens=320,
        )
        if text:
            parsed = parse_brief_item_response(text, request)
            parsed.provider = self.name
            if len(parsed.executive_summary.split()) >= 20:
                return parsed
        fallback = self._fallback.enhance_brief_item(request)
        self._accounting.record(UsageRecord(
            provider=self.name,
            model=self.config.model,
            operation="enhance_brief_item",
            status="fallback",
            fallback_used=True,
            error_type="forced_fallback",
        ))
        return BriefItemEnhancementResult(
            title=fallback.title,
            executive_summary=fallback.executive_summary,
            why_it_matters=fallback.why_it_matters,
            provider=self._fallback.name,
        )

    def converse(self, request: ConversationRequest) -> ConversationResult:
        if not self._available():
            fallback_text = self._fallback_with_record("converse", lambda: self._fallback.converse(request).text)
            return ConversationResult(text=fallback_text, provider=self._fallback.name, used_fallback=True)

        text, response_id = self._generate_with_id(
            operation="converse",
            instructions=deep_dive_instructions(),
            user_input=deep_dive_input(request),
            max_output_tokens=520,
            previous_response_id=request.previous_response_id,
        )
        if text:
            return ConversationResult(
                text=text,
                response_id=response_id,
                provider=self.name,
                used_fallback=False,
            )
        fallback_text = self._fallback_with_record(
            "converse",
            lambda: self._fallback.converse(request).text,
            forced=True,
        )
        return ConversationResult(text=fallback_text, provider=self._fallback.name, used_fallback=True)

    def polish_brief_entry(self, request: BriefPolishRequest) -> str:
        if not self._available():
            return self._fallback.polish_brief_entry(request)
        text = self._generate(
            operation="brief_polish",
            instructions=morning_brief_wording_instructions(),
            user_input=morning_brief_wording_input(request),
            max_output_tokens=180,
        )
        if text and len(text.split()) >= 12:
            return text
        return self._fallback.polish_brief_entry(request)

    def suggested_followups(
        self,
        *,
        title: str,
        executive_summary: str,
        contradiction_count: int = 0,
        corroboration_count: int = 0,
    ) -> List[str]:
        if not self._available():
            return self._fallback.suggested_followups(
                title=title,
                executive_summary=executive_summary,
                contradiction_count=contradiction_count,
                corroboration_count=corroboration_count,
            )
        text = self._generate(
            operation="suggested_followups",
            instructions=followup_instructions(),
            user_input=followup_input(
                title,
                executive_summary,
                contradiction_count=contradiction_count,
                corroboration_count=corroboration_count,
            ),
            max_output_tokens=120,
        )
        parsed = _parse_followups(text)
        if parsed:
            return parsed[:5]
        return self._fallback.suggested_followups(
            title=title,
            executive_summary=executive_summary,
            contradiction_count=contradiction_count,
            corroboration_count=corroboration_count,
        )

    def _fallback_with_record(self, operation: str, fn, *, forced: bool = False) -> str:
        self._status = "fallback"
        result = fn()
        self._accounting.record(UsageRecord(
            provider=self.name,
            model=self.config.model,
            operation=operation,
            status="fallback",
            fallback_used=True,
            error_type="forced_fallback" if forced else "unavailable",
        ))
        return result

    def _generate(
        self,
        *,
        operation: str,
        instructions: str,
        user_input: str,
        max_output_tokens: int,
        previous_response_id: str | None = None,
    ) -> str:
        text, _ = self._generate_with_id(
            operation=operation,
            instructions=instructions,
            user_input=user_input,
            max_output_tokens=max_output_tokens,
            previous_response_id=previous_response_id,
        )
        return text

    def _generate_with_id(
        self,
        *,
        operation: str,
        instructions: str,
        user_input: str,
        max_output_tokens: int,
        previous_response_id: str | None = None,
    ) -> tuple[str, Optional[str]]:
        timer = RequestTimer()
        retries = 0
        last_error = ""

        for attempt in range(self.config.max_retries + 1):
            if attempt > 0:
                retries += 1
                self._retry_count += 1
                time.sleep(self.config.retry_backoff_seconds * attempt)

            try:
                payload, response = self._post_response(
                    instructions=instructions,
                    user_input=user_input,
                    max_output_tokens=max_output_tokens,
                    previous_response_id=previous_response_id,
                )
                text = _extract_output_text(payload)
                response_id = str(payload.get("id") or "")
                status = str(payload.get("status") or "")
                if not text or status == "incomplete":
                    last_error = "incomplete_or_empty"
                    continue

                usage = payload.get("usage") or {}
                prompt_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
                completion_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
                total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
                actual_cost = cost_from_xai_usage(usage)
                estimated_cost = actual_cost if actual_cost is not None else estimate_token_cost(prompt_tokens, completion_tokens)

                self._last_latency_ms = timer.elapsed_ms
                self._status = "healthy"
                self._accounting.record(UsageRecord(
                    provider=self.name,
                    model=str(payload.get("model") or self.config.model),
                    operation=operation,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=timer.elapsed_ms,
                    estimated_cost_usd=estimated_cost,
                    actual_cost_usd=actual_cost,
                    status="success",
                    retries=retries,
                ))
                return text, response_id or None
            except _RetryableError as exc:
                last_error = exc.error_type
                if attempt >= self.config.max_retries:
                    break
                continue
            except Exception as exc:
                last_error = type(exc).__name__
                break

        self._failure_count += 1
        self._status = "degraded"
        self._accounting.record(UsageRecord(
            provider=self.name,
            model=self.config.model,
            operation=operation,
            latency_ms=timer.elapsed_ms,
            status="error",
            fallback_used=False,
            retries=retries,
            error_type=last_error or "unknown",
        ))
        return "", None

    def _post_response(
        self,
        *,
        instructions: str,
        user_input: str,
        max_output_tokens: int,
        previous_response_id: str | None,
    ) -> tuple[Dict[str, Any], Any]:
        import httpx

        body: Dict[str, Any] = {
            "model": self.config.model,
            "input": user_input,
            "instructions": instructions,
            "max_output_tokens": max_output_tokens,
            "temperature": self.config.temperature,
            "store": True,
        }
        if previous_response_id:
            body["previous_response_id"] = previous_response_id
            body.pop("instructions", None)
        if self.config.model.startswith("grok-4.3"):
            body["reasoning"] = {"effort": self.config.reasoning_effort}

        response = httpx.post(
            f"{self.config.base_url}/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self.config.timeout_seconds,
        )

        if response.status_code == 429:
            raise _RetryableError("rate_limit")
        if response.status_code in {500, 502, 503, 504}:
            raise _RetryableError("server_unavailable")
        if response.status_code >= 400:
            raise _RetryableError(f"http_{response.status_code}")

        payload = response.json()
        if payload.get("error"):
            raise _RetryableError("api_error")
        return payload, response


class _RetryableError(Exception):
    def __init__(self, error_type: str):
        self.error_type = error_type
        super().__init__(error_type)


def _extract_output_text(payload: Dict[str, Any]) -> str:
    chunks: List[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message" or item.get("role") == "assistant":
            for part in item.get("content") or []:
                if not isinstance(part, dict):
                    continue
                if part.get("type") in {"output_text", "text"} and part.get("text"):
                    chunks.append(str(part["text"]))
                elif isinstance(part.get("text"), str):
                    chunks.append(part["text"])
    if chunks:
        return _normalize_whitespace(" ".join(chunks))
    # OpenAI-compatible fallback shape
    for choice in payload.get("choices") or []:
        message = choice.get("message") or {}
        if message.get("content"):
            return _normalize_whitespace(str(message["content"]))
    return ""


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _clean_title(text: str) -> str:
    cleaned = text.strip().strip("\"'").rstrip(".")
    cleaned = re.sub(r"^(title|theme)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    words = cleaned.split()
    if not words or len(words) > 8:
        return ""
    if words[0].lower() in {"i", "the", "and", "a"}:
        return ""
    return cleaned


def _parse_followups(text: str) -> List[str]:
    if not text:
        return []
    lines = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-•*0123456789.) ")
        line = line.strip("\"'")
        if line.endswith("?"):
            lines.append(line)
        elif "?" in line:
            lines.append(line.split("?", 1)[0].strip() + "?")
    return lines