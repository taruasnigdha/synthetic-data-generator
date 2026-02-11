#!/usr/bin/env python3
"""
Synthetic Data Fabricator — CLI Runner
======================================
Starts the mock SAP server in a background thread, then runs
the ADK agent with a user-supplied prompt (or a default demo prompt).

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

    print("=" * 70)
    print("🧪  SYNTHETIC DATA FABRICATOR")
    print("=" * 70)
    print(f"\n📋  Prompt: {prompt}\n")
    print("-" * 70)

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    final_response = ""
    async for event in runner.run_async(
        user_id="dev-user",
        session_id=session.id,
        new_message=user_message,
    ):
        # Print tool calls and responses as they happen
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    print(f"\n🔧  Tool Call: {part.function_call.name}")
                    if part.function_call.args:
                        for k, v in part.function_call.args.items():
                            val_str = str(v)
                            if len(val_str) > 100:
                                val_str = val_str[:100] + "..."
                            print(f"     {k}: {val_str}")
                elif part.function_response:
                    resp = part.function_response.response
                    status = resp.get("status", "")
                    if status == "success":
                        print(f"  ✅  {resp.get('message', 'OK')}")
                        # Print key IDs
                        for id_key in ["BusinessPartner", "BillingDocument", "SalesOrder", "Product"]:
                            if id_key in resp:
                                print(f"      {id_key}: {resp[id_key]}")
                    elif "count" in resp:
                        print(f"  📊  Found {resp['count']} records")
                    elif "records" in resp:
                        print(f"  📦  Generated {resp.get('count', len(resp['records']))} records")
                elif part.text:
                    final_response = part.text

    print("\n" + "=" * 70)
    print("📝  AGENT RESPONSE")
    print("=" * 70)
    print(f"\n{final_response}")
    print(f"\n{'=' * 70}")
    print("🌐  View all data → http://localhost:8080/")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_PROMPT
    start_mock_server()
    asyncio.run(run_agent(prompt))


if __name__ == "__main__":
    main()
