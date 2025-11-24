# Code Documentation Summary

This document provides an overview of all the code files in the project and what they do.

## 📂 Project Structure Overview

### Backend (Web Server)

#### `backend/app.py` ⭐ START HERE!
**Purpose**: Main web server that handles all API requests

**What it does**:
- Creates the FastAPI web server
- Defines API endpoints (`/health`, `/validate`)
- Handles file uploads for QR codes
- Routes requests to the orchestrator
- Serves the web interface

**Key functions**:
- `health()` - Health check endpoint
- `validate()` - Main validation endpoint for all input types

**Beginner note**: This is the entry point of the application. Start reading here!

---

#### `backend/orchestrator.py` ⭐ CORE LOGIC
**Purpose**: Routes validation requests to specialized validators

**What it does**:
- Acts as a traffic controller for validation requests
- Implements caching to speed up repeated validations
- Coordinates between Stage 1 (fast ML) and Stage 2 (deep analysis)
- Combines results from different validation stages

**Key functions**:
- `validate_input()` - Main routing function
- `validate_link()` - Routes link validation
- `validate_vpa()` - Routes VPA validation
- `validate_message()` - Routes message validation
- `validate_qr()` - Routes QR code validation
- `get_cache_key()` - Generates cache keys
- `get_from_cache()` - Retrieves cached results
- `save_to_cache()` - Stores validation results

**Beginner note**: This file shows how modular architecture works - breaking complex tasks into smaller pieces.

---

### Link Validation Module

#### `link_validation/feature_extractor.py`
**Purpose**: Extracts features from URLs for ML analysis

**What it does**:
- Parses URLs into components (domain, path, query, etc.)
- Calculates 38 different features like:
  - Domain age estimation
  - SSL/HTTPS status
  - URL length and complexity
  - Suspicious keywords (kyc, verify, update)
  - Brand impersonation detection
  - UPI-specific patterns

**Key functions**:
- `extract_training_features()` - Extracts all 38 features from a URL
- `get_feature_array()` - Converts features to array for ML model

**Beginner note**: This is where we turn a URL into numbers that ML models can understand.

---

#### `link_validation/validator.py` ⭐ STAGE 1
**Purpose**: ML-based URL fraud detection (Stage 1)

**What it does**:
- Loads pre-trained ML models (XGBoost, Isolation Forest)
- Checks URLs against whitelist (trusted domains)
- Checks URLs against blacklist (known phishing patterns)
- Uses ML models to predict fraud probability
- Returns verdict: OK, WARN, or BLOCK

**Key functions**:
- `validate_url()` - Main validation function
- `load_models()` - Loads ML models (cached)
- `is_trusted_domain()` - Checks if URL is whitelisted
- `check_domain_blacklist()` - Checks for phishing patterns

**Key variables**:
- `TRUSTED_DOMAINS` - List of safe domains (banks, payment apps)
- `PHISHING_PATTERNS` - Regex patterns for phishing domains
- `DOMAIN_KEYWORDS` - Suspicious keywords in domains

**Beginner note**: This is the first line of defense - fast ML-based checking.

---

#### `link_validation/link_orchestrator.py`
**Purpose**: Alternative link validation orchestrator

**What it does**:
- Similar to validator.py but with different architecture
- Manages model caching globally
- Provides command-line interface for testing

**Key functions**:
- `load_stage1_artifacts()` - Loads ML models with caching
- `static_score_for_url()` - Validates URL using ML
- `simple_features_from_url()` - Extracts basic features
- `fallback_rule_based()` - Fallback if ML fails

**Beginner note**: Alternative implementation showing different design patterns.

---

### QR Code Validation Module

#### `qr_validation/qr_parser.py`
**Purpose**: Decodes and identifies QR code types

**What it does**:
- Decodes QR code images using pyzbar library
- Identifies QR code type (URL, UPI payment, VPA, etc.)
- Extracts relevant data (URLs, VPA addresses)
- Routes to appropriate validator based on type

**Key functions**:
- `parse_qr_image()` - Main QR parsing function
- `decode_qr()` - Decodes QR image to text
- `identify_qr_content_type()` - Determines QR type

**QR Types Detected**:
- `protected_payment` - Encrypted payment QR (Google Pay, PhonePe)
- `upi` - Standard UPI payment QR
- `url` - HTTP/HTTPS link QR
- `vpa` - Plain VPA address
- `tel`, `mailto`, `sms` - System intents
- `geo` - Location/maps
- `wifi` - WiFi credentials
- `vcard` - Contact card
- `text` - Plain text

**Beginner note**: This is the QR code decoder. It figures out what's in the QR code.

---

#### `qr_validation/vpa_validator.py`
**Purpose**: Validates VPA (UPI ID) formats and providers

**What it does**:
- Checks if VPA format is valid (username@provider)
- Maintains list of known UPI providers
- Validates against known banks and payment apps
- Returns OK for known providers, WARN for unknown

**Key functions**:
- `validate_vpa_format()` - Main VPA validation
- `is_vpa_format()` - Quick format check

**Key data**:
- `KNOWN_PROVIDERS` - Dictionary of UPI providers and their names

**Beginner note**: VPAs are like email addresses for payments. This checks if they're valid.

---

#### `qr_validation/qr_utils.py`
**Purpose**: Utility functions for QR analysis

**What it does**:
- Provides helper functions for QR code processing
- Extracts VPA from UPI strings
- Identifies protected payment QR formats
- Generates human-readable descriptions

**Key functions**:
- `extract_vpa_from_upi()` - Gets VPA from UPI URL
- `is_protected_payment_qr()` - Checks if QR is encrypted payment
- `get_qr_description()` - Returns verdict and description for QR type

---

### Message Validation Module

#### `message_validation/msg_validator.py`
**Purpose**: Validates SMS/WhatsApp messages for fraud

**What it does**:
- Analyzes message text for suspicious patterns
- Combines rule-based and ML-based detection
- Extracts and validates URLs within messages
- Checks for urgency indicators and scam keywords

**Key functions**:
- `validate_message()` - Main message validation
- `analyze_message()` - Legacy function (alias)

**Beginner note**: This analyzes text messages to find scam patterns.

---

#### `message_validation/msg_rules.py`
**Purpose**: Rule-based message fraud detection

**What it does**:
- Defines lists of suspicious keywords
- Checks for high-risk patterns
- Calculates fraud score based on rules
- Detects urgency indicators and aggressive formatting

**Key functions**:
- `check_rules()` - Applies all rule-based checks

**Key data**:
- `high_risk` - List of dangerous keywords (kyc, verify, urgent, etc.)
- `urgency_words` - Words indicating urgency

---

#### `message_validation/msg_utils.py`
**Purpose**: Utility functions for message analysis

**What it does**:
- Extracts features from message text
- Finds URLs, phone numbers, emails in text
- Calculates text statistics
- Identifies UPI IDs in messages

**Key functions**:
- `extract_features()` - Extracts all features from message text
- `extract_urls()` - Finds URLs in text
- `urgency_score()` - Calculates urgency level
- `has_money_words()` - Checks for money-related words

---

#### `message_validation/model/msg_classifier.py`
**Purpose**: Lightweight ML classifier for messages

**What it does**:
- Provides simple ML-based message classification
- Uses rule-based scoring (can be replaced with real ML model)
- Calculates scam probability score

**Key functions**:
- `predict_msg()` - Predicts if message is fraud

**Key data**:
- `SCAM_KEYWORDS` - List of scam-related words

**Beginner note**: This is a placeholder for more sophisticated ML. You can replace it with a trained model.

---

### Stage 1 (Static Analysis)

#### `stage1/links_stage1.py` ⭐ ML TRAINING
**Purpose**: Trains the ML models for Stage 1

**What it does**:
- Loads training data from CSV
- Trains XGBoost classifier
- Trains Isolation Forest for anomaly detection
- Optimizes decision thresholds
- Saves trained models and configuration

**Key functions**:
- `main()` - Main training pipeline
- `isolation_forest_scores()` - Normalizes IF scores
- `eval_combo()` - Evaluates ensemble performance

**Training process**:
1. Load CSV training data
2. Split into train/validation sets
3. Train XGBoost with class balancing
4. Train Isolation Forest on legitimate samples
5. Search for optimal thresholds
6. Save models to `stage1/` directory

**Output files**:
- `xgb_static.pkl` - XGBoost model
- `iforest_static.pkl` - Isolation Forest model
- `if_scaler.pkl` - Feature scaler
- `ensemble_config.json` - Model configuration

**Beginner note**: Run this to train new ML models. Requires training data in `data/` folder.

---

#### `stage1/ensemble_config.json`
**Purpose**: Configuration for ML ensemble

**Contains**:
- Feature list (38 features)
- Ensemble weights (how to combine XGBoost and Isolation Forest)
- Decision thresholds (t_block, t_ok)
- Validation metrics

---

### Stage 2 (Dynamic Analysis)

#### `stage2_dynamic/stage2_validator.py` ⭐ STAGE 2 ENTRY
**Purpose**: Entry point for Stage 2 validation

**What it does**:
- Coordinates headless browser scanning
- Calls scan_playwright for browser automation
- Combines behavioral analysis with ML scoring
- Returns verdict based on deep analysis

**Key functions**:
- `validate_url_stage2()` - Main Stage 2 validation function

**Beginner note**: Stage 2 is the deep check - it actually visits the website!

---

#### `stage2_dynamic/headless_browser.py` ⭐ BROWSER AUTOMATION
**Purpose**: Headless browser-based URL analysis

**What it does**:
- Opens URLs in invisible browser (headless Chrome)
- Analyzes actual webpage behavior:
  - Form fields (password, OTP, PIN)
  - Banking UI mimicry
  - Suspicious JavaScript
  - Domain redirects
- Combines behavioral flags with ML model
- Returns detailed risk assessment

**Key functions**:
- `scan_url_headless()` - Main browser scanning function
- `load_stage2_model()` - Loads Stage 2 ML model
- `extract_behavioral_features()` - Extracts features from webpage
- `is_trusted_domain()` - Checks whitelist
- `is_likely_bank_domain()` - Detects bank-like domains

**Key data**:
- `TRUSTED_DOMAINS` - Whitelist of safe domains
- `SUSPICIOUS_TLDS` - List of risky top-level domains
- `BANK_KEYWORDS` - Words indicating banking sites

**Beginner note**: This is the most sophisticated part - it acts like a real user visiting the site.

---

#### `stage2_dynamic/scan_playwright.py`
**Purpose**: Playwright-based browser automation

**What it does**:
- Uses Playwright library for browser control
- Implements advanced stealth techniques
- Handles timeouts and retries
- Extracts DOM features from webpages
- Saves screenshots and HTML for analysis

**Key functions**:
- `extract_dom_features()` - Extracts features from webpage
- `create_stealth_context()` - Creates stealth browser context
- `scan_single_url()` - Scans one URL with retries

**Configuration**:
- `NAV_TIMEOUT` - Navigation timeout (60 seconds)
- `MAX_ATTEMPTS` - Retry attempts per URL
- `CONCURRENCY` - Parallel scanning limit

**Beginner note**: Advanced browser automation. Uses anti-detection techniques.

---

#### `stage2_dynamic/fallback_engine.py`
**Purpose**: Fallback validation when browser fails

**What it does**:
- Provides simple rule-based validation
- Used when Playwright/browser automation fails
- Basic checks without requiring browser

---

#### `stage2_dynamic/train_dynamic.py`
**Purpose**: Trains Stage 2 ML models

**What it does**:
- Loads behavioral features from Stage 2 scans
- Trains ML model on browser-extracted features
- Saves trained model for Stage 2 validation

---

### VPA Validation Module

#### `vpa_validation/vpa_validator.py`
**Purpose**: Comprehensive VPA validation

**What it does**:
- Validates VPA format
- Checks against provider database
- Analyzes VPA patterns for fraud

---

#### `vpa_validation/vpa_rules.py`
**Purpose**: Rule-based VPA validation logic

**Contains**: Business rules for VPA validation

---

#### `vpa_validation/vpa_utils.py`
**Purpose**: VPA utility functions

**Contains**: Helper functions for VPA processing

---

#### `vpa_validation/vpa_reputation.py`
**Purpose**: VPA reputation checking

**What it does**:
- Checks VPA against reputation database
- Identifies known fraudulent VPAs

---

### Frontend (Web Interface)

#### `backend/static/index.html`
**Purpose**: Main web interface HTML

**What it includes**:
- Tab navigation (Link, VPA, Message, QR)
- Input forms for each validation type
- Result display area
- Health status indicator

**Structure**:
- Header with title
- Tab buttons
- Form for each input type
- Loading indicator
- Results container

---

#### `backend/static/main.js`
**Purpose**: Frontend JavaScript logic

**What it does**:
- Handles tab switching
- Submits validation requests to backend
- Displays results with colors (OK=green, WARN=yellow, BLOCK=red)
- Shows loading indicators
- Formats and displays reasons

**Key functions**:
- `checkHealth()` - Checks if server is running
- `setupTabs()` - Initializes tab navigation
- `setupForms()` - Sets up form submission handlers
- `validateText()` - Validates text inputs (link/vpa/message)
- `validateQR()` - Validates QR code images
- `displayResult()` - Shows validation results

**Beginner note**: This is the interactive part that users see and click on.

---

#### `backend/static/styles.css`
**Purpose**: Web interface styling

**What it includes**:
- Modern card-based layout
- Color scheme (green/yellow/red for verdicts)
- Responsive design
- Button and form styling
- Animation for loading states

---

### Data Files

#### `data/` folder
**Purpose**: Training data and datasets

**Files**:
- `links_stage1_training_refined.csv` - Training data for Stage 1
- `scored_full.csv` - Full scored dataset
- `warn_urls.csv` - URLs flagged for Stage 2 analysis
- Various other training datasets

---

### Configuration Files

#### `requirements.txt`
**Purpose**: List of required Python packages

**Install with**: `pip install -r requirements.txt`

**Includes**:
- FastAPI (web framework)
- XGBoost (ML)
- scikit-learn (ML)
- Playwright (browser automation)
- Pillow & pyzbar (QR code processing)
- And more...

---

#### `.gitignore`
**Purpose**: Tells Git which files not to track

**Excludes**:
- `__pycache__/` (Python cache)
- `*.pkl` (large model files)
- `venv/` (virtual environment)
- IDE settings
- Log files

---
