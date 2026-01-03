"""Tracing decorators and utilities for Langfuse integration."""
from functools import wraps
from typing import Optional, Dict, Any, Callable
import time
from langfuse.decorators import langfuse_context, observe

from src.observability.langfuse_client import get_langfuse


def trace_agent(agent_name: str, prompt_version: Optional[str] = None):
    """
    Decorator to trace agent execution with Langfuse.

    Args:
        agent_name: Name of the agent being traced
        prompt_version: Optional prompt version identifier

    Usage:
        @trace_agent("context_analyzer", prompt_version="v1.0")
        def analyze(self, decision: str, context: str) -> ContextAnalysis:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            langfuse = get_langfuse()

            if langfuse is None:
                # Langfuse not configured, run without tracing
                return func(*args, **kwargs)

            # Extract metadata from kwargs if available
            metadata = {
                "agent": agent_name,
            }
            if prompt_version:
                metadata["prompt_version"] = prompt_version

            # Use Langfuse observe decorator for automatic tracing
            observed_func = observe(name=agent_name, metadata=metadata)(func)
            return observed_func(*args, **kwargs)

        return wrapper
    return decorator


def create_trace(
    name: str,
    decision_id: Optional[str] = None,
    version: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Create a Langfuse trace for a decision evaluation.

    Args:
        name: Trace name (e.g., "decision_evaluation")
        decision_id: Decision ID for metadata
        version: Decision version for metadata
        metadata: Additional metadata

    Returns:
        Langfuse trace object or None if not configured
    """
    langfuse = get_langfuse()

    if langfuse is None:
        return None

    trace_metadata = metadata or {}
    if decision_id:
        trace_metadata["decision_id"] = decision_id
    if version:
        trace_metadata["version"] = version

    try:
        trace = langfuse.trace(
            name=name,
            metadata=trace_metadata
        )
        return trace
    except Exception as e:
        print(f"[WARNING] Failed to create Langfuse trace: {e}")
        return None


def create_span(
    trace_id: str,
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Create a Langfuse span within a trace.

    Args:
        trace_id: Parent trace ID
        name: Span name (e.g., "context_analyzer")
        input_data: Input data for the span
        metadata: Additional metadata

    Returns:
        Langfuse span object or None if not configured
    """
    langfuse = get_langfuse()

    if langfuse is None:
        return None

    try:
        span = langfuse.span(
            trace_id=trace_id,
            name=name,
            input=input_data,
            metadata=metadata
        )
        return span
    except Exception as e:
        print(f"[WARNING] Failed to create Langfuse span: {e}")
        return None


def log_score(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None
):
    """
    Log a score/metric to Langfuse.

    Args:
        trace_id: Trace ID to attach score to
        name: Score name (e.g., "context_completeness")
        value: Score value
        comment: Optional comment about the score
    """
    langfuse = get_langfuse()

    if langfuse is None:
        return

    try:
        langfuse.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment
        )
    except Exception as e:
        print(f"[WARNING] Failed to log Langfuse score: {e}")


def flush_langfuse():
    """Flush pending Langfuse events."""
    langfuse = get_langfuse()
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            print(f"[WARNING] Failed to flush Langfuse: {e}")
