# 📧 Email Notifications Guide

## Overview

The Reminder Agent now includes **automated email notification** capabilities. When invoices are due soon or overdue, the system can automatically send professional HTML email reminders to Business Partners via SMTP.

## 🎯 Key Features

### ✅ What's Included

1. **Automatic Email Notifications**
   - Checks invoice due dates against current date
   - Sends email reminders to Business Partner's registered email
   - Professional HTML templates with color-coded priorities

2. **Email Storage in Business Partners**
   - Email field added to all Business Partner records
   - Required for receiving notifications
   - Default test email: `devstar3372@gcplab.me`

3. **SMTP Configuration**
   - Uses standard SMTP (Gmail, Outlook, etc.)
   - Configured via `.env` file
   - Supports TLS encryption

4. **Smart Priority System**
   - **Overdue**: RED urgent email (CRITICAL priority)
   - **Due in 1-3 days**: YELLOW warning email (HIGH priority)
   - **Due in 4-7 days**: YELLOW reminder email (MEDIUM priority)

## 📋 Setup Instructions

### Step 1: Configure SMTP in .env

Edit `synthetic-data-generator/.env` and add your SMTP credentials:

```bash
# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=SAP Reminder System
```

**For Gmail:**
1. Enable 2-Factor Authentication
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the App Password (not your regular password) in `SMTP_PASSWORD`

### Step 2: Create Business Partners with Email

When creating Business Partners, **always include an email address**:

```python
create_business_partner(
    name="Acme Corporation",
    country="US",
    city="New York",
    street="123 Main St",
    postal_code="10001",
    email="devstar3372@gcplab.me",  # REQUIRED for notifications
    credit_limit=10000,
    currency="USD"
)
```

### Step 3: Use Email-Enabled Reminder Tools

The system provides two email-enabled tools:

#### Option A: Manual Email for Specific Invoice
```python
send_reminder_email(
    invoice_id="INV1A2B3C4D",
    partner_id="BP0000000001",
    reminder_type="upcoming_due_date"
)
```

#### Option B: Automated Check & Email (RECOMMENDED)
```python
check_due_soon_and_email(days_ahead=7)
```

This automatically:
1. Finds all unpaid invoices due within 7 days
2. Creates reminder records
3. Sends email to each Business Partner
4. Reports success/failure for each email

## 🛠️ New Tools

### 1. send_reminder_email

Send an email notification for a specific invoice.

**Parameters:**
- `invoice_id` (required): Invoice ID (e.g., 'INV1A2B3C4D')
- `partner_id` (required): Business Partner ID (e.g., 'BP0000000001')
- `reminder_type` (optional): 'overdue_invoice', 'upcoming_due_date', or 'custom'

**Returns:**
```json
{
  "status": "success",
  "message": "Reminder email sent successfully",
  "recipient_email": "devstar3372@gcplab.me",
  "invoice_id": "INV1A2B3C4D",
  "partner_id": "BP0000000001",
  "subject": "📅 Payment Reminder: Invoice INV1A2B3C4D Due Soon",
  "days_until_due": 5
}
```

### 2. check_due_soon_and_email

Check for invoices due soon and automatically send email reminders.

**Parameters:**
- `days_ahead` (optional): How many days ahead to check (default: 7)

**Returns:**
```json
{
  "status": "success",
  "days_ahead": 7,
  "invoices_found": 3,
  "reminders_created": 3,
  "emails_sent": 3,
  "emails_failed": 0,
  "reminder_ids": ["REM1A2B3C4D", "REM2E42F7A0", "REM3B8845DA"],
  "email_results": [
    {
      "invoice_id": "INV1A2B3C4D",
      "partner_id": "BP0000000001",
      "email_status": "success",
      "recipient_email": "devstar3372@gcplab.me",
      "days_until_due": 5
    }
  ]
}
```

## 📧 Email Templates

### Template Features

- **Professional HTML Design**: Responsive, mobile-friendly layout
- **Color-Coded Priority**:
  - 🔴 RED: Overdue invoices (CRITICAL)
  - 🟡 YELLOW: Due soon (HIGH/MEDIUM)
  - 🔵 BLUE: Informational (LOW)
- **Invoice Details**: Number, amount, due date, days remaining
- **Personalization**: Business Partner name in greeting
- **Timestamp**: Auto-generated send time
- **Branding**: SAP Reminder System header

### Example Email (Overdue Invoice)

**Subject:** ⚠️ Overdue Invoice INV1A2B3C4D - Immediate Action Required

**Body:**
```
┌────────────────────────────────────────┐
│   💼 SAP Invoice Reminder              │
│   [OVERDUE - URGENT]                   │
└────────────────────────────────────────┘

Dear Acme Corporation,

This invoice is now overdue. Please arrange payment 
immediately to avoid any service interruptions.

┌────────────────────────────────────────┐
│ Invoice Number: INV1A2B3C4D            │
│ Due Date: 2024-11-01                   │
│ Amount Due: USD 25,000.00              │
└────────────────────────────────────────┘

If you have already processed this payment, 
please disregard this reminder.

Best regards,
SAP Reminder System
```

## 🚀 Usage Examples

### Example 1: Generate Invoices and Send Reminders

```bash
# Create invoices with email-enabled Business Partner
python run.py "Generate 3 invoices due in the next 7 days for a US customer with email devstar3372@gcplab.me"

# Check and send email reminders
python run.py "Send email reminders for all invoices due in the next 7 days"
```

**Expected Output:**
```
📧 [Reminder] active
📧 [Reminder] check_due_soon_and_email
     days_ahead: 7

✅ Found 3 invoices due soon
✅ Created 3 reminders
✅ Sent 3 emails successfully

Email Results:
- INV1A2B3C4D → devstar3372@gcplab.me ✓
- INV2E42F7A0 → devstar3372@gcplab.me ✓
- INV3B8845DA → devstar3372@gcplab.me ✓
```

### Example 2: Overdue Invoice Notifications

```bash
python run.py "Generate 2 overdue invoices and send urgent email reminders"
```

**Expected Flow:**
1. Creates Business Partner with email
2. Creates 2 overdue invoices (past due dates)
3. Sends CRITICAL priority RED emails automatically
4. Reports delivery status

### Example 3: Manual Email for Specific Invoice

```bash
python run.py "Send an email reminder for invoice INV1A2B3C4D"
```

### Example 4: Check Without Sending

```bash
# Just check, don't send emails
python run.py "What invoices are due in the next 14 days?"

# Then decide to send
python run.py "Send email reminders for those invoices"
```

## 🔧 Configuration

### SMTP Providers

#### Gmail
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Generate at myaccount.google.com/apppasswords
```

#### Outlook/Office 365
```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail
```bash
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

### Email Template Customization

Email templates are generated in `tools.py` via the `_get_email_template()` function. 

**To customize:**
1. Edit `synthetic_data_agent/tools.py`
2. Modify the `_get_email_template()` function
3. Update HTML, colors, message text, etc.

## 📊 Email Workflow

```
User Request
    ↓
Orchestrator Agent
    ↓
Reminder Agent
    ↓
check_due_soon_and_email(days_ahead=7)
    ↓
├─ Query invoices due within 7 days
├─ For each invoice:
│   ├─ Get Business Partner details
│   ├─ Check if email exists
│   ├─ Calculate days until due
│   ├─ Determine priority (critical/high/medium)
│   ├─ Create reminder record
│   ├─ Generate HTML email from template
│   ├─ Send via SMTP
│   └─ Track success/failure
└─ Return comprehensive results
```

## ⚠️ Troubleshooting

### Issue: "SMTP credentials not configured"

**Solution:** Add SMTP settings to `.env` file:
```bash
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Issue: "No email address found for Business Partner"

**Solution:** Business Partners need email addresses:
```python
# When creating, always include email
create_business_partner(
    name="Test Corp",
    email="devstar3372@gcplab.me",  # Add this!
    ...
)
```

### Issue: "Failed to send email: Authentication failed"

**Solutions:**
1. **Gmail**: Use App Password, not regular password
2. **Enable "Less secure app access"** (not recommended)
3. **Check 2FA**: Must be enabled for Gmail App Passwords
4. **Verify credentials**: Double-check username/password

### Issue: Emails not arriving

**Check:**
1. Spam/Junk folder
2. SMTP logs in terminal output
3. Recipient email validity
4. Network connectivity
5. SMTP server status

### Issue: "SMTPAuthenticationError"

**For Gmail:**
```bash
# Enable 2FA first, then:
# 1. Go to: https://myaccount.google.com/apppasswords
# 2. Generate App Password
# 3. Use that password in SMTP_PASSWORD
```

## 🧪 Testing

### Test Script

Create `test_email.py`:

```python
#!/usr/bin/env python3
from synthetic_data_agent.tools import send_reminder_email

# Assumes you have an invoice and business partner created
result = send_reminder_email(
    invoice_id="INV1A2B3C4D",
    partner_id="BP0000000001",
    reminder_type="upcoming_due_date"
)

print(result)
```

### Complete Test Workflow

```bash
# 1. Start mock server
cd synthetic-data-generator
.venv/bin/python3.14 -m mock_sap_server.app

# 2. In another terminal, create test data with email
.venv/bin/python3.14 run.py "Generate 3 invoices due in 5 days for customer with email devstar3372@gcplab.me"

# 3. Send email reminders
.venv/bin/python3.14 run.py "Send email reminders for all invoices due soon"

# 4. Check your email inbox at devstar3372@gcplab.me
```

## 📈 Advanced Usage

### Scheduled Email Reminders (Cron Job)

Create a daily cron job to send reminders:

```bash
#!/bin/bash
# daily_reminders.sh

cd /Users/I771312/GoogleADK/synthetic-data-generator

# Start mock server if not running
.venv/bin/python3.14 -m mock_sap_server.app &
sleep 2

# Send reminders for invoices due in next 7 days
.venv/bin/python3.14 run.py "Send email reminders for all invoices due in the next 7 days"

# Optional: Also check 14 and 30 days ahead
.venv/bin/python3.14 run.py "Send email reminders for invoices due in 14 days"
```

**Cron schedule (daily at 9 AM):**
```cron
0 9 * * * /path/to/daily_reminders.sh
```

### Custom Email Templates

Modify `_get_email_template()` in `tools.py` for custom branding:

```python
def _get_email_template(reminder_type: str, data: dict) -> tuple[str, str]:
    # Add your company logo
    logo_url = "https://your-company.com/logo.png"
    
    # Customize colors
    if reminder_type == "overdue_invoice":
        priority_color = "#ff0000"  # Your brand red
    
    # Add custom footer
    footer_html = """
    <div class="footer">
        <img src="{logo_url}" alt="Company Logo" height="40">
        <p>Your Company Name | Accounts Receivable</p>
        <p>Phone: +1-555-0123 | Email: ar@company.com</p>
    </div>
    """
    
    # ... rest of template
```

## 🔄 Workflow Integration

### Scenario 1: New Customer with Auto-Reminders

```python
# User prompt: "Create a US customer with 5 invoices due in next week, send email reminders"

Flow:
1. Data Generation Agent → Generate customer data
2. Business Partner Agent → Create with email='devstar3372@gcplab.me'
3. Transaction Agent → Create 5 invoices with future due dates
4. Reminder Agent → check_due_soon_and_email(days_ahead=7)
5. Result → 5 emails sent successfully
```

### Scenario 2: Daily Reminder Check

```python
# User prompt: "Check all invoices and send reminders where needed"

Flow:
1. Reminder Agent → check_due_soon_and_email(days_ahead=30)
2. Finds: 2 overdue (RED), 3 due in 5 days (YELLOW), 4 due in 20 days (YELLOW)
3. Sends 9 emails total
4. Reports: 9 sent, 0 failed
```

## 📝 Email Specifications

### Email Headers
- **From**: SAP Reminder System <your-configured-email>
- **To**: Business Partner's registered email
- **Subject**: Dynamic based on reminder type
- **Content-Type**: HTML (with fallback to plain text)

### Email Content Structure

```
┌─────────────────────────────────┐
│ Header (Color-coded)             │
│ - Title: SAP Invoice Reminder    │
│ - Priority Badge                 │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ Body                             │
│ - Greeting (personalized)        │
│ - Message Box (main message)     │
│ - Invoice Details Box:           │
│   • Invoice Number               │
│   • Due Date                     │
│   • Amount Due (large, colored)  │
│ - Additional Information         │
│ - Closing                        │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ Footer                           │
│ - System Information             │
│ - Timestamp                      │
└─────────────────────────────────┘
```

### Color Scheme

| Priority | Header Color | Text Color | Use Case |
|----------|--------------|------------|----------|
| CRITICAL | #dc3545 (Red) | White | Overdue invoices |
| HIGH | #ffc107 (Yellow) | Dark | Due in 1-3 days |
| MEDIUM | #ffc107 (Yellow) | Dark | Due in 4-7 days |
| LOW | #17a2b8 (Blue) | White | Informational |

## 🎓 Complete Examples

### Example 1: End-to-End with Email

```bash
# Terminal 1: Start mock server
cd synthetic-data-generator
.venv/bin/python3.14 -m mock_sap_server.app

# Terminal 2: Create scenario with emails
.venv/bin/python3.14 run.py "Generate 5 invoices for US customer with email devstar3372@gcplab.me. Make 2 overdue and 3 due in next week. Send email reminders for all."
```

**Expected Agent Actions:**
1. ✅ Generate customer data
2. ✅ Create Business Partner (email: devstar3372@gcplab.me)
3. ✅ Generate invoice data
4. ✅ Create 2 overdue invoices (past due dates)
5. ✅ Create 3 invoices due next week
6. ✅ Send 2 CRITICAL RED emails (overdue)
7. ✅ Send 3 MEDIUM YELLOW emails (due soon)
8. ✅ Report: 5 emails sent to devstar3372@gcplab.me

### Example 2: Daily Reminder Script

```python
#!/usr/bin/env python3
"""
Daily reminder script - Run via cron
"""
import asyncio
from google.adk.runners import Runner
from google.genai import types
from synthetic_data_agent import root_agent

async def send_daily_reminders():
    runner = Runner(agent=root_agent)
    
    message = types.Content(
        role="user",
        parts=[types.Part(text="Send email reminders for all invoices due in the next 7 days")]
    )
    
    async for event in runner.run_async(new_message=message):
        pass  # Process events
    
    print("✅ Daily reminders sent successfully")

if __name__ == "__main__":
    asyncio.run(send_daily_reminders())
```

## 🔒 Security Considerations

1. **Credential Storage**
   - Store SMTP credentials in `.env` (not in code)
   - Add `.env` to `.gitignore`
   - Never commit credentials to version control

2. **Email Validation**
   - System validates email format
   - Checks for Business Partner email existence
   - Reports errors if email missing

3. **Rate Limiting**
   - Be mindful of SMTP provider limits
   - Gmail: ~500 emails/day for free accounts
   - Consider batching for large volumes

4. **Data Privacy**
   - Emails contain invoice details (amounts, IDs)
   - Ensure compliance with data protection regulations
   - Use secure SMTP (TLS/SSL)

## 📊 Monitoring & Analytics

### Track Email Metrics

Monitor these metrics from `check_due_soon_and_email` results:

- **Emails Sent**: Successfully delivered count
- **Emails Failed**: Failed delivery count
- **Recipient Addresses**: Who received notifications
- **Days Until Due**: Urgency distribution
- **Invoice Amounts**: Total value of reminders sent

### Example Monitoring Dashboard

```python
# Get email statistics
result = check_due_soon_and_email(days_ahead=30)

print(f"Invoices Found: {result['invoices_found']}")
print(f"Emails Sent: {result['emails_sent']}")
print(f"Emails Failed: {result['emails_failed']}")
print(f"Success Rate: {result['emails_sent']/result['invoices_found']*100:.1f}%")
```

## 🎯 Best Practices

1. **Always Include Email in Business Partners**
   - Make email a required field
   - Use valid email addresses
   - Test with devstar3372@gcplab.me first

2. **Use check_due_soon_and_email for Automation**
   - Single tool does everything
   - More efficient than separate steps
   - Better error handling

3. **Set Appropriate days_ahead**
   - 7 days: Standard reminder window
   - 14 days: Extended planning window
   - 30 days: Full month forecast

4. **Monitor Email Delivery**
   - Check email_results for failures
   - Retry failed emails
   - Verify SMTP logs

5. **Test Thoroughly**
   - Use test email first (devstar3372@gcplab.me)
   - Verify HTML rendering in email client
   - Check mobile device display

## 🆘 Support

### Common Questions

**Q: Can I use a different email provider?**
A: Yes! Just update SMTP_HOST and SMTP_PORT in .env

**Q: Can I customize email templates?**
A: Yes! Edit `_get_email_template()` in `synthetic_data_agent/tools.py`

**Q: Can I send attachments (like invoice PDFs)?**
A: Not yet, but this can be added to `_send_email_smtp()` function

**Q: What if Business Partner has no email?**
A: The system will return an error and skip that invoice

**Q: Can I test without sending real emails?**
A: Yes! Use a mock SMTP server or check logs without SMTP credentials

## 📚 Related Documentation

- [Reminder Agent Guide](REMINDER_AGENT_GUIDE.md)
- [Main README](README.md)
- [Agent Architecture](synthetic_data_agent/agent.py)
- [Tools Reference](synthetic_data_agent/tools.py)

---

**Built with Google ADK** | **SMTP Email Integration** | **Professional HTML Templates**
