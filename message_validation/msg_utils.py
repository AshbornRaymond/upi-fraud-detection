# message_validation/msg_utils.py

"""Utility functions for message analysis"""

import re

def extract_features(text: str):
    """Extract features from message text"""
    features = {}
    
    # URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    features['has_url'] = len(urls) > 0
    features['url_count'] = len(urls)
    features['urls'] = urls
    
    # Phone numbers
    phone_pattern = r'\b\d{10}\b|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    features['has_phone'] = len(phones) > 0
    features['phone_count'] = len(phones)
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    features['has_email'] = len(emails) > 0
    
    # UPI IDs
    upi_pattern = r'\b[\w.-]+@[\w.-]+\b'
    potential_upis = [m for m in re.findall(upi_pattern, text) if '@' in m and not '@gmail' in m.lower()]
    features['has_upi'] = len(potential_upis) > 0
    
    # Text stats
    features['length'] = len(text)
    features['word_count'] = len(text.split())
    features['has_special_chars'] = bool(re.search(r'[!@#$%^&*()_+=\[\]{}|;:,.<>?]', text))
    
    return features

if __name__ == "__main__":
    test = "URGENT: Click https://fake-bank.com or call 9876543210"
    features = extract_features(test)
    print(features)
