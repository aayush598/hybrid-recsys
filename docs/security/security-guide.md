# Security Guide

## Authentication & Authorization

### JWT Authentication
- **Token Type**: Bearer JWT
- **Expiration**: 60 minutes (access), 7 days (refresh)
- **Signing Algorithm**: RS256 (RSA + SHA-256)
- **Claims**: user_id, role, exp, iat, jti

### Token Flow
```
1. Client → POST /api/v1/auth/login {email, password}
2. Server → Validate credentials, generate JWT
3. Client → Store JWT (httpOnly cookie or memory)
4. Client → Authorization: Bearer <token>
5. Server → Validate JWT, extract user_id
```

### Role-Based Access Control (RBAC)
| Role | Permissions |
|------|-----------|
| viewer | Read recommendations, view profiles |
| analyst | Read all data, run reports |
| engineer | Read/write data, manage models |
| admin | Full system access |

## API Security

### Rate Limiting
- **Sliding Window**: 100 requests/minute per user
- **Token Bucket**: 10 tokens/second, burst of 50
- **IP-based**: 1000 requests/minute per IP (unauthenticated)

### Input Validation
```python
# Pydantic schemas enforce strict validation
class RatingRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    item_id: int = Field(..., ge=1)
    rating: float = Field(..., ge=0.5, le=5.0)
```

### Security Headers
```
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

### CORS Policy
```python
ALLOWED_ORIGINS = [
    "https://beautyrec.dev",
    "https://www.beautyrec.dev",
    "http://localhost:3000",  # Development only
]
```

## Data Security

### Encryption at Rest
- **Database**: AES-256 (PostgreSQL TDE)
- **S3 Buckets**: SSE-KMS with customer-managed keys
- **FAISS Indices**: Encrypted at rest (LUKS for local)

### Encryption in Transit
- **Client → Server**: TLS 1.3 (HTTPS only)
- **Service → Service**: mTLS (mutual TLS)
- **Database**: SSL/TLS required

### Secrets Management
```python
# Environment variables (never in code)
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
REDIS_URL = os.getenv("REDIS_URL")

# Kubernetes secrets
apiVersion: v1
kind: Secret
metadata:
  name: beautyrec-secrets
type: Opaque
data:
  database-url: <base64-encoded>
```

## PII Handling

### Classification
| Field | Level | Handling |
|-------|-------|----------|
| email | Restricted | Hashed, never logged |
| user_id | Internal | Pseudonymized in logs |
| ip_address | Confidential | Anonymized (last octet zeroed) |
| age | Internal | Generalized to ranges |
| rating | Public | No restrictions |

### GDPR Compliance
- **Right to Access**: `GET /api/v1/users/{id}/data`
- **Right to Erasure**: `DELETE /api/v1/users/{id}`
- **Data Portability**: JSON export format
- **Consent Tracking**: Opt-in timestamp recorded

## Vulnerability Management

### Dependency Scanning
```bash
# Python
pip-audit
safety check

# npm
npm audit
```

### Static Analysis
```bash
# Bandit (security linter)
bandit -r backend/app

# Semgrep
semgrep --config=p/python backend/
```

### Container Scanning
```bash
# Trivy
trivy image beautyrec-backend:latest

# Snyk
snyk container test beautyrec-backend:latest
```

## Incident Response

### Severity Levels
| Level | Response Time | Examples |
|-------|--------------|---------|
| P0 Critical | 1 hour | Data breach, service down |
| P1 High | 4 hours | Authentication bypass |
| P2 Medium | 24 hours | Rate limiting bypass |
| P3 Low | 1 week | Minor information leak |

### Response Steps
1. **Detect**: Automated alerts + manual reports
2. **Triage**: Assess severity and impact
3. **Contain**: Isolate affected systems
4. **Eradicate**: Fix root cause
5. **Recover**: Restore service
6. **Learn**: Post-incident review

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- NIST Cybersecurity Framework
- GDPR: https://gdpr.eu/
