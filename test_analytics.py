#!/usr/bin/env python3
"""
Test Script: Analytics & Reporting Agent
=========================================
Tests the analytics and reporting functionality with sample data.
"""

import asyncio
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

from synthetic_data_agent import root_agent


async def test_analytics():
    """Test the analytics agent with various report types."""
    
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

    print("=" * 80)
    print("📊 TESTING ANALYTICS & REPORTING AGENT")
    print("=" * 80)
    print()

    # Test scenarios
    test_scenarios = [
        {
            "name": "Generate Test Data",
            "prompt": "Generate 10 invoices with mixed statuses: 3 paid, 3 overdue (30-60 days), 4 unpaid but not yet due",
        },
        {
            "name": "Aging Report",
            "prompt": "Show me the aging report for all unpaid invoices",
        },
        {
            "name": "Calculate KPIs",
            "prompt": "Calculate all KPIs for accounts receivable",
        },
        {
            "name": "Payment Summary",
            "prompt": "Give me a payment summary for the last 30 days",
        },
        {
            "name": "Top Customers",
            "prompt": "Show me the top 5 customers by outstanding amount",
        },
    ]

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_scenarios)}: {scenario['name']}")
        print(f"{'='*80}")
        print(f"Prompt: {scenario['prompt']}")
        print(f"{'-'*80}\n")

        user_message = types.Content(
            role="user",
            parts=[types.Part(text=scenario['prompt'])],
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

        print("Response:")
        print(final_response)
        print()

    print("=" * 80)
    print("✅ Analytics Testing Complete!")
    print("=" * 80)


if __name__ == "__main__":
    print()
    print("⚠️  IMPORTANT: Ensure the mock SAP server is running at http://localhost:8080")
    print()
    print("Starting analytics tests...")
    print()
    
    asyncio.run(test_analytics())
