import logging
from collections.abc import Callable
from typing import Any

from app.core.config import LANGSMITH_ENABLED, LANGSMITH_PROJECT


logger = logging.getLogger("warrenbuffet_ai")


def _identity_decorator(func: Callable) -> Callable:
    return func


def traceable_if_enabled(
    name: str,
    run_type: str = "chain",
    metadata: dict[str, Any] | None = None,
    process_inputs: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    process_outputs: Callable[[Any], Any] | None = None,
) -> Callable:
    if not LANGSMITH_ENABLED:
        return _identity_decorator

    try:
        from langsmith import traceable
    except Exception:
        logger.warning("LangSmith tracing requested but langsmith could not be imported.")
        return _identity_decorator

    safe_metadata = {
        "project": LANGSMITH_PROJECT,
        **(metadata or {}),
    }

    return traceable(
        name=name,
        run_type=run_type,
        project_name=LANGSMITH_PROJECT,
        metadata=safe_metadata,
        process_inputs=process_inputs,
        process_outputs=process_outputs,
        enabled=True,
    )


def summarize_chunks_output(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"output_type": type(output).__name__}

    chunks = output.get("chunks") or []
    return {
        "success": output.get("success"),
        "chunks_count": len(chunks),
        "error": output.get("error"),
    }


def summarize_answer_output(answer: Any) -> dict[str, Any]:
    text = str(answer or "")
    return {
        "answer_length": len(text),
        "has_answer": bool(text.strip()),
    }


def summarize_price_history_output(output: Any) -> dict[str, Any]:
    rows = output if isinstance(output, list) else []
    return {
        "rows_returned": len(rows),
    }
