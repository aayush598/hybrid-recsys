# API Reference

## Base URL
```
https://api.beautyrec.dev/api/v1
```

## Authentication
```bash
# Get token
curl -X POST https://api.beautyrec.dev/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl https://api.beautyrec.dev/api/v1/recommendations/ \
  -H "Authorization: Bearer <token>"
```

## Endpoints

### Recommendations

#### Get Recommendations
```http
GET /api/v1/recommendations/?user_id=123&n=10&strategy=hybrid
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| user_id | int | required | User ID |
| n | int | 10 | Number of recommendations |
| strategy | string | hybrid | Recommendation strategy |
| diversity | float | 0.3 | Diversity weight |

**Response:**
```json
{
  "recommendations": [
    {
      "item_id": 456,
      "score": 0.95,
      "strategy": "collaborative_filtering",
      "metadata": {
        "title": "The Matrix",
        "genres": ["Action", "Sci-Fi"]
      }
    }
  ],
  "user_id": 123,
  "strategy": "hybrid",
  "latency_ms": 45.2
}
```

#### Get Similar Items
```http
GET /api/v1/recommendations/similar/456?n=10
```

**Response:**
```json
{
  "item_id": 456,
  "similar_items": [
    {
      "item_id": 789,
      "similarity": 0.89,
      "title": "The Matrix Reloaded"
    }
  ]
}
```

### Movies

#### List Movies
```http
GET /api/v1/movies/?page=1&per_page=20&genre=Action&search=matrix
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| per_page | int | 20 | Items per page |
| genre | string | - | Filter by genre |
| search | string | - | Search query |

**Response:**
```json
{
  "movies": [
    {
      "id": 456,
      "title": "The Matrix",
      "genres": ["Action", "Sci-Fi"],
      "year": 1999,
      "rating": 4.5,
      "description": "A computer hacker learns..."
    }
  ],
  "total": 62000,
  "page": 1,
  "per_page": 20,
  "pages": 3100
}
```

#### Get Movie Details
```http
GET /api/v1/movies/456
```

**Response:**
```json
{
  "id": 456,
  "title": "The Matrix",
  "genres": ["Action", "Sci-Fi"],
  "year": 1999,
  "rating": 4.5,
  "description": "A computer hacker learns...",
  "cast": ["Keanu Reeves", "Laurence Fishburne"],
  "similar_items": [789, 101, 234]
}
```

### Users

#### Register User
```http
POST /api/v1/users/
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "user_id": 123,
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### Get User Profile
```http
GET /api/v1/users/123
```

**Response:**
```json
{
  "user_id": 123,
  "username": "john_doe",
  "total_ratings": 150,
  "favorite_genres": ["Action", "Sci-Fi"],
  "recent_activity": [
    {
      "item_id": 456,
      "rating": 5.0,
      "timestamp": "2025-01-01T12:00:00Z"
    }
  ]
}
```

#### Add Rating
```http
POST /api/v1/users/123/ratings
Content-Type: application/json

{
  "item_id": 456,
  "rating": 4.5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Rating added successfully"
}
```

### Health

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "cache": "healthy",
    "ml_models": "healthy"
  }
}
```

#### Metrics
```http
GET /metrics
```

**Response:**
```json
{
  "requests_total": 1234567,
  "requests_per_second": 123.45,
  "avg_latency_ms": 45.2,
  "error_rate": 0.01,
  "cache_hit_rate": 0.95,
  "model_accuracy": 0.38
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request parameters",
  "details": {
    "user_id": "Must be a positive integer"
  }
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "message": "Please provide a valid JWT token"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found",
  "message": "Movie with id 999 does not exist"
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "message": "Please retry after 60 seconds",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred",
  "request_id": "req-abc123"
}
```

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| /recommendations | 100 | 1 minute |
| /movies | 200 | 1 minute |
| /users | 50 | 1 minute |
| /health | Unlimited | - |

## WebSocket

### Connect
```javascript
const ws = new WebSocket('wss://api.beautyrec.dev/ws/recommendations/123');
```

### Receive Updates
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New recommendations:', data.recommendations);
};
```

## References

- OpenAPI Spec: https://api.beautyrec.dev/docs
- Swagger UI: https://api.beautyrec.dev/docs
- ReDoc: https://api.beautyrec.dev/redoc
