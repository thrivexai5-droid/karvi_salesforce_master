# Automatic Notification System Setup Guide

## Overview
Your Django project now has an automatic notification system that sends daily reminders and escalations for:
- Purchase Orders due today (to Sales/Project Managers)
- Invoice payments due today (to Sales)
- Overdue Purchase Orders (escalated to Admins)
- Overdue Invoice payments (escalated to Admins)

## Setup Instructions

### 1. Configure Email Settings

Update your `.env` file with your email credentials:

```env
# Email Configuration for Notifications
EMAIL_HOST_USER=your_company_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

# Secret key for automation URL (change this to something secure)
CRON_SECRET_KEY=YourSecureKey2026
```

**For Gmail:**
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an "App Password" in Google Account Settings > Security
3. Use the app password (not your regular password) in `EMAIL_HOST_PASSWORD`

### 2. Test the System

#### Manual Test:
1. Start your Django server: `python manage.py runserver`
2. Create test data: `python test_notifications.py create`
3. Test notifications: `python test_notifications.py test`
4. Or visit directly: `http://127.0.0.1:8000/automation/send-emails/?secret=YourSecureKey2026`

#### Expected Response:
```json
{
  "status": "success",
  "date": "2026-01-02",
  "actions": [
    "Reminder sent to Sales (sales@test.com): PO TEST-PO-TODAY",
    "Overdue PO escalation sent to 1 Admins"
  ],
  "summary": {
    "due_today_pos": 1,
    "due_today_invoices": 0,
    "overdue_pos": 1,
    "overdue_invoices": 0
  }
}
```

### 3. Set Up Automatic Daily Execution

#### Option A: Cron-Job.org (Free Online Service)
1. Go to [Cron-Job.org](https://cron-job.org)
2. Create a free account
3. Add a new cron job:
   - **URL:** `https://your-website.com/automation/send-emails/?secret=YourSecureKey2026`
   - **Schedule:** Every day at 09:00 AM
   - **Timezone:** Your local timezone

#### Option B: Server Cron (If you have server access)
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 9 AM)
0 9 * * * curl -s "https://your-website.com/automation/send-emails/?secret=YourSecureKey2026"
```

#### Option C: GitHub Actions (If using GitHub)
Create `.github/workflows/daily-notifications.yml`:
```yaml
name: Daily Notifications
on:
  schedule:
    - cron: '0 9 * * *'  # 9 AM UTC daily
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Send notifications
        run: |
          curl -s "https://your-website.com/automation/send-emails/?secret=${{ secrets.CRON_SECRET_KEY }}"
```

### 4. Security Notes

- **Change the secret key** in your `.env` file to something unique and secure
- **Never share** your secret key publicly
- The URL will return `403 Unauthorized` if the wrong secret is used
- Only users with admin/manager roles can view notifications in the dashboard

### 5. Notification Logic

#### Daily Reminders (9 AM):
- **Sales/Project Managers** get reminders for Purchase Orders due today
- **Sales** get reminders for Invoice payments due today

#### Escalations (9 AM):
- **Admins** get escalation reports for:
  - Overdue Purchase Orders (past delivery date)
  - Overdue Invoice payments (past payment due date)

### 6. Customization

You can modify the notification logic in `dashboard/views.py` in the `run_daily_notifications` function:

- Change email templates
- Modify recipient logic
- Add more notification types
- Adjust timing criteria

### 7. Monitoring

- Check the JSON response for successful execution
- Monitor your email inbox for test notifications
- Use the Django admin to verify user roles and email addresses
- Check server logs for any email sending errors

### 8. Troubleshooting

**No emails received?**
- Verify email settings in `.env`
- Check spam/junk folders
- Ensure users have valid email addresses
- Test with a simple email first

**403 Unauthorized?**
- Check the secret key in URL matches `.env`
- Ensure `.env` file is loaded properly

**No notifications sent?**
- Verify there are Purchase Orders/Invoices due today or overdue
- Check that users have the correct roles (admin, sales, project_manager)
- Ensure email addresses are set for users

## Example Notification Emails

### Reminder Email (to Sales/Manager):
```
Subject: 📅 Reminder: PO 'PO-12345' is due Today!

Hello John Doe,

This is a reminder that Purchase Order 'PO-12345' for ABC Company is due today (2026-01-02).

Order Details:
- PO Number: PO-12345
- Customer: ABC Company
- Order Value: ₹50,000.00
- Delivery Date: 2026-01-02

Please update the status and ensure timely delivery.

Best regards,
Project Management System
```

### Escalation Email (to Admin):
```
Subject: 🚨 ESCALATION: 3 Purchase Orders Overdue

⚠️ URGENT: The following 3 Purchase Orders are OVERDUE:

- PO PO-12345 | Customer: ABC Company | Due: 2025-12-28 | Overdue: 5 days | Value: ₹50,000.00
- PO PO-12346 | Customer: XYZ Corp | Due: 2025-12-30 | Overdue: 3 days | Value: ₹75,000.00

Total Overdue Value: ₹125,000.00

Please take immediate action to resolve these delays.

Best regards,
Project Management System
```

Your notification system is now ready! 🎉