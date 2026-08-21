# Runbook: Capacity Planning & Scaling Decisions

**Cadence:** Review monthly; ad-hoc when traffic grows > 20% MoM
**Owner:** Platform on-call with backend lead sign-off

## Objectives

- Keep p95 recommendation latency < 100 ms and error rate < 0.5% at peak.
- Maintain headroom: steady-state CPU < 60% of requests, DB connections < 70%.
- Scale proactively before marketing campaigns or seasonal peaks.

## Key Capacity Signals

| Signal | Source | Warning threshold | Action threshold |
| --- | --- | --- | --- |
| Backend CPU utilization | HPA / Prometheus | 60% sustained 1h | HPA max reached |
| Pod memory | `kubectl top pods` | 75% of limit | OOMKill risk |
| RDS CPU | CloudWatch | 60% sustained | Vertical resize |
| DB connections | `pg_stat_activity` | 70% of max_connections | Pool tuning / PgBouncer |
| Redis memory | ElastiCache metrics | 70% of node memory | Node type up |
| Disk (RDS) | FreeStorageSpace | < 25% free | Storage autoscaling check |
| Ingress RPS vs limit | nginx metrics | 80% of rate-limit budget | Raise limits |

## Scaling Levers (cheapest first)

1. **HPA bounds** — current: min 2, max 10, target CPU 70%
   (`infra/kubernetes/helm/beautyrec/values.yaml`).
   ```bash
   helm upgrade beautyrec infra/kubernetes/helm/beautyrec \
     --set backend.autoscaling.maxReplicas=15
   ```
2. **EKS node group** — scale desired/max in the environment's Terraform:
   ```bash
   # infra/terraform/environments/production/main.tf → module "eks"
   terraform -chdir=infra/terraform/environments/production apply
   ```
3. **Vertical pod sizing** — raise requests/limits if per-pod saturation, not load.
4. **RDS vertical resize** — instance class change (Multi-AZ failover makes this
   low-downtime); plan for a maintenance window anyway.
5. **Read replica** — add one (`create_read_replica = true`) when read-heavy
   queries (analytics, catalog) compete with transactional writes.
6. **Redis node type** — memory-bound cache growth is the usual trigger.

## Forecasting Method

1. Pull 30-day peak RPS and p95 latency from Grafana.
2. Compute per-pod capacity: `peak_rps_at_70pct_cpu / replica_count`.
3. Required replicas at forecast peak = `forecast_peak_rps / per_pod_capacity × 1.3`.
4. Verify EKS nodes can host that many pods (CPU/memory sums + daemonsets).
5. Confirm DB connection math: `replicas × pool_size ≤ 0.7 × max_connections`.

## Pre-Launch Checklist (campaigns/product launches)

- [ ] Load test at 2× forecast peak (`backend/tests/load`)
- [ ] HPA max raised for the event window
- [ ] RDS/Redis headroom verified against the table above
- [ ] Runbook owners briefed; on-call rotation confirmed
- [ ] Rollback plan: revert Helm/Terraform values documented in the change ticket

## Cost Guardrails

- Staging runs spot nodes, single-AZ RDS, single-node Redis — keep it that way.
- Review NAT gateway count (per-AZ only in production).
- Set AWS budgets alert at 80% of monthly plan; investigate before 100%.
