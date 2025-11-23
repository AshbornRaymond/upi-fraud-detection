# QR Validation Module

### Features
- Decodes QR images using pyzbar.
- Detects if QR contains:
  - URL → send to link validation
  - UPI payment intent (upi://pay / collect) → extract pa, pn, am → send to VPA validation
- Normalizes text, parses query params.

### Run:
