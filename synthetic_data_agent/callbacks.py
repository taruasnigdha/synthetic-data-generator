"""
Agent Callbacks — Visible Reasoning & Event Logging
=====================================================
ADK callbacks that emit structured events to the mock server's
event log, powering the live Agent Activity dashboard.

These callbacks make the agent's "thinking" visible:
- Which agent is active
- What tool is being called and why
- The result of each tool call
- How long each operation took
"""

import time
import requests
from datetime import datetime, timezone

MOCK_SAP_URL = "http://localhost:8080"


def _emit_event(event: dict) -> None:
    """Send an agent activity event to the mock server's event log.

    Fire-and-forget — we don't want logging failures to break the agent.
    """
    try:
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        requests.post(
            f"{MOCK_SAP_URL}/api/agent-events",
            json=event,
            timeout=2,
        )
    except Exception:
        pass  # logging should never break the agent


# ---------------------------------------------------------------------------
# Timing state for tracking tool call durations
# ---------------------------------------------------------------------------
_tool_start_times: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Before-agent callback — logs agent activation / transfers
# ---------------------------------------------------------------------------
async def before_agent_callback(callback_context):
    """Called when a sub-agent is activated. Shows delegation in the dashboard."""
    agent_name = callback_context.agent_name if hasattr(callback_context, 'agent_name') else "unknown"

    _emit_event({
        "event_type": "agent_activated",
        "agent_name": agent_name,
        "icon": _agent_icon(agent_name),
    })
    return None  # let the agent proceed


# ---------------------------------------------------------------------------
# Tools that require HITL confirmation before execution
# ---------------------------------------------------------------------------
_DESTRUCTIVE_TOOLS = {"delete_record", "delete_by_filter", "reset_all_data"}


def _confirmation_hint(tool_name: str, args: dict) -> str:
    """Build a user-friendly confirmation hint for destructive tools."""
    if tool_name == "delete_record":
        return f"⚠️ Delete {args.get('entity_type', '?')} record '{args.get('record_id', '?')}'? This cannot be undone."
    elif tool_name == "delete_by_filter":
        filt = args.get("filter_expression", "")
        desc = f" matching '{filt}'" if filt else " (ALL records)"
        return f"⚠️ Delete {args.get('entity_type', '?')} records{desc}? This cannot be undone."
    elif tool_name == "reset_all_data":
        return "🚨 This will DELETE ALL data (Business Partners, Invoices, Sales Orders, Materials). Are you sure?"
    return "Confirm this action?"


# ---------------------------------------------------------------------------
# Before-tool callback — logs tool invocation + HITL for destructive tools
# ---------------------------------------------------------------------------
async def before_tool_callback(tool, args, tool_context):
    """Called before every tool execution.

    Two responsibilities:
    1. Log the tool call to the dashboard event feed.
    2. For destructive tools (delete/reset), request user confirmation
       via ADK's native HITL mechanism. Returns a short-circuit dict
       to prevent the tool from running until the user approves.
    """
    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
    agent_name = tool_context.agent_name if hasattr(tool_context, 'agent_name') else "unknown"

    # Track timing
    call_key = f"{agent_name}.{tool_name}.{id(args)}"
    _tool_start_times[call_key] = time.monotonic()

    # Truncate long arg values for display
    display_args = {}
    for k, v in (args or {}).items():
        val_str = str(v)
        display_args[k] = val_str[:150] + "…" if len(val_str) > 150 else val_str

    _emit_event({
        "event_type": "tool_called",
        "agent_name": agent_name,
        "tool_name": tool_name,
        "args": display_args,
        "icon": _agent_icon(agent_name),
    })

    # HITL: For destructive tools, request confirmation before executing
    if tool_name in _DESTRUCTIVE_TOOLS:
        # Check if user has already confirmed this call
        if tool_context.tool_confirmation and tool_context.tool_confirmation.confirmed:
            # User approved — let the tool run
            _emit_event({
                "event_type": "tool_confirmed",
                "agent_name": agent_name,
                "tool_name": tool_name,
                "icon": "✅",
            })
            return None  # proceed with the tool

        # Not yet confirmed — request user approval
        hint = _confirmation_hint(tool_name, args or {})
        tool_context.request_confirmation(
            hint=hint,
            payload={"tool_name": tool_name, "args": args},
        )

        _emit_event({
            "event_type": "confirmation_requested",
            "agent_name": agent_name,
            "tool_name": tool_name,
            "hint": hint,
            "icon": "⏳",
        })

        # Short-circuit: return None so ADK uses the confirmation event
        # instead of calling the tool
        return None

    return None  # non-destructive tool — proceed normally


# ---------------------------------------------------------------------------
# After-tool callback — logs tool result
# ---------------------------------------------------------------------------
async def after_tool_callback(tool, args, tool_context, tool_response):
    """Called after every tool execution.

    Logs the result and duration so the dashboard shows the outcome.

    NOTE: ADK passes all arguments as keyword args. The 4th parameter
    MUST be named `tool_response` to match the ADK calling convention.
    """
    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
    agent_name = tool_context.agent_name if hasattr(tool_context, 'agent_name') else "unknown"

    # Compute duration
    call_key = f"{agent_name}.{tool_name}.{id(args)}"
    start = _tool_start_times.pop(call_key, None)
    duration_ms = int((time.monotonic() - start) * 1000) if start else None

    # Extract key info from result
    result = tool_response
    if isinstance(result, dict):
        status = result.get("status", "ok")
        message = result.get("message", "")
        # Pull out key IDs for display
        ids = {}
        for key in ["BusinessPartner", "BillingDocument", "SalesOrder", "Product", "record_id"]:
            if key in result:
                ids[key] = result[key]
    else:
        status = "ok"
        message = str(result)[:200] if result else ""
        ids = {}

    _emit_event({
        "event_type": "tool_completed",
        "agent_name": agent_name,
        "tool_name": tool_name,
        "status": status,
        "message": message,
        "ids": ids,
        "duration_ms": duration_ms,
        "icon": _agent_icon(agent_name),
    })
    return None  # don't modify the result


# ---------------------------------------------------------------------------
# Agent icon mapping
# ---------------------------------------------------------------------------
def _agent_icon(agent_name: str) -> str:
    """Map agent names to emoji icons for the dashboard."""
    icons = {
        "orchestrator": "🧠",
        "data_generation_agent": "📊",
        "business_partner_agent": "🏢",
        "transaction_agent": "📄",
        "verification_agent": "✅",
        "cleanup_agent": "🗑️",
        "synthetic_data_fabricator": "🧪",
    }
    return icons.get(agent_name, "🤖")
