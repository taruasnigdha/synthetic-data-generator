#!/usr/bin/env python3
"""
End-to-End Test: Email Reminder System
========================================
Tests the complete email notification workflow:
1. Creates Business Partner with email
2. Creates invoices with various due dates
3. Sends email reminders automatically
4. Verifies email delivery status
"""

import asyncio
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

from synthetic_data_agent import root_agent


async def test_email_reminders():
    """Test the complete email reminder workflow."""
    
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
    print("📧 TESTING EMAIL REMINDER SYSTEM")
    print("=" * 80)
    print()
    
    # Test scenario: Create invoices and send email reminders
    test_prompt = """
    Generate 5 invoices for a US customer with the following requirements:
    - Customer email: devstar3372@gcplab.me
    - 2 invoices should be overdue (past due dates)
    - 3 invoices should be due in the next 5 days
    - After creating the invoices, send email reminders to the customer for all invoices
    """
    
    print("📋 Test Scenario:")
    print(test_prompt.strip())
    print()
    print("=" * 80)
    print()

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=test_prompt)],
    )

    final_response = ""
    
    print("🤖 Agent Execution Log:")
    print("-" * 80)
    
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
    print("=" * 80)
    print("📝 FINAL RESPONSE")
    print("=" * 80)
    print()
    print(final_response)
    print()
    print("=" * 80)
    print("✅ Test Complete!")
    print()
    print("📬 Next Steps:")
    print("1. Check the terminal output above for email delivery status")
    print("2. Check the email inbox at devstar3372@gcplab.me for received emails")
    print("3. Verify the emails have:")
    print("   - Correct invoice details (ID, amount, due date)")
    print("   - Proper color coding (RED for overdue, YELLOW for due soon)")
    print("   - Professional HTML formatting")
    print("=" * 80)


if __name__ == "__main__":
    print()
    print("⚠️  IMPORTANT: Before running this test:")
    print("   1. Ensure the mock SAP server is running at http://localhost:8080")
    print("   2. Configure SMTP credentials in .env file")
    print("   3. Use a valid test email address")
    print()
    print("Starting test in 3 seconds...")
    print()
    
    import time
    time.sleep(3)
    
    asyncio.run(test_email_reminders())
