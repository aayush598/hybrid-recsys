# Runbook: Model Quality Degradation

**Severity:** SEV-2 (SEV-3 if degradation is gradual and within tolerance)
**Alerts:** `beautyrec:model_ndcg_drop_24h`, `beautyrec:ctr_below_baseline`
**Dashboards:** Grafana → "BeautyRec / Model Quality", MLflow experiment tracking

## Symptoms

- Offline metrics drop: NDCG@10 / Recall@10 below baseline by > 5% relative.
- Online signals decay: CTR, add-to-cart rate, or conversion below rolling baseline.
- Data drift alarms: feature distribution shift beyond PSI threshold.
- User complaints of irrelevant or repetitive recommendations.

## Immediate Actions

1. **Confirm it is real, not a metric bug:**
   - Check evaluation pipeline ran to completion (no partial eval artifacts).
   - Compare against the same evaluation window last week (weekday/weekend effects).
2. **Identify which model version is serving:**
   ```bash
   kubectl exec -n beautyrec deploy/beautyrec-backend -- \
     curl -s localhost:8000/api/v1/admin/model-info
   ```
3. **Check for correlated events:** new release? catalog bulk import?
   tracking schema change? traffic mix shift (campaign traffic)?

## Diagnosis Decision Tree

```
Metrics dropped after retrain?
├── YES → suspect training data / hyperparameters
│     ├── Compare training data snapshot vs previous run (row counts, null rates)
│     ├── Check for label leakage fix or interaction-log schema change
│     └── Roll back to previous model version (see Remediation)
└── NO  → suspect drift or serving issue
      ├── Feature drift? → inspect PSI report per feature
      ├── Serving errors on rec endpoints? → see high-error-rate.md runbook
      └── Catalog change? → verify embeddings cover new SKUs (cold-start path)
```

## Remediation

### Roll back to the previous model version

1. Locate the last known-good version in the model registry (MLflow).
2. Repoint the active alias and trigger an atomic reload:
   ```bash
   kubectl exec -n beautyrec deploy/beautyrec-backend -- \
     curl -X POST localhost:8000/api/v1/admin/models/reload -H 'Content-Type: application/json' \
       -d '{"version": "<last-known-good>"}'
   ```
3. Verify online metrics recover within 30–60 minutes.

### Retrain with corrected inputs

```bash
# From the backend workspace
python -m ml.pipelines.train --config configs/training/default.yaml
```

- Validate offline metrics beat the *currently serving* version before promotion.
- Promote only if NDCG@10 ≥ baseline − 2% and no guardrail regression.

### Drift-driven fixes

- Refresh feature statistics and retrain; extend drift monitors to the shifted features.
- If catalog churn is the cause, shorten the content-index refresh interval.

## Prevention

- Keep champion/challenger evaluation in CI for every training run.
- Alert thresholds: warn at 3% relative NDCG drop, page at 7%.
- Schedule weekly DR-style drill: restore latest model backup and evaluate.

## Escalation

- No root cause within 4 hours → escalate to ML lead.
- Sustained CTR loss > 10% for a full day → notify product owner; consider
  falling back to trending-only recommendations as a safe default.
