#!/usr/bin/env python
# coding: utf-8

"""
links_stage1.py  — Static hybrid trainer
✅ Works with existing feature-only training data
✅ Correct label encoding: 1=fraud, 0=legitimate
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "links_stage1_training_refined.csv"
LABEL = "label_is_phish"

# All features (already in the CSV)
ALL_FEATURES = [
    "domain_age_days", "tld_risk", "url_length", "subdomain_depth", "brand_lev_distance",
    "ssl_valid", "is_http", "query_entropy", "redirect_count",
    "kw_kyc", "kw_verify", "kw_bonus",
    "upi_intent_pay", "upi_intent_collect", "upi_pa_present", "upi_am_present", "upi_amount",
    "vpa_format_valid", "vpa_provider_allow", "vpa_entropy",
    "qr_present", "qr_param_missing_count", "qr_from_shortener",
    "log_domain_age_days", "log_upi_amount", "log_url_length", "log_query_entropy",
    "is_new_domain_30", "is_new_domain_60", "risky_tld_flag", "brand_impersonation",
    "long_url_flag", "deep_subdomain_flag", "http_or_bad_ssl", "has_kyc_or_verify",
    "small_amount_verification", "pay_intent_no_collect", "kyc_on_new_domain"
]

def isolation_forest_scores(iforest, X_scaled: np.ndarray) -> np.ndarray:
    raw = iforest.decision_function(X_scaled)
    ranks = pd.Series(raw).rank(method="average").to_numpy()
    anom = (ranks - ranks.min()) / (ranks.max() - ranks.min())
    return 1.0 - anom

def eval_combo(w_link, t_block, t_ok, xgb_prob, if_score, y_true):
    final = w_link*xgb_prob + (1-w_link)*if_score
    hard = np.where(final >= t_block, 1, np.where(final <= t_ok, 0, -1))
    preds_safety = np.where(hard == -1, 1, hard)
    precA, recA, f1A, _ = precision_recall_fscore_support(y_true, preds_safety, average="binary", zero_division=0)
    preds_strict = np.where(hard == 1, 1, 0)
    precB, recB, f1B, _ = precision_recall_fscore_support(y_true, preds_strict, average="binary", zero_division=0)
    auc = roc_auc_score(y_true, final)
    warn_rate = float(np.mean(hard == -1)); block_rate = float(np.mean(hard == 1))
    return (precA, recA, f1A, precB, recB, f1B, auc, warn_rate, block_rate), hard, final

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"❌ Training data not found: {DATA_PATH}")
    
    df = pd.read_csv(DATA_PATH)
    print(f"✓ Loaded {len(df)} rows")
    print(f"✓ Columns: {df.columns.tolist()[:10]}...")

    if LABEL not in df.columns:
        raise KeyError(f"Label column '{LABEL}' not found")

    # ✅ FIX: Invert backwards labels in CSV
    # Original CSV: 0=legit, 1=fraud (backwards!)
    # We need: 0=legit, 1=fraud (standard)
    original_dist = df[LABEL].value_counts().to_dict()
    print(f"\nOriginal CSV distribution: {original_dist}")
    print("Note: CSV uses backwards convention (0=good quality, 1=bad quality)")
    
    # Flip to standard ML convention: 0=legit, 1=fraud
    df[LABEL] = 1 - df[LABEL]
    
    new_dist = df[LABEL].value_counts().to_dict()
    print(f"After correction: {new_dist}")
    print("✅ Fixed: 0=legitimate, 1=fraud (standard)\n")

    # Load features
    X = df[ALL_FEATURES].astype(float)
    y = df[LABEL].astype(int).to_numpy()
    
    print(f"✓ Features: {X.shape[1]} columns")
    print(f"✓ Samples: legit={np.sum(y==0)}, fraud={np.sum(y==1)}")
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    # XGB with class balancing
    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    scale_pos_weight = max(1.0, neg / max(1, pos))
    
    print(f"\n🔧 Training XGBoost (scale_pos_weight={scale_pos_weight:.2f})...")
    xgb = XGBClassifier(
        n_estimators=450, max_depth=6, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9,
        reg_lambda=1.5, reg_alpha=0.1, min_child_weight=2, random_state=42, n_jobs=-1,
        eval_metric="auc", scale_pos_weight=scale_pos_weight, tree_method="hist"
    )
    xgb.fit(X_train, y_train)
    xgb_val_prob = xgb.predict_proba(X_val)[:,1]
    
    print(f"✓ XGBoost trained (train_score={xgb.score(X_train, y_train):.3f})")

    # Isolation Forest (train on legitimate samples only)
    print(f"\n🔧 Training Isolation Forest...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train.values)
    X_val_scaled = scaler.transform(X_val.values)
    
    benign_mask = (y_train == 0)
    print(f"   Training on {benign_mask.sum()} legitimate samples...")
    iforest = IsolationForest(n_estimators=350, contamination=0.20, max_features=1.0, random_state=42, n_jobs=-1)
    iforest.fit(X_train_scaled[benign_mask])
    if_val = isolation_forest_scores(iforest, X_val_scaled)
    
    print(f"✓ Isolation Forest trained")

    # Threshold search
    print(f"\n🔍 Searching for optimal thresholds...")
    best, best_params = None, None
    for w in [0.8, 0.85, 0.9]:  # Higher weight on XGB
        for t_block in np.linspace(0.5, 0.7, 9):
            for t_ok in np.linspace(0.2, 0.4, 9):
                if t_ok >= (t_block - 0.15):
                    continue
                metrics, hard_preds, final = eval_combo(w, t_block, t_ok, xgb_val_prob, if_val, y_val)
                precA, recA, f1A, precB, recB, f1B, auc, warn_rate, block_rate = metrics
                
                score_tuple = (
                    recA >= 0.80,  # Must catch 80%+ fraud
                    precB,          # Maximize precision when blocking
                    -abs(warn_rate - 0.25),  # Target 25% warn rate
                    auc
                )
                
                if (best is None) or (score_tuple > best):
                    best = score_tuple
                    best_params = {
                        "w_link": float(w), "t_block": float(t_block), "t_ok": float(t_ok),
                        "metrics": {
                            "safety_view": {"precision": float(precA), "recall": float(recA), "f1": float(f1A)},
                            "strict_view": {"precision": float(precB), "recall": float(recB), "f1": float(f1B)},
                            "auc": float(auc), "warn_rate": float(warn_rate), "block_rate": float(block_rate)
                        }
                    }

    w = best_params["w_link"]
    t_block = best_params["t_block"]
    t_ok = best_params["t_ok"]
    
    metrics, hard_preds, final = eval_combo(w, t_block, t_ok, xgb_val_prob, if_val, y_val)
    precA, recA, f1A, precB, recB, f1B, auc, warn_rate, block_rate = metrics

    print("\n" + "="*60)
    print("VALIDATION METRICS")
    print("="*60)
    print(f"Safety view:  precision={precA:.3f} recall={recA:.3f} f1={f1A:.3f}")
    print(f"Strict view:  precision={precB:.3f} recall={recB:.3f} f1={f1B:.3f}")
    print(f"AUC={auc:.3f} | WARN={warn_rate:.3f} | BLOCK={block_rate:.3f}")
    print(f"Thresholds: w={w:.2f}, t_block={t_block:.2f}, t_ok={t_ok:.2f}")

    preds_safety = np.where(hard_preds == -1, 1, hard_preds)
    cm = confusion_matrix(y_val, preds_safety)
    print("\nConfusion matrix (Safety view):")
    print("                Predicted")
    print("                Legit  Fraud")
    print(f"Actual Legit   {cm[0][0]:5d}  {cm[0][1]:5d}")
    print(f"Actual Fraud   {cm[1][0]:5d}  {cm[1][1]:5d}")

    # Save models
    out_dir = ROOT / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(xgb, out_dir/"xgb_static.pkl")
    joblib.dump(iforest, out_dir/"iforest_static.pkl")
    joblib.dump(scaler, out_dir/"if_scaler.pkl")
    
    with open(out_dir/"ensemble_config.json", "w") as f:
        json.dump({
            "feature_list": ALL_FEATURES,
            "ensemble": {"w_link": w, "t_block": t_block, "t_ok": t_ok},
            "val_metrics": best_params["metrics"],
            "label_encoding": "1=fraud, 0=legitimate (inverted during training)"
        }, f, indent=2)

    print(f"\n✅ Models saved to {out_dir}/")
    print("✅ TRAINING COMPLETE!")

if __name__ == "__main__":
    main()
