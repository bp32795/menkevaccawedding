# Menke & Vacca Wedding Website

A beautiful, modern wedding website built with Flask, featuring RSVP functionality and a dynamic registry connected to Google Sheets.

## Features

- 🏠 **Home Page**: Elegant landing page with wedding information
- 📝 **RSVP System**: Guest response system (to be configured)
- 🎁 **Dynamic Registry**: Connected to Google Sheets with real-time updates
- 💌 **Email Notifications**: Automatic notifications when items are purchased
- 📱 **Responsive Design**: Beautiful on all devices
- ☁️ **Azure Ready**: Configured for easy Azure deployment
- 🔒 **Secure**: Built with security best practices

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Database**: Google Sheets API
- **Email**: Flask-Mail with Gmail SMTP
- **Deployment**: Azure App Service
- **Testing**: Python unittest with comprehensive test coverage

## Quick Start

### Prerequisites

- Python 3.11+
- Git
- Google Cloud Project with Sheets API enabled (for registry)
- Gmail account for email notifications (optional - auto SMTP server included)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd menkevaccawedding
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   The default `.env` file works out of the box! The app includes:
   - ✅ **Built-in SMTP Server** for development email testing
   - ✅ **Automatic email logging** to `email_logs/` directory
   - ✅ **No Gmail setup required** for development

5. **Run the application**
   ```bash
   python app.py
   ```

   You'll see:
   ```
   📧 Using local SMTP server for development
   📧 Local SMTP server started for email testing
   📧 Dev SMTP Server started on localhost:1025
   📁 Email logs will be saved to: email_logs/
   * Running on http://127.0.0.1:5000
   ```

   Visit `http://localhost:5000` in your browser.

## Private RSVP Overview

The private `/rsvp/admin` page is omitted from public navigation and requires
HTTP Basic authentication. Use username `admin` and the password configured in
`RSVP_ADMIN_PASSWORD`. Set this environment variable in your local `.env` and in
Azure App Service application settings, then restart the app. Never commit the
password to source control. The page is disabled when the password is unset.
Use HTTPS in production to protect the credentials in transit.

The overview shows only attendance (Yes/No), number attending, welcome-party
attendance (Yes/No), and party names, sorted by names. Declined RSVPs show zero
attendees and No for the welcome party. Emails, notes, and dietary information
are not fetched or included in the page. Responses are marked private/no-store
and noindex/nofollow. Browser-managed credentials may remain active until you
close the browser or private browsing session.

### Household tracking and manual matching

Import the invitation CSV into the response database using:

```powershell
python import_guest_list.py export.csv --azure-app menkevaccawedding --resource-group rg-menkevaccawedding
```

Omit the Azure arguments to use the local environment's database settings. The importer
validates the CSV before writing and stores only primary, partner, and child names.
It never uploads the CSV, emails, phone numbers, or addresses. Reimporting unchanged
households is idempotent. Renamed or removed households need separate database cleanup;
the importer does not delete existing households or saved matches.

The overview lists every imported household as Responded, Not responded, or Needs review.
Declines count as responses. Automatic matching requires an unambiguous full name;
duplicate names, responses spanning households, and similar spellings are flagged for
review instead of being silently accepted. First-name-only guests are not auto-matched.
Unmatched RSVP responses remain visible for manual assignment.

Expand **Match manually** beside a household to select one or more RSVP responses, then
choose **Save match**. A response covering multiple households can be selected for each.
Saving an empty selection explicitly marks that household as not responded. **Use automatic
match** removes the override. Manual assignments are stored in Cosmos DB and survive
restarts and deployments. Manual assignments take priority over automatic matching;
RSVPs explicitly assigned elsewhere are not auto-assigned again. Matching controls
require the same password and a session-specific CSRF token. They never change guests'
submitted RSVP answers. Household totals count households, not people; use the submitted
RSVP table for attendance counts without double-counting shared responses.

Both tables have independent name, attendance, and welcome-party filters. The household
table also filters by RSVP status. Filters combine, and name search ignores case,
accents, and punctuation. Household searches include invited and matched names, not
every name in the manual-match dropdown. Attendance filters require an actual matched
RSVP; unanswered households are not treated as declines. When both answer filters are
selected, the same RSVP must satisfy both. Entire households stay together, including
manual matching controls. Visible-result counts and empty-result messages update as
you filter; summary totals and saved matches are unchanged. **Clear filters** restores
all rows. Filtering runs in the browser without sending search terms to the server
and requires JavaScript. Filters reset when the page reloads or a match is saved.

## Development Features

### Built-in Email Server 🎯

The app automatically starts a local SMTP server for development:

- **Port**: localhost:1025
- **Email Logs**: Saved to `email_logs/` directory
- **No Configuration**: Works immediately without Gmail setup
- **Real Testing**: Actually sends emails to the local server

### View Development Emails

```bash
# View all emails sent during development
python view_emails.py

# Clear email logs
python view_emails.py clear
```

### Test Email Flow

1. **Start the app** - SMTP server starts automatically
2. **Visit registry page** - http://localhost:5000/registry
3. **Purchase an item** - Click "I Bought This" and fill the form
4. **Check email logs** - Run `python view_emails.py`

## Email Setup (Optional)

Email notifications are sent when someone purchases a registry item. This is optional - the website works perfectly without email configuration.

### Quick Email Check

Run the email configuration checker:
```bash
python check_email.py
```

### Setting Up Gmail for Notifications

1. **Enable 2-Factor Authentication** on your Google account
2. **Go to Google Account Settings** > Security > App passwords
3. **Generate an app password** for "Mail" 
4. **Edit `.env` file** and add:
   ```
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-16-character-app-password
   MAIL_DEFAULT_SENDER=your-email@gmail.com
   ```
5. **Restart the application**

### Email Configuration Example
```
MAIL_USERNAME=bp32795@gmail.com
MAIL_PASSWORD=abcd efgh ijkl mnop
MAIL_DEFAULT_SENDER=bp32795@gmail.com
```

## Google Sheets Setup

The registry connects to a Google Sheet with the following columns:

| Column | Description |
|--------|-------------|
| URL | Link to the item |
| Priority | Priority level (higher numbers first) |
| Image URL | Link to product image |
| Price | Item price |
| Bought? | Purchase status (Yes/No) |
| Item Title (if not entered, website will try to make one) | Name of the item |
| Bought by | Name of purchaser |

### Setting up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Google Sheets API
4. Create a service account
5. Download the service account key (JSON)
6. Share your Google Sheet with the service account email
7. Update the credentials in `app.py`

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_wedding_website.py::HomePageTestCase -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

### Test Coverage

The test suite includes:
- ✅ Home page functionality
- ✅ RSVP page structure
- ✅ Registry page with Google Sheets integration
- ✅ Purchase workflow end-to-end
- ✅ Email notification system
- ✅ Error handling and security
- ✅ Utility functions
- ✅ Integration tests

## Azure Deployment

### Option 1: GitHub Actions (Recommended)

1. **Fork this repository**
2. **Create Azure Web App**
   ```bash
   az webapp create --resource-group myResourceGroup --plan myPlan --name menkevaccawedding --runtime "PYTHON|3.11"
   ```
3. **Configure custom domain**
   ```bash
   az webapp config hostname add --webapp-name menkevaccawedding --resource-group myResourceGroup --hostname menkevaccawedding.com
   ```
4. **Set environment variables in Azure**
   ```bash
   az webapp config appsettings set --name menkevaccawedding --resource-group myResourceGroup --settings SECRET_KEY="your-secret" MAIL_USERNAME="your-email"
   ```
5. **Get publish profile and add to GitHub secrets**
6. **Push to main branch** - automatic deployment via GitHub Actions

### Option 2: Azure CLI Direct Deploy

```bash
# Login to Azure
az login

# Deploy directly
az webapp up --sku B1 --name menkevaccawedding --location "East US"
```

### Option 3: VS Code Azure Extension

1. Install Azure App Service extension
2. Right-click project folder
3. Select "Deploy to Web App"
4. Follow prompts

## Custom Domain Setup

1. **Purchase domain** (menkevaccawedding.com)
2. **Configure DNS**:
   ```
   Type: CNAME
   Name: @
   Value: menkevaccawedding.azurewebsites.net
   ```
3. **Add custom domain in Azure**:
   ```bash
   az webapp config hostname add --webapp-name menkevaccawedding --resource-group myResourceGroup --hostname menkevaccawedding.com
   ```
4. **Enable SSL**:
   ```bash
   az webapp config ssl bind --certificate-thumbprint {thumbprint} --ssl-type SNI --name menkevaccawedding --resource-group myResourceGroup
   ```

## Project Structure

```
menkevaccawedding/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── startup.py             # Azure startup file
├── web.config             # Azure configuration
├── .env.example           # Environment variables template
├── templates/             # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── home.html         # Home page
│   ├── rsvp.html         # RSVP page
│   ├── registry.html     # Registry page
│   ├── 404.html          # 404 error page
│   └── 500.html          # 500 error page
├── tests/                # Test suite
│   └── test_wedding_website.py
├── .github/              # GitHub workflows
│   └── workflows/
│       └── azure-deploy.yml
└── README.md             # This file
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `MAIL_USERNAME` | Gmail username | Yes |
| `MAIL_PASSWORD` | Gmail app password | Yes |
| `MAIL_DEFAULT_SENDER` | Default sender email | Yes |
| `FLASK_ENV` | Environment (development/production) | No |

### Gmail App Password Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account Settings > Security > App passwords
3. Generate an app password for "Mail"
4. Use this password in `MAIL_PASSWORD` environment variable

## Registry Features

### Purchase Workflow

1. **View Items**: Registry displays items from Google Sheets
2. **Sort/Filter**: Sort by priority, price, or name
3. **Purchase**: Click "I Bought This" to open purchase dialog
4. **Confirmation**: Enter name, purchase date, optional delivery date
5. **Updates**: Google Sheet updated, email sent to couple
6. **Visual Feedback**: Item appears as "Already Purchased"

### Item Display

- **Priority Badges**: High-priority items highlighted
- **Images**: Product images from URLs
- **Pricing**: Clear price display with sorting
- **Status**: Visual indication of purchased items
- **Links**: Direct links to product pages

## Security Features

- ✅ CSRF protection (Flask-WTF)
- ✅ Secure headers
- ✅ Input validation
- ✅ SQL injection protection (using Google Sheets API)
- ✅ XSS protection (template escaping)
- ✅ Secure secret key management
- ✅ Environment variable configuration

## Troubleshooting

### Common Issues

**Google Sheets not loading:**
- Check service account permissions
- Verify sheet is shared with service account email
- Check Google Sheets API is enabled

**Email not sending:**
- Verify Gmail app password is correct
- Check 2FA is enabled on Google account
- Ensure less secure app access is disabled (use app password)

**Azure deployment fails:**
- Check Python version (3.11 required)
- Verify all environment variables are set
- Check requirements.txt is complete

### Getting Help

1. Check the test suite: `python -m pytest tests/ -v`
2. Enable debug mode: Set `FLASK_ENV=development`
3. Check logs: `tail -f app.log`
4. Verify environment variables: Check `.env` file

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Write tests for new functionality
4. Ensure all tests pass: `python -m pytest tests/`
5. Submit a pull request

## License

This project is private and intended for the Menke & Vacca wedding.

## Support

For support or questions about this wedding website, contact:
- Email: bp32795@gmail.com

---

*Made with ❤️ for Menke & Vacca's special day*
