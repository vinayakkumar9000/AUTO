# 🤖 Auto Registration Workflow

Automated registration system that combines temporary email generation, identity creation, browser automation, and AI-powered OTP extraction.

## ✨ Features

- **Temporary Email Generation**: Automatically creates disposable email addresses using mail.tm
- **Identity Generation**: Generates realistic Indian identities with names, locations, and demographics
- **Smart Field Detection**: Intelligently finds email and OTP input fields using multiple fallback strategies
- **AI-Powered OTP Extraction**: Uses FreeModel AI API to extract verification codes from emails
- **Headless Browser Automation**: Playwright-based automation for seamless registration
- **User Confirmations**: Asks for confirmation at critical steps for control and transparency
- **Error Handling**: Robust error handling with detailed feedback

## 📋 Prerequisites

- Python 3.8 or higher
- FreeModel API key (get from [freemodel.dev](https://freemodel.dev))
- Internet connection

## 🚀 Installation

### 1. Navigate to the project directory

```bash
cd "D:\AUTO\auto registration"
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers

```bash
playwright install chromium
```

## 🔧 Configuration

On first run, the script will prompt you for your FreeModel API key. You can choose to save it for future use in `config.json`.

### Manual Configuration (Optional)

Create a `config.json` file in the same directory:

```json
{
  "freemodel_api_key": "your-api-key-here"
}
```

## 📖 Usage

### Basic Usage

Run the script and follow the interactive prompts:

```bash
python auto_registration.py
```

### Workflow Steps

1. **Enter URL**: Provide the registration page URL
2. **Identity Generation**: Review the generated identity (name, age, location)
3. **Email Generation**: Temporary email is created automatically
4. **Browser Automation**: Script opens the site and enters the email
5. **OTP Waiting**: Waits up to 20 seconds for verification email
6. **AI Extraction**: AI extracts the OTP from the email
7. **OTP Submission**: Enters and submits the OTP automatically

### Example Session

```
🤖 Auto Registration Workflow
Automated registration with temp email and AI-powered OTP extraction

Enter the registration URL: https://example.com/register

Stage 1: Generating Identity
┌─ Generated Identity ─────────────────────────┐
│ Name: Rahul Kumar Sharma                     │
│ Gender: Male                                  │
│ Age: 28                                       │
│ Location: New Delhi, Delhi                   │
└───────────────────────────────────────────────┘
Proceed with this identity? [Y/n]: y

Stage 2: Generating Temporary Email
✓ Email generated: abc123@mail.tm

Stage 3: Opening Website
✓ Navigating to: https://example.com/register
✓ Page loaded

Stage 4: Entering Email
✓ Email entered: abc123@mail.tm
✓ Send Code button clicked

Stage 5: Waiting for OTP Email (max 20s)
✓ Email received

Stage 6: Extracting OTP with AI
✓ OTP extracted: 482731

Stage 7: Entering OTP
✓ OTP entered: 482731
✓ OTP submitted

✓ Workflow Completed Successfully!
```

## 🎯 How It Works

### 1. Identity Generation
Uses the `identity_generator.py` module to create realistic Indian identities with:
- First, middle, and last names
- Gender and age
- State and city
- Parent names
- Username suggestions

### 2. Temporary Email
Integrates with `tempmail.py` to:
- Create disposable email addresses via mail.tm API
- Monitor inbox for incoming messages
- Retrieve email content automatically

### 3. Browser Automation
Uses Playwright to:
- Navigate to registration pages in headless mode
- Detect email input fields using multiple strategies
- Find and click "Send Code" buttons
- Locate OTP input fields
- Submit verification codes

### 4. AI OTP Extraction
Leverages FreeModel AI API (gpt-5.4-mini) to:
- Parse email content intelligently
- Extract only the verification code digits
- Handle various email formats and layouts
- Fallback to manual entry if extraction fails

## 🛡️ Error Handling

The script includes comprehensive error handling:

- **Network Errors**: Retries with exponential backoff
- **Element Not Found**: Multiple fallback strategies for field detection
- **Email Timeout**: 20-second wait with clear feedback
- **AI Failure**: Manual OTP entry fallback
- **User Interruption**: Graceful exit on Ctrl+C

## 🔒 Security & Privacy

- **Temporary Emails**: All emails are disposable and auto-deleted
- **No Data Storage**: Identity data is generated on-the-fly
- **API Key Protection**: Stored locally in config.json (not committed to git)
- **Headless Mode**: Browser runs in background without UI

## 📝 Configuration Options

### API Key Storage
- Stored in `config.json` in the script directory
- Can be entered each time if you prefer not to save it

### Timeout Settings
- Email wait: 20 seconds (configurable in code)
- Page load: Uses Playwright's networkidle state
- AI extraction: 30 seconds timeout

## 🐛 Troubleshooting

### "Email field not found"
- The site may use non-standard input fields
- Check if the site requires JavaScript to load forms
- Try running in non-headless mode for debugging

### "No email received within 20 seconds"
- Some sites have delays in sending emails
- Check if the email went to spam (not applicable for temp emails)
- Verify the site actually sends verification emails

### "AI failed to extract OTP"
- The email format may be unusual
- Script will prompt for manual entry
- Check the displayed email content for the code

### "API key invalid"
- Verify your FreeModel API key is correct
- Check if your API quota is exhausted
- Get a new key from freemodel.dev

## 🔄 Dependencies

- **requests**: HTTP client for API calls
- **rich**: Beautiful terminal output and prompts
- **playwright**: Browser automation framework
- **tempmail module**: Temporary email generation
- **identity_generator module**: Identity creation

## 📂 Project Structure

```
auto registration/
├── auto_registration.py    # Main automation script
├── requirements.txt         # Python dependencies
├── config.json             # Configuration (created on first run)
└── README.md               # This file

Parent directories:
├── tempmail/               # Temporary email module
│   └── tempmail.py
├── identity/               # Identity generator module
│   └── identity_generator.py
└── playwright/             # Playwright utilities
    └── freemodel_verify.py
```

## 🤝 Contributing

This is a utility script for automation testing. Feel free to:
- Report bugs or issues
- Suggest improvements
- Add support for more providers
- Enhance field detection strategies

## ⚠️ Disclaimer

This tool is intended for:
- Testing and development purposes
- Automating legitimate registrations
- Educational demonstrations

**Do not use for:**
- Spam or abuse
- Bypassing security measures
- Violating terms of service
- Illegal activities

## 📄 License

This project uses components from:
- tempmail (by zebbern)
- Custom identity generator
- Playwright automation utilities

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section
2. Review error messages carefully
3. Verify all dependencies are installed
4. Ensure you have a valid API key

## 🎓 Examples

### Example 1: Basic Registration
```bash
python auto_registration.py
# Enter URL when prompted
# Follow interactive steps
```

### Example 2: Multiple Registrations
Run the script multiple times - each run generates a new identity and email.

### Example 3: Custom Identity
Modify `identity_generator.py` to customize:
- Age ranges
- Regions
- Gender preferences

## 🔮 Future Enhancements

Potential improvements:
- Support for multiple email providers
- Configurable timeout values
- Batch registration mode
- Custom identity templates
- Screenshot capture on errors
- Detailed logging to file

---

**Version**: 1.0.0  
**Last Updated**: June 2026  
**Author**: Bob Shell
