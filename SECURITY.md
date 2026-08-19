# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x | :white_check_mark: |
| < 1.0 | :x: |

## Reporting a Vulnerability

If you discover a security vulnerability within BeautyRec, please send an email to security@beautyrec.dev. All security vulnerabilities will be promptly addressed.

**Please do NOT report security vulnerabilities through public GitHub issues.**

### What to include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline:
- **Acknowledgment:** Within 24 hours
- **Initial assessment:** Within 48 hours
- **Fix release:** Within 7 days for critical, 30 days for others

## Security Measures

### Authentication
- JWT tokens with short expiration (60 minutes)
- Secure password hashing (bcrypt)
- Rate limiting on auth endpoints

### API Security
- CORS restricted to known origins
- Input validation on all endpoints
- Request size limits (10MB max)
- Security headers (CSP, HSTS, X-Frame-Options)

### Data Security
- No secrets in code (environment variables only)
- Database encryption at rest
- HTTPS in production
- Audit logging for sensitive operations

### Infrastructure
- Docker images scanned for vulnerabilities
- Dependencies audited regularly
- Network policies in Kubernetes
- Secrets managed via Vault/Secrets Manager

## Best Practices for Contributors

1. Never commit secrets, API keys, or credentials
2. Use environment variables for configuration
3. Validate and sanitize all user inputs
4. Follow OWASP Top 10 guidelines
5. Run `bandit` security scanner before submitting PRs
