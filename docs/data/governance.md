# Data Governance Guide

## Data Governance Framework

BeautyRec implements a comprehensive data governance framework ensuring data quality, compliance, and usability.

## Data Catalog

### Metadata Schema
```python
@dataclass
class DatasetMetadata:
    name: str
    description: str
    owner: str
    domain: str
    sensitivity_level: str  # public, internal, confidential, restricted
    freshness: str  # real-time, hourly, daily, weekly
    retention_days: int
    schema_version: str
    tags: List[str]
    lineage: DataLineage
```

### Dataset Registry
| Dataset | Owner | Sensitivity | Retention | Freshness |
|---------|-------|-------------|-----------|-----------|
| Users | Data Team | Confidential | 365 days | Real-time |
| Ratings | Data Team | Internal | 365 days | Real-time |
| Movies | Content Team | Public | Unlimited | Daily |
| Features | ML Team | Internal | 90 days | Hourly |
| Recommendations | ML Team | Internal | 30 days | Real-time |

## Data Lineage

### Lineage Tracking
```python
@dataclass
class DataLineage:
    source: str
    transformation: str
    destination: str
    timestamp: datetime
    version: str
    dependencies: List[str]
```

### Lineage Graph
```
MovieLens CSV → ETL Pipeline → Database → Feature Engineering → FAISS Index
                ↓                                         ↓
         Data Validation                          Model Training
                ↓                                         ↓
         Quality Reports                        Trained Models
```

## Data Quality Standards

### Quality Dimensions
1. **Accuracy**: Data correctly represents real-world entities
2. **Completeness**: All required data is present
3. **Consistency**: Data is uniform across systems
4. **Timeliness**: Data is available when needed
5. **Validity**: Data conforms to defined formats
6. **Uniqueness**: No duplicate records

### Quality Rules
```python
QUALITY_RULES = {
    "ratings": {
        "rating_range": (0.5, 5.0),
        "user_id_exists": True,
        "item_id_exists": True,
        "timestamp_valid": True,
        "no_duplicates": True,
        "completeness_threshold": 0.95,
    },
    "users": {
        "user_id_unique": True,
        "age_range": (0, 150),
        "gender_valid": ["M", "F", "Other"],
    },
}
```

### Quality Monitoring
- **Daily Reports**: Automated quality checks
- **Alerts**: Threshold violations (completeness <95%)
- **Dashboards**: Quality metrics visualization
- **Trend Analysis**: Quality over time

## Data Retention Policies

### Retention Schedule
| Data Type | Retention | Archive | Delete |
|-----------|-----------|---------|--------|
| User Profiles | 3 years | 7 years | After 10 years |
| Ratings | 3 years | 7 years | After 10 years |
| Recommendations | 30 days | 90 days | After 180 days |
| Logs | 30 days | 90 days | After 180 days |
| Features | 90 days | 1 year | After 2 years |

### Archival Strategy
- **Hot**: Last 30 days (fast access)
- **Warm**: 30-90 days (slower access)
- **Cold**: 90+ days (archive storage)
- **Delete**: After retention period

## PII Handling

### PII Classification
| Field | Classification | Handling |
|-------|---------------|----------|
| user_id | Internal | Hashing optional |
| email | Restricted | Encryption at rest |
| ip_address | Confidential | Anonymization |
| age | Internal | Generalization |
| gender | Internal | Optional collection |
| location | Confidential | Anonymization |

### PII Protection
```python
# Pseudonymization
def pseudonymize_email(email: str) -> str:
    return hash(email) + "@anonymized.com"

# Generalization
def generalize_age(age: int) -> str:
    if age < 18: return "under_18"
    elif age < 30: return "18-29"
    elif age < 50: return "30-49"
    else: return "50+"

# K-Anonymity
def k_anonymize(data: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    # Group by quasi-identifiers, suppress groups < k
    pass
```

### GDPR Compliance
- **Right to Access**: Export user data (API endpoint)
- **Right to Erasure**: Delete user data (API endpoint)
- **Right to Portability**: JSON export format
- **Data Minimization**: Collect only necessary fields
- **Consent Management**: Explicit opt-in tracking

## Data Access Controls

### Role-Based Access Control (RBAC)
| Role | Access Level |
|------|-------------|
| Viewer | Read-only access to public data |
| Analyst | Read access to internal data |
| Engineer | Read/write access to internal data |
| Admin | Full access to all data |

### Access Logging
```python
@dataclass
class AccessLog:
    user_id: int
    dataset: str
    action: str  # read, write, delete
    timestamp: datetime
    ip_address: str
    user_agent: str
```

## Data Compliance

### Regulatory Compliance
- **GDPR**: EU data protection regulation
- **CCPA**: California consumer privacy act
- **HIPAA**: Health information (future if health data)
- **SOC 2**: Security and compliance framework

### Compliance Monitoring
- **Access Reviews**: Quarterly access audits
- **Data Mapping**: Know where data lives
- **Impact Assessments**: For new data processing
- **Breach Notification**: 72-hour notification requirement

## References

- "Data Governance: How to Design, Deploy, and Sustain an Effective Data Governance Program" by John Ladley
- GDPR: https://gdpr.eu/
- DAMA-DMBOK: Data Management Body of Knowledge
