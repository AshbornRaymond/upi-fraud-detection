# Intelligent System For UPI Fraud Detection

A real-time fraud detection system for UPI (Unified Payments Interface) transactions in India. This system analyzes links, VPA addresses, messages, and QR codes to identify potential fraud attempts.

## 🎯 What Does This Project Do?

This system helps protect users from UPI fraud by analyzing different types of inputs:

- **🔗 Links**: Checks if URLs are phishing attempts trying to steal your information
- **💳 VPA (Virtual Payment Address)**: Validates UPI IDs like `username@bank`
- **💬 Messages**: Analyzes SMS/WhatsApp messages for fraud indicators
- **📱 QR Codes**: Scans payment QR codes to detect suspicious patterns

### How It Works

The system uses a **two-stage validation approach**:

1. **Stage 1 (Fast ML Check)**: Uses machine learning models trained on fraud patterns to quickly assess risk
2. **Stage 2 (Deep Browser Analysis)**: For suspicious cases, launches a headless browser to analyze the actual website behavior

## 🏗️ Project Structure

```
major project/
├── backend/                    # Web server and API
│   ├── app.py                 # Main FastAPI server
│   ├── orchestrator.py        # Routes validation requests
│   └── static/                # Web interface (HTML/CSS/JS)
│       ├── index.html
│       ├── main.js
│       └── styles.css
│
├── link_validation/            # URL fraud detection
│   ├── feature_extractor.py   # Extracts features from URLs
│   ├── link_orchestrator.py   # Manages link validation
│   └── validator.py           # ML-based link validator
│
├── message_validation/         # SMS/message fraud detection
│   ├── msg_validator.py       # Main message validator
│   ├── msg_rules.py           # Rule-based checks
│   ├── msg_utils.py           # Helper functions
│   └── model/
│       └── msg_classifier.py  # ML classifier for messages
│
├── qr_validation/              # QR code fraud detection
│   ├── qr_parser.py           # Decodes QR codes
│   ├── qr_decoder.py          # QR image processing
│   ├── qr_utils.py            # QR analysis helpers
│   └── vpa_validator.py       # Validates UPI VPA addresses
│
├── stage1/                     # Stage 1: Static ML analysis
│   ├── links_stage1.py        # Training script for Stage 1
│   ├── xgb_static.pkl         # Trained XGBoost model
│   ├── iforest_static.pkl     # Trained Isolation Forest model
│   └── ensemble_config.json   # Model configuration
│
├── stage2_dynamic/             # Stage 2: Dynamic browser analysis
│   ├── stage2_validator.py    # Stage 2 entry point
│   ├── headless_browser.py    # Browser automation
│   ├── scan_playwright.py     # Playwright-based scanner
│   └── train_dynamic.py       # Training script for Stage 2
│
├── vpa_validation/             # VPA-specific validation
│   ├── vpa_validator.py       # VPA format checker
│   ├── vpa_rules.py           # VPA validation rules
│   └── vpa_utils.py           # VPA helper functions
│
└── data/                       # Training data and datasets
    └── *.csv                   # Various training datasets
```

## 🚀 Getting Started

### Prerequisites

Before you begin, make sure you have:

- **Python 3.8 or higher** installed on your system
- **pip** (Python package installer)
- Basic understanding of command line/terminal

### Installation

1. **Clone or download this repository** to your computer

2. **Navigate to the project directory**:
   ```bash
   cd "d:\upi-fraud-detection"
   ```

3. **Install required Python packages**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the server**:
   ```bash
   python backend/app.py
   ```

   Or if that doesn't work:
   ```bash
   python -m backend.app
   ```

2. **Open your web browser** and go to:
   ```
   http://localhost:8008/static/index.html
   ```

3. You should see the fraud detection interface!

## 🎮 How to Use

### Testing Links

1. Click the **🔗 Link** tab
2. Paste a URL (e.g., `https://example.com`)
3. Click "Validate Link"
4. The system will analyze it and show:
   - **OK**: Safe to visit
   - **WARN**: Be careful, might be suspicious
   - **BLOCK**: Dangerous, do not visit!

### Testing VPA (UPI ID)

1. Click the **💳 VPA** tab
2. Enter a UPI ID (e.g., `username@paytm`)
3. Click "Validate VPA"
4. It checks if the VPA format is valid and the provider is known

### Testing Messages

1. Click the **💬 Message** tab
2. Paste an SMS or WhatsApp message
3. Click "Validate Message"
4. The system will:
   - Look for suspicious keywords
   - Extract and validate any URLs in the message
   - Check for phone numbers

### Testing QR Codes

1. Click the **📱 QR Code** tab
2. Upload a QR code image
3. Click "Validate QR Code"
4. The system will:
   - Decode the QR code
   - Identify what type it is (URL, UPI, etc.)
   - Validate the contents for fraud

## 🔧 Configuration

### Model Files

The system requires trained ML models located in:
- `stage1/xgb_static.pkl` - XGBoost fraud detector
- `stage1/iforest_static.pkl` - Anomaly detector
- `stage1/ensemble_config.json` - Model settings

### Trusted Domains

The system has a whitelist of trusted domains (banks, payment apps) in:
- `link_validation/validator.py` - Stage 1 whitelist
- `stage2_dynamic/headless_browser.py` - Stage 2 whitelist

You can modify these lists to add new trusted domains.

## 📊 How the ML Models Work

### Stage 1: Static Analysis

Uses **38 features** extracted from URLs:
- Domain age
- SSL/HTTPS status
- URL length and structure
- Suspicious keywords (kyc, verify, update)
- Brand impersonation detection
- UPI-specific patterns

**Models used**:
- **XGBoost**: Supervised learning to classify fraud vs. legitimate
- **Isolation Forest**: Unsupervised anomaly detection

### Stage 2: Dynamic Analysis

When Stage 1 is uncertain, Stage 2:
1. Opens the URL in a headless browser (invisible browser)
2. Analyzes the actual webpage:
   - Password/OTP input fields
   - Banking UI mimicry
   - Suspicious JavaScript
   - Domain redirects
3. Combines behavioral analysis with ML scoring

## 🛠️ Development

### Training New Models

To retrain the Stage 1 model with new data:

```bash
python stage1/links_stage1.py
```

This will:
- Load training data from `data/links_stage1_training_refined.csv`
- Train XGBoost and Isolation Forest models
- Save new models to `stage1/` directory

### Adding New Features

To add new fraud detection features:

1. **For URLs**: Edit `link_validation/feature_extractor.py`
2. **For messages**: Edit `message_validation/msg_rules.py`
3. **For VPAs**: Edit `vpa_validation/vpa_rules.py`

### Running Tests

You can test individual components:

```bash
# Test link validation
python -m link_validation.validator https://example.com

# Test VPA validation
python -m qr_validation.vpa_validator username@bank

# Test message validation
python -m message_validation.msg_validator "Your test message"
```

## 📝 API Documentation

The FastAPI framework automatically generates API documentation.

Once the server is running, visit:
- **Swagger UI**: http://localhost:8008/docs
- **ReDoc**: http://localhost:8008/redoc

### API Endpoints

#### POST /validate

Main validation endpoint.

**Request**:
```bash
curl -X POST "http://localhost:8008/validate" \
     -F "type=link" \
     -F "value=https://example.com"
```

**Parameters**:
- `type`: One of `"link"`, `"vpa"`, `"message"`, `"qr"`
- `value`: The text to validate (for link/vpa/message)
- `file`: The image file (for QR code)

**Response**:
```json
{
  "input": {"type": "link", "value": "https://example.com"},
  "final_verdict": "OK",
  "risk_score": 0.15,
  "reasons": ["✓ URL appears legitimate"],
  "stage1": {...},
  "stage2": {...}
}
```

#### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "Detection Engine",
  "version": "1.0 (beta)"
}
```

## 🔍 Understanding Verdicts

The system returns one of three verdicts:

| Verdict | Meaning | What to Do |
|---------|---------|------------|
| **OK** | Low risk, appears safe | Proceed normally |
| **WARN** | Medium risk, be careful | Verify before proceeding |
| **BLOCK** | High risk, likely fraud | Do NOT proceed! |

### Risk Scores

- **0.0 - 0.3**: Low risk (OK)
- **0.3 - 0.7**: Medium risk (WARN)
- **0.7 - 1.0**: High risk (BLOCK)

## 🧪 Example Fraud Patterns Detected

### Phishing URLs

- `sbi-netbanking-verify.com` → **BLOCK** (fake bank domain)
- `paytm-kyc-update.xyz` → **BLOCK** (impersonation + suspicious TLD)
- `bit.ly/win-bonus` → **WARN** (URL shortener + reward keyword)

### Suspicious VPAs

- `user123@unknownprovider` → **WARN** (unrecognized provider)
- `a@b` → **BLOCK** (invalid format)

### Fraud Messages

- "Update KYC urgently: http://fake-bank.com" → **BLOCK** (urgent keyword + suspicious URL)
- "You won ₹50,000! Click here" → **WARN** (lottery scam pattern)

## 🤝 Contributing

This is a learning project! If you want to improve it:

1. Make your changes
2. Test them thoroughly
3. Document what you changed
4. Share your improvements

## 📚 Technologies Used

- **FastAPI**: Modern Python web framework
- **XGBoost**: Gradient boosting for fraud classification
- **scikit-learn**: Isolation Forest for anomaly detection
- **Playwright**: Headless browser automation
- **Pillow**: Image processing for QR codes
- **pyzbar**: QR code decoding
- **pandas/numpy**: Data processing
- **joblib**: Model serialization

## ⚠️ Important Notes

### This is a Learning Project

This system is built for educational purposes. In production:
- Add proper authentication
- Use a database instead of in-memory cache
- Add rate limiting
- Deploy with HTTPS
- Add comprehensive logging
- Implement proper error handling

### Privacy & Security

- The system does NOT store any validated URLs or messages
- All validation happens locally
- No data is sent to external services (except when visiting URLs for Stage 2)

### Limitations

- Stage 2 validation requires internet connection
- ML models need periodic retraining with new fraud patterns
- Some legitimate sites might be flagged as suspicious
- New fraud techniques might not be detected

## 🐛 Troubleshooting

### Server won't start

**Problem**: `ModuleNotFoundError` when starting server

**Solution**: Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Models not found

**Problem**: `FileNotFoundError: stage1/xgb_static.pkl not found`

**Solution**: Train the models first:
```bash
python stage1/links_stage1.py
```

### Port already in use

**Problem**: `Address already in use`

**Solution**: Either:
1. Close the other program using port 8008
2. Or change the port in `backend/app.py`

### Headless browser fails

**Problem**: Stage 2 validation always fails

**Solution**: Install Playwright browsers:
```bash
playwright install chromium
```

## 📞 Support

For questions or issues:
1. Check the code comments - they explain how things work
2. Review the logs in the terminal
3. Test individual components separately
4. Make sure all dependencies are installed

## 📄 License

This project is for educational purposes. Feel free to learn from it, modify it, and share it!

## 🎓 Learning Resources

To understand this project better:

- **FastAPI**: https://fastapi.tiangolo.com/
- **Machine Learning Basics**: https://www.coursera.org/learn/machine-learning
- **XGBoost**: https://xgboost.readthedocs.io/
- **Web Development**: https://developer.mozilla.org/

---

**Made by students, for learning about fraud detection and machine learning! 🚀**
