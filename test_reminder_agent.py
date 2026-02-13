#!/usr/bin/env python3
"""
Test script for the Reminder Agent
===================================
Tests the reminder agent functionality with existing invoices.
"""

import asyncio
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

from synthetic_data_agent import root_agent


async def test_reminder_agent():
    """Test the reminder agent with a simple scenario."""
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="synthetic_data_fabricator",
        user_id="test-user",
    )

    runner = Runner(
        agent=root_agent,
        app_name="synthetic_data_fabricator",
        session_service=session_service,
    )

    print("=" * 70)
    print("🔔 TESTING REMINDER AGENT")
    print("=" * 70)
    print()

    # Test 1: Check for invoices due soon
    test_prompt = "What invoices are due in the next 30 days?"
    
    print(f"📋 Test Prompt: {test_prompt}")
    print("-" * 70)
    print()

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=test_prompt)],
    )

    final_response = ""
    
    async for event in runner.run_async(
        user_id="test-user",
        session_id=session.id,
        new_message=user_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_response = part.text

    print()
    print("=" * 70)
    print("📝 RESPONSE")
    print("=" * 70)
    print()
    print(final_response)
    print()


if __name__ == "__main__":
    asyncio.run(test_reminder_agent())
