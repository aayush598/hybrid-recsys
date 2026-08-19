# Data Engineering Guide

## Data Collection

### Explicit Feedback
- **Ratings**: 0.5-5.0 star ratings (MovieLens dataset)
- **Reviews**: Free-text reviews (future enhancement)
- **Likes/Dislikes**: Binary feedback (future)

### Implicit Feedback
- **Views**: Number of times a user viewed an item
- **Click-through**: Click patterns on recommendations
- **Dwell Time**: Time spent viewing an item
- **Add to List**: "Want to see" / "Already seen" actions

### Behavioral Data
- **Session Data**: Login/logout timestamps, navigation paths
- **Search Queries**: What users search for
- **Filter Usage**: Which filters users apply

### Contextual Data
- **Time of Day**: Morning/afternoon/evening patterns
- **Day of Week**: Weekend vs weekday behavior
- **Device Type**: Mobile vs desktop preferences
- **Location**: Geographic preferences (future)

## Data Preprocessing

### Data Cleaning
```python
# Remove duplicates
df = df.drop_duplicates(subset=["user_id", "item_id"])

# Remove invalid ratings
df = df[(df["rating"] >= 0.5) & (df["rating"] <= 5.0)]

# Handle missing values
df["rating"] = df["rating"].fillna(df["rating"].median())
```

### Missing Value Treatment
- **Ratings**: Use median rating per item
- **Genres**: Default to "Unknown" category
- **Timestamps**: Use item creation date
- **User Features**: Use population median/mode

### Outlier Detection
```python
# IQR method for rating outliers
Q1 = df["rating"].quantile(0.25)
Q3 = df["rating"].quantile(0.75)
IQR = Q3 - Q1
df = df[(df["rating"] >= Q1 - 1.5 * IQR) & (df["rating"] <= Q3 + 1.5 * IQR)]
```

### Feature Scaling
```python
# Min-Max scaling for user features
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
user_features[["rating_count", "avg_rating"]] = scaler.fit_transform(
    user_features[["rating_count", "avg_rating"]]
)
```

## Data Storage

### Relational (PostgreSQL/SQLite)
- User profiles, interactions, metadata
- ACID compliance for write-heavy workloads
- Indexing for fast lookups

### Vector (FAISS)
- Item embeddings for similarity search
- Memory-mapped for large indices
- IVF/PQ for sub-linear search

### Cache (Redis)
- Hot recommendations (top-10 per user)
- Session data
- Rate limiting counters

### Columnar (Parquet)
- Training data (compressed, fast column access)
- Feature store offline store
- Historical analytics

## Feature Engineering

### User Features
- **Aggregate**: Rating count, average rating, rating variance
- **Temporal**: Last active, session frequency, recency
- **Behavioral**: Genre preferences, viewing patterns
- **Embedding**: User latent factors from matrix factorization

### Item Features
- **Aggregate**: Average rating, rating count, popularity
- **Content**: Genre distribution, description embedding
- **Temporal**: Release year, trending score
- **Embedding**: Item latent factors from matrix factorization

### Interaction Features
- **Rating**: Explicit user-item rating
- **Temporal**: Rating timestamp, recency weight
- **Context**: Device, time of day, session ID

### Cross Features
- **User-Item**: Cosine similarity of user/item embeddings
- **User-Genre**: Genre preference alignment
- **Item-Item**: Co-occurrence patterns

## Data Pipelines

### Batch Pipeline (Daily)
```
Raw Data → Validation → Cleaning → Feature Engineering → Feature Store
```

### Real-time Pipeline (Streaming)
```
Event Stream → Validation → Feature Extraction → Online Store → Inference
```

### Pipeline Orchestration
- **Scheduled**: Daily batch jobs (cron-like)
- **Triggered**: Real-time events (webhooks)
- **Manual**: Ad-hoc retraining (API call)

## Data Quality Monitoring

### Validation Rules
- **Schema**: Column types, required fields
- **Range**: Rating bounds, timestamp validity
- **Uniqueness**: No duplicate user-item pairs
- **Completeness**: Missing data threshold (<5%)

### Quality Metrics
- **Freshness**: Data staleness (hours since last update)
- **Volume**: Expected vs actual row counts
- **Distribution**: Feature distribution drift
- **Accuracy**: Ground truth validation (sampling)

## References

- "Fundamentals of Data Engineering" by Joe Reis
- "Designing Machine Learning Systems" by Chip Huyen
- Netflix: "Data Engineering at Netflix" (2020)
