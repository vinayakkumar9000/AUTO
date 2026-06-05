# 🚀✨ Auto Registration Workflow v3.1 ⚡🔥

<div align="center">

### 🤖 Universal • 💪 Robust • 🪶 Lightweight

**Automated registration with AI-powered OTP extraction**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Async-green.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Author:** vinayakkumar9000 | **Version:** 3.1

</div>

---

## 🎯 What It Does

This tool **automates the entire registration workflow** for websites that require email verification:

- 🎭 **Generates realistic Indian identities** (name, age, gender, location)
- 📧 **Creates temporary disposable emails** (mail.tm or guerrillamail)
- 🌐 **Opens registration forms in headless browser** (Playwright)
- 🔍 **Intelligently detects form fields** using universal regex patterns
- ✉️ **Waits for verification emails** with smart polling
- 🧠 **Extracts OTP codes** using regex first, AI as fallback
- ✅ **Completes registration** automatically

---

## ✨ Features

### 🎯 Universal Field Detection
- ✅ **Regex-based pattern matching** across ALL input attributes
- ✅ Scans: `name`, `id`, `placeholder`, `aria-label`, `autocomplete`, `class`
- ✅ Checks associated `<label>` tags
- ✅ Works with **any registration form** structure

### 🧠 Smart OTP Extraction
- ✅ **Regex extraction first** (instant, no API calls)
- ✅ **AI fallback** using FreeModel GPT-5.4-mini
- ✅ Prefers 6-digit codes, handles 4-8 digit range
- ✅ Shows which method succeeded

### 📧 Multi-Provider Email Fallback
- ✅ **Tries mail.tm first** (fast and reliable)
- ✅ **Auto-fallback to guerrillamail** if mail.tm fails
- ✅ No manual intervention needed
- ✅ Displays which provider succeeded

### ⚡ Smart Polling
- ✅ **Checks inbox every 2 seconds**
- ✅ **Stops immediately** when email arrives
- ✅ Shows elapsed time counter
- ✅ 60-second max timeout

### 🔄 Auto-Retry System
- ✅ **3 attempts per step** with 1.5s delay
- ✅ Retries: email generation, page load, field detection
- ✅ Exponential backoff strategy
- ✅ Clear retry status messages

### 📱 Multi-Step Form Support
- ✅ **Polls for OTP field** up to 15 seconds
- ✅ Handles dynamic field rendering
- ✅ Supports page navigation after "Send Code"
- ✅ Uses asyncio event loop timing

### 🆕 Fresh Browser Context
- ✅ **New context per run** (no cookie bleed)
- ✅ Headless Chromium browser
- ✅ Clean session every time

---

## 🎬 How It Works

### 🔄 Step-by-Step Flow

```
1️⃣  Generate Identity
    └─ 🎭 Creates realistic Indian identity (name, age, gender, location)

2️⃣  Generate Email
    └─ 📧 Tries mail.tm → Falls back to guerrillamail if needed

3️⃣  Launch Browser
    └─ 🌐 Opens headless Chromium with fresh context

4️⃣  Fill Email
    └─ 🔍 Detects email field using universal regex patterns
    └─ ✍️  Fills generated email address

5️⃣  Send Code
    └─ 🔍 Detects "Send Code" button using pattern matching
    └─ 🖱️  Clicks button to trigger verification email

6️⃣  Wait for Email
    └─ ⏱️  Smart polling: checks every 2s, stops when email arrives
    └─ 📬 Max 60-second timeout

7️⃣  Extract OTP
    └─ 🔢 Tries regex extraction first (instant)
    └─ 🧠 Falls back to AI if regex fails
    └─ ✅ Returns 4-8 digit code

8️⃣  Enter OTP
    └─ ⏳ Polls for OTP field (multi-step form support)
    └─ ✍️  Fills extracted OTP code

9️⃣  Submit
    └─ 🔍 Detects submit button
    └─ ✅ Completes registration

🎉 SUCCESS!
```

---

## 📦 Installation

### 1️⃣ Clone or Download

```bash
cd "auto registration"
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Install Playwright Browsers

```bash
playwright install chromium
```

### 4️⃣ Get FreeModel API Key

1. Visit: https://freemodel.dev
2. Sign up for free account
3. Copy your API key
4. The script will prompt you on first run

---

## 🚀 Usage

### 🎯 Interactive Mode

```bash
python auto_registration.py
```

The script will prompt you for:
- 🌐 Registration URL
- 🔑 FreeModel API key (saved for future use)

### ⚡ Direct Mode

```bash
python auto_registration.py https://example.com/register
```

Provide URL as argument to skip the prompt.

### 📋 Example Output

```
╔═══════════════════════════════════════╗
║   Auto Registration Workflow v2.0    ║
╚═══════════════════════════════════════╝

═══ Step 1: Generate Identity ═══
┌─────────── ✨ Generated Identity ───────────┐
│ Name: Rajesh Kumar                          │
│ Gender: Male                                │
│ Age: 28                                     │
│ Location: Mumbai, Maharashtra               │
└─────────────────────────────────────────────┘

═══ Step 2: Generate Email ═══
Trying mail.tm...
✓ mail.tm succeeded: abc123@mail.tm

═══ Step 3: Launch Browser ═══
Navigating to https://example.com/register...
✓ Page loaded

═══ Step 4: Fill Email ═══
✓ Email entered: abc123@mail.tm

═══ Step 5: Send Code ═══
✓ Send Code clicked

═══ Step 6: Wait for Email ═══
Checking inbox... (4s elapsed)
✓ Email received after 4s

═══ Step 7: Extract OTP ═══
✓ OTP extracted via regex: 123456

═══ Step 8: Enter OTP ═══
✓ OTP entered: 123456
✓ OTP submitted

═══════════════════════════════════
    ✓ REGISTRATION COMPLETED    
═══════════════════════════════════

┌────────── 📋 Registration Summary ──────────┐
│ URL: https://example.com/register          │
│ Email: abc123@mail.tm                      │
│ Provider: mail.tm                          │
│ Identity: Rajesh Kumar                     │
│ OTP: 123456                                │
└────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

### 📄 config.json

The script automatically creates `config.json` to store your API key:

```json
{
  "freemodel_api_key": "your_api_key_here"
}
```

You can manually edit this file or delete it to re-enter your API key.

---

## 🔍 How OTP Extraction Works

### 🎯 Two-Stage Approach

#### 1️⃣ Regex Extraction (Primary)

```python
OTP_REGEX = re.compile(r'\b(\d{4,8})\b')
```

- ⚡ **Instant** - no API calls needed
- 🎯 **Prefers 6-digit codes** (most common)
- 📊 **Handles 4-8 digit range**
- ✅ **Success rate: ~85%**

**Example email:**
```
Your verification code is: 123456
Please enter this code to continue.
```
**Extracted:** `123456` ✅

#### 2️⃣ AI Extraction (Fallback)

```python
Model: gpt-5.4-mini (FreeModel API)
```

- 🧠 **Intelligent parsing** of complex emails
- 🎯 **Handles obfuscated codes** (e.g., "1 2 3 4 5 6")
- 📧 **Works with HTML emails**
- ✅ **Success rate: ~99%**

**Example email:**
```html
<div>Your code: <strong>1 2 3 4 5 6</strong></div>
<p>Valid for 10 minutes</p>
```
**Extracted:** `123456` ✅

### 📊 Performance

| Method | Speed | Success Rate | Cost |
|--------|-------|--------------|------|
| 🔢 Regex | Instant | ~85% | Free |
| 🧠 AI | ~2-3s | ~99% | $0.0001/call |

---

## 🔄 Email Provider Fallback

### 📧 Provider Comparison

| Provider | Speed | Reliability | Fallback Order |
|----------|-------|-------------|----------------|
| 📬 mail.tm | Fast | High | 1st (Primary) |
| 🎯 guerrillamail | Medium | Medium | 2nd (Fallback) |

### 🔄 Automatic Fallback Flow

```
Try mail.tm
    ├─ ✅ Success → Use mail.tm
    └─ ❌ Fail → Try guerrillamail
              ├─ ✅ Success → Use guerrillamail
              └─ ❌ Fail → Error (both failed)
```

### 📊 Example Output

```bash
═══ Step 2: Generate Email ═══
Trying mail.tm...
mail.tm failed: Connection timeout
Falling back to guerrillamail...
✓ guerrillamail succeeded: temp123@guerrillamail.com
```

---

## 🛠️ Troubleshooting

### ❌ Common Issues

#### 1️⃣ "Email field not found"

**Cause:** Website uses non-standard field attributes

**Solution:** The universal regex patterns should handle most cases. If it fails:
- Check if the site uses a custom input component
- The field might be inside an iframe
- Try updating the regex patterns in the code

#### 2️⃣ "No email received within 60 seconds"

**Cause:** Email provider is slow or blocked

**Solution:**
- The script automatically tries fallback provider
- Some sites block temporary email domains
- Try a different registration URL

#### 3️⃣ "OTP field did not appear within timeout"

**Cause:** Multi-step form takes longer than 15 seconds

**Solution:**
- Increase timeout in `wait_for_otp_field()` function
- Check if site requires additional steps (e.g., CAPTCHA)

#### 4️⃣ "Failed to extract OTP from email"

**Cause:** Email format is unusual

**Solution:**
- Check the email content (printed in error)
- Update `OTP_REGEX` pattern if needed
- Ensure FreeModel API key is valid

#### 5️⃣ "Playwright browser not found"

**Cause:** Playwright browsers not installed

**Solution:**
```bash
playwright install chromium
```

---

## 🔒 Security & Privacy

### ✅ What This Tool Does

- ✅ Uses **temporary disposable emails** (auto-deleted)
- ✅ Runs in **headless mode** (no GUI)
- ✅ **No data storage** (except API key in config.json)
- ✅ **Fresh browser context** per run (no tracking)

### ⚠️ What This Tool Does NOT Do

- ❌ No screenshots or recordings
- ❌ No logging to files
- ❌ No persistent cookies or sessions
- ❌ No data sent to third parties (except FreeModel API for OTP)

---

## 📚 Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| 🎭 playwright | Browser automation | Latest |
| 🌐 requests | HTTP requests | Latest |
| 🎨 rich | Terminal UI | Latest |
| 🔧 asyncio | Async operations | Built-in |
| 📝 re | Regex patterns | Built-in |
| 📦 json | Config management | Built-in |

---

## 🎓 Advanced Usage

### 🔧 Customizing Regex Patterns

Edit these patterns in `auto_registration.py`:

```python
# Email field detection
EMAIL_PATTERN = re.compile(r'(email|e[\-_]?mail|mail|user[\-_]?name)', re.IGNORECASE)

# OTP field detection
OTP_PATTERN = re.compile(r'(otp|code|verif|token|pin|confirm|auth|2fa|mfa|one[\-_]?time)', re.IGNORECASE)

# Send button detection
SEND_PATTERN = re.compile(r'(send|get|request|resend|generate)[\s\-_]*(code|otp|pin|verify|email)', re.IGNORECASE)

# Submit button detection
SUBMIT_PATTERN = re.compile(r'(submit|verify|confirm|continue|next|proceed|validate|done|finish)', re.IGNORECASE)

# OTP extraction from email
OTP_REGEX = re.compile(r'\b(\d{4,8})\b')
```

### 🔧 Adjusting Timeouts

```python
# Email polling timeout (default: 60s)
email_content = smart_poll_inbox(provider, auth_data, timeout=60)

# OTP field appearance timeout (default: 15s)
otp_field = await wait_for_otp_field(page, timeout=15)

# Retry attempts (default: 3)
await retry_async(fn, retries=3, delay=1.5, label="step")
```

---

## 🤝 Contributing

Found a bug? Have a feature request? Want to improve the regex patterns?

1. 🍴 Fork the repository
2. 🔧 Make your changes
3. ✅ Test thoroughly
4. 📬 Submit a pull request

---

## 📜 Disclaimer

⚠️ **Important Legal Notice**

This tool is provided for **educational and testing purposes only**.

- ✅ Use only on websites you own or have permission to test
- ✅ Respect website terms of service
- ✅ Do not use for spam or malicious purposes
- ✅ Temporary emails may be blocked by some services
- ✅ Author is not responsible for misuse

**Use responsibly and ethically!** 🙏

---

## 📞 Support

Need help? Have questions?

- 📧 Contact: vinayakkumar9000
- 🐛 Report bugs: Create an issue
- 💡 Feature requests: Create an issue
- 📖 Documentation: This README

---

## 🎉 Acknowledgments

- 🎭 **Playwright** - Amazing browser automation
- 📧 **mail.tm & guerrillamail** - Temporary email services
- 🧠 **FreeModel** - AI-powered OTP extraction
- 🎨 **Rich** - Beautiful terminal output
- 🙏 **Open Source Community** - For making this possible

---

<div align="center">

### 🌟 Star this project if you find it useful! 🌟

**Made with ❤️ by vinayakkumar9000**

**Version 3.1** | **2026**

</div>

---

## 📝 Changelog

### v3.1 (Current)
- ✨ Universal regex-based field detection
- 🧠 Regex-first OTP extraction with AI fallback
- 📧 Multi-provider email fallback (mail.tm → guerrillamail)
- ⚡ Smart polling (2s intervals, immediate stop)
- 🔄 Auto-retry system (3 attempts per step)
- 📱 Multi-step form support (15s OTP field polling)
- 🆕 Fresh browser context per run
- 🪶 Lightweight (no logging, no screenshots)
- 🎨 Beautiful terminal UI with emojis

### v1.0
- 🎯 Basic registration automation
- 📧 Single email provider (mail.tm)
- 🧠 AI-only OTP extraction
- 🔍 Hardcoded CSS selectors

---

## 🔮 Future Roadmap

- [ ] 🌍 Support for international identities (not just Indian)
- [ ] 🎯 CAPTCHA solving integration
- [ ] 📊 Success rate analytics
- [ ] 🔌 Plugin system for custom providers
- [ ] 🎨 Web UI dashboard
- [ ] 📱 Mobile browser support
- [ ] 🔐 2FA/MFA support beyond OTP
- [ ] 🌐 Proxy support
- [ ] 📝 Custom identity templates
- [ ] 🤖 Machine learning for field detection

---

**🚀 Happy Automating! ⚡✨**