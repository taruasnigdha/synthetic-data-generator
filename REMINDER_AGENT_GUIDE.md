# 🔔 Reminder Agent Guide

## Overview

The **Reminder Agent** is a specialized sub-agent in the Synthetic Data Fabricator multi-agent system that manages reminders and notifications for time-sensitive SAP entities such as invoices, sales orders, and business partners.

## Architecture

```
Orchestrator Agent
    └── Reminder Agent (Sub-Agent 6)
        ├── create_reminder
        ├── list_reminders
        ├── check_due_soon
        └── dismiss_reminder
```

## Features

### 🎯 Reminder Types

| Type | Description | Use Case |
|------|-------------|----------|
| `overdue_invoice` | Alert for overdue payments | Invoices past due date with unpaid status |
| `upcoming_due_date` | Proactive reminder | Invoices due within 7 days |
| `credit_limit_warning` | Credit limit alert | Customer approaching credit limit |
| `delivery_reminder` | Delivery deadline | Upcoming delivery dates for sales orders |
| `custom` | User-defined | Any custom reminder scenario |

### ⚡ Priority Levels

- **low** — Informational, no urgency
- **medium** — Standard reminder (default)
- **high** — Important, needs attention soon
- **critical** — Urgent, immediate action required

### 🔄 Recurring Options

- **no** — One-time reminder (default)
- **daily** — Repeats every day
- **weekly** — Repeats every week
- **monthly** — Repeats every month

## Tools

### 1. create_reminder

Creates a new reminder for an invoice, sales order, or business partner.

**Parameters:**
- `reminder_type` (required): Type of reminder
- `entity_id` (required): SAP record ID (e.g., 'INV1A2B3C4D')
- `entity_type` (required): 'BusinessPartner', 'Invoice', or 'SalesOrder'
- `message` (required): Reminder message text
- `trigger_date` (optional): When to trigger (YYYY-MM-DD)
- `priority` (optional): 'low', 'medium', 'high', or 'critical'
- `recurring` (optional): 'no', 'daily', 'weekly', or 'monthly'

**Example:**
```python
create_reminder(
    reminder_type="overdue_invoice",
    entity_id="INV2E42F7A0",
    entity_type="Invoice",
    message="Invoice INV2E42F7A0 for $37,797 is overdue. Customer: BP0000000001",
    priority="high"
)
```

### 2. list_reminders

Lists all reminders with optional filtering.

**Parameters:**
- `entity_type` (optional): Filter by entity type
- `entity_id` (optional): Filter by specific entity ID
- `priority` (optional): Filter by priority level
- `status` (optional): 'active' (default), 'completed', or 'all'

**Example:**
```python
list_reminders(
    entity_type="Invoice",
    priority="high",
    status="active"
)
```

### 3. check_due_soon

Proactively checks for invoices due soon and optionally creates reminders.

**Parameters:**
- `days_ahead` (optional): How many days ahead to check (default: 7)
- `auto_create_reminders` (optional): Auto-create reminders (default: False)

**Example:**
```python
check_due_soon(
    days_ahead=7,
    auto_create_reminders=True
)
```

### 4. dismiss_reminder

Marks a reminder as completed/dismissed.

**Parameters:**
- `reminder_id` (required): The reminder ID to dismiss

**Example:**
```python
dismiss_reminder(reminder_id="REM1A2B3C4D")
```

## Usage Examples

### Example 1: Create Reminders for Overdue Invoices

```
User: "Remind me about all overdue invoices"

Agent Flow:
1. Orchestrator delegates to reminder_agent
2. Reminder agent queries for overdue invoices
3. Creates high-priority reminders for each overdue invoice
4. Reports reminder IDs created
```

**CLI:**
```bash
python run.py "Remind me about all overdue invoices"
```

### Example 2: Check What's Due Soon

```
User: "What invoices are due in the next 7 days?"

Agent Flow:
1. Orchestrator delegates to reminder_agent
2. Reminder agent uses check_due_soon(days_ahead=7)
3. Reports count and details of invoices due soon
4. Asks if reminders should be created
```

### Example 3: Set Up Proactive Reminders

```
User: "Set up reminders for all invoices due in the next 14 days"

Agent Flow:
1. Orchestrator delegates to reminder_agent
2. Reminder agent uses check_due_soon(days_ahead=14, auto_create_reminders=True)
3. Creates reminders for all found invoices
4. Reports how many reminders were created
```

### Example 4: View All Active Reminders

```
User: "Show me all my reminders"

Agent Flow:
1. Orchestrator delegates to reminder_agent
2. Reminder agent uses list_reminders(status="active")
3. Presents organized list of active reminders
```

### Example 5: Create Custom Reminder

```
User: "Remind me to follow up with customer BP0000000001 in 3 days"

Agent Flow:
1. Orchestrator delegates to reminder_agent
2. Reminder agent calculates trigger_date (3 days from now)
3. Creates custom reminder with medium priority
4. Reports reminder ID
```

## Integration with Multi-Agent System

The Reminder Agent works seamlessly with other agents:

### With Verification Agent
```
User: "Create invoices and set up reminders for them"

Flow:
1. Data Generation → creates invoice data
2. Transaction Agent → creates invoices
3. Verification Agent → confirms creation
4. Reminder Agent → creates reminders for due dates
```

### With Transaction Agent
```
User: "Generate overdue invoices and remind me about them"

Flow:
1. Transaction Agent → creates overdue invoices
2. Reminder Agent → automatically creates high-priority reminders
```

## Best Practices

### 1. Always Include Key Details in Messages
```python
# Good
message="Invoice INV2E42F7A0 for $37,797 is overdue. Customer: BP0000000001"

# Bad
message="Invoice overdue"
```

### 2. Use Appropriate Priority Levels
- Overdue invoices → `high` or `critical`
- Due within 7 days → `medium`
- Due within 30 days → `low`

### 3. Leverage check_due_soon for Proactive Management
```python
# Check daily for invoices due in next 7 days
check_due_soon(days_ahead=7, auto_create_reminders=True)
```

### 4. Clean Up Completed Reminders
```python
# After acting on a reminder, dismiss it
dismiss_reminder(reminder_id="REM1A2B3C4D")
```

## API Endpoints (Mock Server)

The reminder tools interact with these endpoints:

```
POST   /api/reminders              # Create reminder
GET    /api/reminders              # List reminders (with query params)
PATCH  /api/reminders/{id}         # Update reminder status
```

## Reminder Data Structure

```json
{
  "ReminderID": "REM1A2B3C4D",
  "ReminderType": "overdue_invoice",
  "EntityID": "INV2E42F7A0",
  "EntityType": "Invoice",
  "Message": "Invoice INV2E42F7A0 for $37,797 is overdue",
  "TriggerDate": "2024-12-02",
  "Priority": "high",
  "Recurring": "no",
  "Status": "active",
  "CreatedAt": "2024-12-02T10:30:00Z"
}
```

## Advanced Scenarios

### Scenario 1: Credit Limit Monitoring
```
User: "Alert me when customers exceed 80% of their credit limit"

Implementation:
1. Query all business partners
2. Check credit usage vs limit
3. Create credit_limit_warning reminders for those over 80%
```

### Scenario 2: Delivery Deadline Tracking
```
User: "Remind me 3 days before any delivery is due"

Implementation:
1. Query all sales orders
2. Check RequestedDeliveryDate
3. Create delivery_reminder with trigger_date = delivery_date - 3 days
```

### Scenario 3: Recurring Payment Reminders
```
User: "Send me weekly reminders about all unpaid invoices"

Implementation:
1. Create reminder with recurring="weekly"
2. System automatically triggers reminder every week
3. Updates list of unpaid invoices dynamically
```

## Troubleshooting

### Issue: Reminders Not Showing
**Solution:** Check reminder status - may be filtered out if looking only at 'active'
```python
list_reminders(status="all")
```

### Issue: check_due_soon Returns No Results
**Solution:** Adjust days_ahead parameter or check if invoices exist
```python
check_due_soon(days_ahead=30)  # Extend search window
```

### Issue: Cannot Dismiss Reminder
**Solution:** Verify reminder ID is correct
```python
# List all reminders first to get correct ID
reminders = list_reminders(status="all")
```

## Performance Considerations

- **Bulk Operations**: When creating many reminders, use `check_due_soon` with `auto_create_reminders=True`
- **Filtering**: Use specific filters in `list_reminders` to reduce response size
- **Recurring Reminders**: Use sparingly to avoid notification overload

## Future Enhancements

Potential additions to the Reminder Agent:

- 📧 Email/SMS integration for reminder delivery
- 📊 Analytics dashboard for reminder statistics
- 🤖 AI-powered smart scheduling based on patterns
- 🔗 Integration with calendar systems
- 📱 Mobile app notifications
- ⏰ Snooze functionality for reminders
- 🎯 Custom reminder rules engine

## Integration Example: Complete Workflow

```python
# Complete example: Create test data with automatic reminders

# 1. Generate overdue invoices
python run.py "Generate 5 overdue invoices for a US customer"

# 2. Set up reminders
python run.py "Create high-priority reminders for all overdue invoices"

# 3. Check what's coming up
python run.py "What invoices are due in the next 14 days?"

# 4. Set up proactive monitoring
python run.py "Create reminders for all invoices due in the next month"

# 5. View all reminders
python run.py "Show me all my active reminders"

# 6. Dismiss completed ones
python run.py "Dismiss reminder REM1A2B3C4D"
```

## Conclusion

The Reminder Agent provides a powerful, flexible system for managing time-sensitive SAP entities. By integrating seamlessly with the multi-agent architecture, it ensures that critical deadlines and events are never missed.

For more information, see:
- [Main README](README.md)
- [Agent Architecture Documentation](synthetic_data_agent/agent.py)
- [Tools Documentation](synthetic_data_agent/tools.py)

---

**Built with Google ADK** | **Part of Synthetic Data Fabricator Multi-Agent System**
