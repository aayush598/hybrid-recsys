# Runbook: High Error Rate (> 5%)

**Severity:** SEV-2 (SEV-1 if error rate > 20% or all requests failing)
**Alert:** `beautyrec:http_error_rate_5m > 0.05`
**Dashboards:** Grafana → "BeautyRec / API Health"

## Symptoms

- Alert fires: HTTP 5xx rate over 5 minutes exceeds 5%.
- User reports of failed recommendations, timeouts, or login errors.
- Possible spike in p99 latency alongside the error rate.

## Immediate Actions (first 5 minutes)

1. **Acknowledge the alert** in PagerDuty/ops channel; declare incident if > 10%.
2. **Check the blast radius:**
   ```bash
   # Error rate by status code and route
   kubectl logs -n beautyrec deploy/beautyrec-backend --tail=200 | grep -E '"(5[0-9]{2})"' | tail -50
   ```
3. **Was anything just deployed?**
   ```bash
   kubectl rollout history -n beautyrec deploy/beautyrec-backend
   ```
   If errors started right after a release → **roll back first, investigate later:**
   ```bash
   kubectl rollout undo -n beautyrec deploy/beautyrec-backend
   ```

## Diagnosis

| Error signature | Likely cause | Check |
| --- | --- | --- |
| 500 on `/api/v1/recommendations` | Model load failure / missing artifacts | Pod logs for `ModelNotFound`, artifact mount |
| 502/504 at ingress | Pods not ready or crashing | `kubectl get pods -n beautyrec` — restarts? |
| 503 from backend | DB connection pool exhausted | RDS connections metric, `max_connections` |
| 429/5xx mixed | Redis down (rate limiter/cache) | ElastiCache health, `redis://` connectivity |
| 500 with traceback containing `psycopg` | Database failover in progress | RDS events, failover status |

Useful commands:

```bash
kubectl describe pod -n beautyrec -l app=beautyrec-backend | grep -A5 Events
kubectl top pods -n beautyrec          # OOMKill suspects show high memory then restarts
kubectl get events -n beautyrec --sort-by=.lastTimestamp | tail -20
```

## Remediation

- **CrashLoopBackOff / OOMKilled:** raise memory limits via Helm values and redeploy:
  ```bash
  helm upgrade beautyrec infra/kubernetes/helm/beautyrec \
    --set backend.resources.limits.memory=4Gi
  ```
- **DB pool exhaustion:** restart pods to drain leaked connections, then fix leak;
  consider raising `max_connections` (Terraform `rds` module).
- **Redis unreachable:** verify security groups allow EKS node SG on 6379;
  check ElastiCache failover completed.
- **Bad model artifact:** restore previous version per ADR 005 reload procedure.

## Escalation

- Not mitigated within 15 minutes → page backend on-call lead.
- Data-layer cause → escalate to platform/DBA on-call.
- Suspected upstream provider outage → open vendor ticket, enable degraded mode.

## Post-Incident

- Fill the incident template within 48h; include error-rate graph timeline.
- Add a regression test or alert tuning note so this class of failure is caught earlier.
