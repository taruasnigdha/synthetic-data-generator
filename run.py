#!/usr/bin/env python3
"""
Synthetic Data Fabricator — CLI Runner
======================================
Starts the mock SAP server in a background thread, then runs
the ADK agent with a user-supplied prompt (or a default demo prompt).

Features:
    - Multi-agent architecture with visible agent transfers
    - Color-coded console output by agent type
    - Tool call tracking with timing

Usage:
    python run.py "Generate 5 overdue invoices for a US-based customer with a credit limit below $5,000"
    python run.py   # uses default demo prompt
"""

import sys
import threading
import time
import asyncio

from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mock_sap_server.app import app as flask_app
from synthetic_data_agent import root_agent


# ---------------------------------------------------------------------------
# ANSI colors for agent-specific output
# ---------------------------------------------------------------------------
class C:
    """ANSI color codes for terminal output."""
    RESET    = "\033[0m"
    BOLD     = "\033[1m"
    DIM      = "\033[2m"
    # Agent colors
    ORCH     = "\033[95m"   # magenta/purple — orchestrator
    DATA     = "\033[94m"   # blue — data gen
    BP       = "\033[33m"   # yellow/orange — business partner
    TX       = "\033[92m"   # green — transaction
    VER      = "\033[96m"   # cyan — verification
    CLEAN    = "\033[91m"   # red — cleanup
    # Status
    OK       = "\033[92m"
    ERR      = "\033[91m"
    TOOL     = "\033[93m"
    INFO     = "\033[94m"


AGENT_COLORS = {
    "synthetic_data_fabricator": C.ORCH,
    "data_generation_agent":    C.DATA,
    "business_partner_agent":   C.BP,
    "transaction_agent":        C.TX,
    "verification_agent":       C.VER,
    "cleanup_agent":            C.CLEAN,
}

AGENT_ICONS = {
    "synthetic_data_fabricator": "🧠",
    "data_generation_agent":    "📊",
    "business_partner_agent":   "🏢",
    "transaction_agent":        "📄",
    "verification_agent":       "✅",
    "cleanup_agent":            "🗑️",
}


def _agent_prefix(agent_name: str) -> str:
    """Return a colored agent prefix for console output."""
    color = AGENT_COLORS.get(agent_name, C.DIM)
    icon = AGENT_ICONS.get(agent_name, "🤖")
    label = agent_name.replace("_agent", "").replace("_", " ").title()
    return f"{color}{icon} [{label}]{C.RESET}"


# ---------------------------------------------------------------------------
# Default demo prompt
# ---------------------------------------------------------------------------
DEFAULT_PROMPT = (
    "Generate 5 overdue invoices for a US-based customer "
    "with a credit limit below $5,000."
)


# ---------------------------------------------------------------------------
# Start mock SAP server in background
# ---------------------------------------------------------------------------
def start_mock_server(port: int = 8080):
    """Run Flask in a daemon thread so it doesn't block the agent."""
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)   # quieten Flask logs during agent run

    thread = threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=port, debug=False),
        daemon=True,
    )
    thread.start()
    time.sleep(1)  # give the server a moment to start
    print(f"✅  Mock SAP server running at http://localhost:{port}")
    print(f"    Dashboard UI → http://localhost:{port}/\n")


# ---------------------------------------------------------------------------
# Run the agent
# ---------------------------------------------------------------------------
async def run_agent(prompt: str):
    """Execute the ADK agent and print the conversation."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="synthetic_data_fabricator",
        user_id="dev-user",
    )

    runner = Runner(
        agent=root_agent,
        app_name="synthetic_data_fabricator",
        session_service=session_service,
    )

    print(f"{C.BOLD}{'=' * 70}")
    print(f"🧪  SYNTHETIC DATA FABRICATOR — Multi-Agent Architecture")
    print(f"{'=' * 70}{C.RESET}")
    print(f"\n{C.INFO}📋  Prompt:{C.RESET} {prompt}\n")
    print(f"{C.DIM}{'─' * 70}{C.RESET}")

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    final_response = ""
    last_agent = None

    async for event in runner.run_async(
        user_id="dev-user",
        session_id=session.id,
        new_message=user_message,
    ):
        # Detect agent transfers
        current_agent = getattr(event, 'author', None) or ""
        if current_agent and current_agent != last_agent:
            if last_agent is not None:
                print(f"\n{C.DIM}  {'─' * 50}{C.RESET}")
            prefix = _agent_prefix(current_agent)
            print(f"\n{prefix} {C.BOLD}active{C.RESET}")
            last_agent = current_agent

        # Print tool calls and responses as they happen
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    prefix = _agent_prefix(current_agent)
                    print(f"\n{prefix} {C.TOOL}🔧 {part.function_call.name}{C.RESET}")
                    if part.function_call.args:
                        for k, v in part.function_call.args.items():
                            val_str = str(v)
                            if len(val_str) > 100:
                                val_str = val_str[:100] + "…"
                            print(f"  {C.DIM}   {k}: {val_str}{C.RESET}")
                elif part.function_response:
                    resp = part.function_response.response
                    status = resp.get("status", "")
                    if status == "success":
                        print(f"  {C.OK}  ✓ {resp.get('message', 'OK')}{C.RESET}")
                        # Print key IDs
                        for id_key in ["BusinessPartner", "BillingDocument", "SalesOrder", "Product"]:
                            if id_key in resp:
                                print(f"  {C.INFO}    {id_key}: {resp[id_key]}{C.RESET}")
                    elif status == "error":
                        print(f"  {C.ERR}  ✗ {resp.get('message', 'Error')}{C.RESET}")
                    elif "count" in resp and "records" in resp:
                        count = resp['count']
                        label = resp.get('entity_type', 'records')
                        print(f"  {C.OK}  📊 Found {count} {label} records{C.RESET}")
                    elif "records" in resp:
                        print(f"  {C.OK}  📦 Generated {resp.get('count', len(resp['records']))} records{C.RESET}")
                    elif "deleted_count" in resp:
                        print(f"  {C.ERR}  🗑️  Deleted {resp['deleted_count']} records{C.RESET}")
                elif part.text:
                    final_response = part.text
                    # Show agent reasoning inline (for orchestrator)
                    if current_agent == "synthetic_data_fabricator" and not part.text.startswith("Here"):
                        # Show first 200 chars of reasoning
                        reasoning = part.text[:300]
                        if len(part.text) > 300:
                            reasoning += "…"
                        lines = reasoning.split("\n")
                        for line in lines[:6]:
                            if line.strip():
                                print(f"  {C.ORCH}💭 {line.strip()}{C.RESET}")

    print(f"\n{C.BOLD}{'=' * 70}")
    print(f"📝  FINAL RESPONSE")
    print(f"{'=' * 70}{C.RESET}")
    print(f"\n{final_response}")
    print(f"\n{C.BOLD}{'=' * 70}")
    print(f"🌐  Dashboard → http://localhost:8080/")
    print(f"{'=' * 70}{C.RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_PROMPT
    start_mock_server()
    asyncio.run(run_agent(prompt))


if __name__ == "__main__":
    main()
