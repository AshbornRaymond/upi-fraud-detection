# train_dynamic.py (robust version)
import json
import joblib
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import math
import sys

DATA = Path(r"D:\major project\data")
DJ = Path(r"D:\major project\stage2_dynamic\dynamic_json")

# load scored_full.csv (ensure it exists)
scored_fp = DATA / "scored_full.csv"
if not scored_fp.exists():
    print(f"ERROR: {scored_fp} not found. Run Stage-1 scoring first.")
    sys.exit(1)

scored = pd.read_csv(scored_fp)

# read dynamic JSONs
rows = []
for f in sorted(DJ.glob("*.json")):
    try:
        j = json.load(open(f, "r", encoding="utf-8"))
    except Exception as e:
        print(f"warning: failed to load {f}: {e}")
        continue
    # try to read URL/id fields robustly
    final_url = j.get("final_url") or j.get("url") or j.get("source_url") or ""
    dom = j.get("dom", {}) or {}
    upi = j.get("upi", []) or []
    rows.append({
        "final_url": final_url,
        "script_count": dom.get("script_count", 0),
        "iframe_count": dom.get("iframe_count", 0),
        "form_count": dom.get("form_count", 0),
        "has_otp_input": int(dom.get("has_otp_input", False)),
        "has_password_input": int(dom.get("has_password_input", False)),
        "has_pin_input": int(dom.get("has_pin_input", False)),
        "large_cta_above_fold": int(dom.get("large_cta_above_fold", False)),
        "onbeforeunload": int(dom.get("onbeforeunload", False)),
        "timings": (j.get("timings") or {}).get("nav_time_s", 0),
        "upi_count": len(upi)
    })

if not rows:
    print("ERROR: no dynamic JSON files found in", DJ)
    sys.exit(1)

dyn = pd.DataFrame(rows)
# normalize for joining
scored2 = scored.copy()
if 'url' not in scored2.columns:
    print("ERROR: 'url' column missing from scored_full.csv")
    sys.exit(1)

scored2['url_norm'] = scored2['url'].astype(str).str.rstrip('/').str.lower()
dyn['final_url_norm'] = dyn['final_url'].astype(str).str.rstrip('/').str.lower()

merged = pd.merge(scored2, dyn, left_on='url_norm', right_on='final_url_norm', how='left')

# If label column name differs, try a few common names
label_cols = [c for c in merged.columns if c.lower() in ("label", "label_is_phish", "is_phish", "phish", "label_phish")]
if not label_cols:
    print("ERROR: No label column found in scored_full.csv. Expected 'label_is_phish' or similar.")
    print("Columns present:", merged.columns.tolist())
    sys.exit(1)
label_col = label_cols[0]
merged = merged.copy()
# ensure label is numeric 0/1
merged[label_col] = pd.to_numeric(merged[label_col], errors='coerce')
merged = merged.dropna(subset=[label_col])
merged[label_col] = merged[label_col].astype(int)

# choose features (adapt if you used different column names)
available_feats = merged.columns.tolist()
# include xgb_prob and if_score if produced by stage1; otherwise use numeric static placeholders
candidate_features = []
for f in ['xgb_prob', 'if_score', 'script_count', 'iframe_count', 'form_count',
          'has_otp_input', 'has_pin_input', 'upi_count', 'timings']:
    if f in available_feats:
        candidate_features.append(f)

if not candidate_features:
    # fallback: take any numeric columns except label
    candidate_features = merged.select_dtypes(include=[np.number]).columns.tolist()
    candidate_features = [c for c in candidate_features if c != label_col]
    if not candidate_features:
        print("ERROR: No numeric features found to train on.")
        sys.exit(1)

print("Using features:", candidate_features)

X = merged[candidate_features].fillna(0).astype(float)
y = merged[label_col].astype(int)

n_samples = len(y)
n_classes = y.nunique()
class_counts = y.value_counts().to_dict()
print(f"Dataset: {n_samples} samples, classes: {n_classes}, counts: {class_counts}")

# decide whether to stratify
desired_test_frac = 0.25
n_test = math.ceil(desired_test_frac * n_samples)
use_stratify = True
if n_test < n_classes:
    print(f"Warning: desired test set size {n_test} < number of classes {n_classes} -> cannot stratify.")
    use_stratify = False
else:
    # also require that each class has at least 2 samples (one for train, one for test)
    min_count = min(class_counts.values())
    if min_count < 2:
        print(f"Warning: at least one class has <2 samples (counts={class_counts}) -> not safe to stratify.")
        use_stratify = False

# Final attempt to split
try:
    if use_stratify:
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=desired_test_frac, random_state=42, stratify=y)
        print("Stratified split used.")
    else:
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=min(0.5, desired_test_frac), random_state=42, shuffle=True)
        print("Non-stratified split used (fallback).")
except Exception as e:
    print("Warning: train_test_split failed with stratify settings:", e)
    print("Falling back to non-stratified split with test_size=0.33")
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.33, random_state=42, shuffle=True)

print(f"Train samples: {len(y_train)}, Val samples: {len(y_val)}")
if len(y_train) < 5:
    print("Warning: very small training set; consider collecting more data before training a stable model.")

# Train a basic XGBoost model
model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.08, n_jobs=-1, random_state=42, tree_method="hist")
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=True)

out_fp = Path(r"D:\major project\stage2_dynamic") / "xgb_dynamic.pkl"
joblib.dump(model, out_fp)
print("Saved dynamic model to:", out_fp)
