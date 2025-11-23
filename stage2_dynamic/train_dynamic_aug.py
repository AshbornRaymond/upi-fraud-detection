# train_dynamic_aug.py
import json, joblib, math
from pathlib import Path
import pandas as pd, numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss, accuracy_score

DATA = Path(r"D:\major project\data")
DJ = Path(r"D:\major project\stage2_dynamic\dynamic_json")

scored_fp = DATA / "scored_full.csv"
if not scored_fp.exists():
    print("scored_full.csv missing. Run stage1 scoring first.")
    raise SystemExit

scored = pd.read_csv(scored_fp)
# load dynamic jsons
rows = []
for f in sorted(DJ.glob("*.json")):
    try:
        j = json.load(open(f, "r", encoding="utf-8"))
    except:
        continue
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
    print("No dynamic JSON files found.")
    raise SystemExit

dyn = pd.DataFrame(rows)
scored['url_norm'] = scored['url'].astype(str).str.rstrip('/').str.lower()
dyn['final_url_norm'] = dyn['final_url'].astype(str).str.rstrip('/').str.lower()
merged = pd.merge(scored, dyn, left_on='url_norm', right_on='final_url_norm', how='inner')

# find label col
label_candidates = [c for c in merged.columns if c.lower() in ("label", "label_is_phish", "is_phish", "phish")]
if not label_candidates:
    print("No label column found in scored_full.csv")
    raise SystemExit
label_col = label_candidates[0]
merged[label_col] = pd.to_numeric(merged[label_col], errors='coerce')
merged = merged.dropna(subset=[label_col])
merged[label_col] = merged[label_col].astype(int)

# choose features
feat_cols = [c for c in ['xgb_prob','if_score','script_count','iframe_count','form_count','has_otp_input','has_pin_input','upi_count','timings'] if c in merged.columns]
if not feat_cols:
    feat_cols = merged.select_dtypes(include=[np.number]).columns.tolist()
    feat_cols = [c for c in feat_cols if c != label_col]

X_real = merged[feat_cols].fillna(0).astype(float)
y_real = merged[label_col].astype(int)

print("Original samples:", len(y_real), "class counts:", y_real.value_counts().to_dict())
# augmentation factor per sample
AUG_PER_SAMPLE = 200  # yields larger dataset; reduce if too big
rng = np.random.default_rng(42)
rows_aug = []
for idx, (xrow, yval) in enumerate(zip(X_real.values, y_real.values)):
    # keep original
    rows_aug.append((xrow, yval))
    for k in range(AUG_PER_SAMPLE):
        noise = rng.normal(loc=0.0, scale=0.03, size=xrow.shape)  # 3% noise
        newx = xrow * (1.0 + noise)
        # clamp negatives
        newx = np.maximum(newx, 0.0)
        rows_aug.append((newx, yval))

X_aug = np.vstack([r[0] for r in rows_aug])
y_aug = np.array([r[1] for r in rows_aug])
print("After augmentation:", X_aug.shape, "class balance:", np.bincount(y_aug))

# split and train
X_train, X_val, y_train, y_val = train_test_split(X_aug, y_aug, test_size=0.20, random_state=42, stratify=y_aug)
model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.08, n_jobs=-1, random_state=42, tree_method="hist")
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
predp = model.predict_proba(X_val)[:,1]
pred = (predp >= 0.5).astype(int)
print("Val samples:", len(y_val), "accuracy:", accuracy_score(y_val, pred), "logloss:", log_loss(y_val, predp))
joblib.dump(model, Path(r"D:\major project\stage2_dynamic") / "xgb_dynamic_aug.pkl")
print("Saved xgb_dynamic_aug.pkl")
