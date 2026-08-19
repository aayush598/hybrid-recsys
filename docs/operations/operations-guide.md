# Operations Guide

## Monitoring & Observability

### Metrics Collection (Prometheus)
- **Request Rate**: requests/second
- **Error Rate**: errors/total requests
- **Latency**: P50, P95, P99 response times
- **ML Metrics**: model accuracy, coverage, diversity
- **Infrastructure**: CPU, memory, disk usage

### Dashboards (Grafana)
- **System Overview**: Request rate, error rate, latency
- **ML Performance**: Model accuracy, coverage, diversity
- **Infrastructure**: CPU, memory, disk, network
- **Business**: User engagement, conversion rates

### Alerting Rules
| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | error_rate > 5% | Critical |
| HighLatency | p95_latency > 500ms | Warning |
| ModelDrift | ndcg_drop > 10% | Critical |
| ServiceDown | health_check_failed | Critical |
| DiskSpace | disk_usage > 85% | Warning |

## Incident Response

### Severity Levels
| Level | Response Time | Examples |
|-------|--------------|---------|
| P0 Critical | 1 hour | Service down, data breach |
| P1 High | 4 hours | Authentication failure |
| P2 Medium | 24 hours | Performance degradation |
| P3 Low | 1 week | Minor bug |

### Runbooks

#### Service Down
1. Check pod status: `kubectl get pods -n beautyrec`
2. Check logs: `kubectl logs -f deployment/beautyrec-backend -n beautyrec`
3. Check resource usage: `kubectl top pods -n beautyrec`
4. Restart if needed: `kubectl rollout restart deployment/beautyrec-backend -n beautyrec`
5. Escalate if not resolved in 30 minutes

#### High Latency
1. Check Prometheus metrics for latency breakdown
2. Identify slow endpoint
3. Check database query performance
4. Check cache hit rate
5. Scale up if needed: `kubectl scale deployment beautyrec-backend --replicas=5 -n beautyrec`

#### Model Drift
1. Check model monitoring dashboard
2. Review drift detection alerts
3. Trigger model retraining if needed
4. Compare old vs new model performance
5. Roll back if new model is worse

## Capacity Planning

### Resource Usage Patterns
- **Peak Hours**: 7PM-11PM (3x normal traffic)
- **Weekends**: 2x weekday traffic
- **Holidays**: 5x normal traffic

### Scaling Thresholds
| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| CPU | >70% | <30% |
| Memory | >80% | <40% |
| Request Rate | >80% capacity | <30% capacity |

### Cost Optimization
- **Spot Instances**: 70% cost reduction for batch jobs
- **Reserved Instances**: 40% cost reduction for base load
- **Auto-scaling**: Right-size based on actual usage

## Backup & Recovery

### Database Backups
- **Daily**: Full backup to S3
- **Hourly**: Incremental backups
- **Retention**: 30 days daily, 12 months monthly

### Model Artifacts
- **Versioned**: All model versions stored in S3
- **Retention**: Last 10 versions
- **Archive**: Older versions to Glacier

### Recovery Procedures
```bash
# Restore database from backup
aws s3 cp s3://beautyrec-backups/db/latest.sql.gz .
gunzip latest.sql.gz
psql -h prod-db -U admin -d beautyrec < latest.sql

# Restore model artifacts
aws s3 sync s3://beautyrec-models/prod/ /app/models/
```

## Performance Tuning

### Database Optimization
- **Indexes**: User ID, item ID, timestamp
- **Connection Pooling**: 20 connections
- **Query Optimization**: EXPLAIN ANALYZE for slow queries

### Cache Optimization
- **Hit Rate Target**: >95%
- **TTL Tuning**: Based on data freshness requirements
- **Eviction Policy**: LRU with size limits

### ML Optimization
- **Batch Inference**: Process multiple users at once
- **Model Quantization**: INT8 for 2x speedup
- **Index Optimization**: IVF with appropriate nprobe

## Security Operations

### Access Reviews
- **Quarterly**: Review all access logs
- **Monthly**: Rotate API keys
- **Daily**: Monitor failed login attempts

### Vulnerability Management
- **Weekly**: Run dependency scans
- **Monthly**: Penetration testing
- **Quarterly**: Security audit

## References

- SRE Workbook: https://sre.google/workbook/table-of-contents/
- Prometheus: https://prometheus.io/docs/
- Grafana: https://grafana.com/docs/
