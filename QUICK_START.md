# Quick Start Guide - UPI Fraud Detection System

This is a simplified guide to get you up and running in 5 minutes!

## ⚡ Super Quick Setup (For Beginners)

### Step 1: Install Python

1. Download Python from https://www.python.org/downloads/
2. During installation, **CHECK THE BOX** that says "Add Python to PATH"
3. Click "Install Now"

### Step 2: Open Command Prompt

- Press `Windows + R`
- Type `cmd` and press Enter

### Step 3: Navigate to Project

```cmd
cd "d:\major project ultra pro max\major project"
```

### Step 4: Install Dependencies

```cmd
pip install -r requirements.txt
```

Wait for everything to install (takes 2-5 minutes).

### Step 5: Start the Server

```cmd
python backend\app.py
```

You should see:
```
🚀 Starting UPI Fraud Detection System
Server: http://localhost:8008
```

### Step 6: Open in Browser

Open your web browser and go to:
```
http://localhost:8008/static/index.html
```

**That's it! The system is now running! 🎉**

## 🎯 Quick Test

Try validating this suspicious URL:
```
http://hdfc-netbanking-verify.com/kyc-update
```

The system should mark it as **BLOCK** because:
- It's impersonating HDFC Bank
- Contains suspicious keywords (verify, kyc, update)
- Uses a fake domain

## 📱 Testing Different Input Types

### Test a Link
```
https://paytm.com → OK (legitimate)
http://paytm-kyc-verify.xyz → BLOCK (phishing)
```

### Test a VPA
```
user@paytm → OK (known provider)
user@unknown → WARN (unrecognized provider)
```

### Test a Message
```
"Your order has been delivered" → OK
"URGENT: Update KYC now http://fake-bank.com" → BLOCK
```

### Test a QR Code
Upload any QR code image (payment QR, URL QR, etc.)

## 🛑 Stopping the Server

In the Command Prompt where the server is running:
- Press `Ctrl + C`
- Type `Y` if asked to confirm

## 🔧 Common Issues & Fixes

### "Python is not recognized"
**Fix**: You need to add Python to PATH
1. Search "Environment Variables" in Windows
2. Edit PATH variable
3. Add Python installation path

### "Module not found"
**Fix**: Install missing package
```cmd
pip install <package-name>
```

### "Port 8008 already in use"
**Fix**: Close other programs using that port, or change port in `backend\app.py`

### "Model file not found"
**Fix**: Make sure `stage1/` folder contains `.pkl` files. If missing, run:
```cmd
python stage1\links_stage1.py
```

## 📊 Understanding Results

### Verdict Meanings

| Verdict | Color | Meaning |
|---------|-------|---------|
| **OK** | Green | Safe - you can proceed |
| **WARN** | Yellow | Be careful - verify before proceeding |
| **BLOCK** | Red | Dangerous - do NOT proceed! |

### Risk Score

- **0.0 - 0.3** = Low risk
- **0.3 - 0.7** = Medium risk  
- **0.7 - 1.0** = High risk

## 🎓 What Each Component Does

```
backend/app.py          → Web server (handles requests)
backend/orchestrator.py → Routes requests to validators
link_validation/        → Checks if URLs are phishing
qr_validation/          → Decodes and validates QR codes
message_validation/     → Analyzes SMS for fraud
stage1/                 → Fast ML-based validation
stage2_dynamic/         → Deep browser-based analysis
```

## 📝 Project File Overview

### Main Files (Must Understand)
- `backend/app.py` - Start here! Main server file
- `backend/orchestrator.py` - Routes validation requests
- `README.md` - Complete documentation
- `requirements.txt` - List of dependencies

### Validation Modules
- `link_validation/validator.py` - Validates URLs
- `qr_validation/qr_parser.py` - Decodes QR codes
- `message_validation/msg_validator.py` - Checks messages
- `stage2_dynamic/headless_browser.py` - Browser automation

### ML Models
- `stage1/xgb_static.pkl` - Trained fraud detector
- `stage1/iforest_static.pkl` - Anomaly detector
- `stage1/links_stage1.py` - Training script

### Web Interface
- `backend/static/index.html` - Main UI
- `backend/static/main.js` - Frontend logic
- `backend/static/styles.css` - Styling

## 🚀 Next Steps

1. **Explore the code**: Start with `backend/app.py`
2. **Test different inputs**: Try various URLs, VPAs, messages
3. **Read the full README**: `README.md` has detailed explanations
4. **Set up Git**: Follow `GIT_SETUP_GUIDE.md` to version control
5. **Experiment**: Try modifying the code!

## 💡 Tips for Learning

### Understanding the Flow

1. User submits input on web page (`index.html`)
2. Frontend sends request to backend (`main.js` → `app.py`)
3. Orchestrator routes to correct validator (`orchestrator.py`)
4. Validator analyzes input using ML models
5. Result is sent back and displayed

### Key Concepts

- **ML Models**: Pre-trained to recognize fraud patterns
- **Stage 1**: Fast check using statistical features
- **Stage 2**: Deep check by actually visiting the website
- **Caching**: Store results to avoid re-checking same input
- **Whitelisting**: List of trusted domains that skip checks

### How to Modify

Want to add a new trusted domain?
→ Edit `link_validation/validator.py` → `TRUSTED_DOMAINS`

Want to add new fraud keywords?
→ Edit `message_validation/msg_rules.py` → `high_risk` list

Want to change risk thresholds?
→ Edit `backend/orchestrator.py` → verdict logic

## 📞 Getting Help

Stuck? Here's what to check:

1. **Read error messages carefully** - they usually tell you what's wrong
2. **Check the terminal** - look for error logs
3. **Verify installation** - make sure all packages installed
4. **Test components separately** - isolate the problem
5. **Review code comments** - we've explained everything!

## 🎯 Challenge Yourself

Once you understand the basics, try:

1. **Add a new feature**: Detect more fraud patterns
2. **Improve the UI**: Make it look better
3. **Train with new data**: Update the ML models
4. **Add new input types**: What else could be validated?
5. **Deploy online**: Make it accessible to others

## 📚 Learning Path

### Beginner (Week 1-2)
- Run the system
- Test different inputs
- Understand the flow
- Read code comments

### Intermediate (Week 3-4)
- Modify simple rules
- Add new keywords
- Change thresholds
- Customize UI

### Advanced (Month 2+)
- Retrain ML models
- Add new features
- Optimize performance
- Deploy to production

---

**Remember**: Everyone starts as a beginner! Take your time, experiment, and don't be afraid to break things - that's how you learn! 🚀

**Need the full documentation?** Check `README.md`  
**Want to use Git?** Check `GIT_SETUP_GUIDE.md`  
**Have questions?** Read the code comments - they explain everything!
