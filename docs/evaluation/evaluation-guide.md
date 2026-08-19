# Evaluation Guide

## Offline Metrics

### Ranking Metrics

#### Precision@K
```python
def precision_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    """Fraction of top-K recommendations that are relevant."""
    top_k = recommended[:k]
    hits = len(set(top_k) & relevant)
    return hits / k
```

#### Recall@K
```python
def recall_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    """Fraction of relevant items found in top-K recommendations."""
    top_k = recommended[:k]
    hits = len(set(top_k) & relevant)
    return hits / len(relevant) if relevant else 0.0
```

#### NDCG@K (Normalized Discounted Cumulative Gain)
```python
def ndcg_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    """Position-aware metric measuring ranking quality."""
    dcg = sum(
        1 / np.log2(i + 2)
        for i, item in enumerate(recommended[:k])
        if item in relevant
    )
    ideal_dcg = sum(1 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0
```

#### MAP@K (Mean Average Precision)
```python
def average_precision(recommended: List[int], relevant: Set[int], k: int) -> float:
    """Average precision across all relevant items in top-K."""
    hits = 0
    sum_precisions = 0.0
    for i, item in enumerate(recommended[:k]):
        if item in relevant:
            hits += 1
            sum_precisions += hits / (i + 1)
    return sum_precisions / len(relevant) if relevant else 0.0
```

### Beyond-Accuracy Metrics

#### Coverage
```python
def catalog_coverage(all_recommendations: List[List[int]], n_items: int) -> float:
    """Fraction of items ever recommended."""
    recommended_items = set(item for recs in all_recommendations for item in recs)
    return len(recommended_items) / n_items
```

#### Diversity (Intra-List Diversity)
```python
def intra_list_diversity(recommendations: List[int], embeddings: Dict[int, np.ndarray]) -> float:
    """Average pairwise distance between recommended items."""
    if len(recommendations) < 2:
        return 0.0
    
    embs = [embeddings[item] for item in recommendations if item in embeddings]
    n = len(embs)
    total_distance = 0
    
    for i in range(n):
        for j in range(i + 1, n):
            similarity = cosine_similarity(embs[i], embs[j])
            total_distance += 1 - similarity
    
    return total_distance / (n * (n - 1) / 2)
```

#### Novelty
```python
def novelty(recommendations: List[int], item_popularity: Dict[int, int]) -> float:
    """Average information content of recommended items."""
    total_users = sum(item_popularity.values())
    novelties = []
    
    for item in recommendations:
        pop = item_popularity.get(item, 0) / total_users
        if pop > 0:
            novelties.append(-np.log2(pop))
    
    return np.mean(novelties) if novelties else 0.0
```

## Online Metrics

### Click-Through Rate (CTR)
```python
def ctr(clicks: int, impressions: int) -> float:
    """Click-through rate."""
    return clicks / impressions if impressions > 0 else 0.0
```

### Conversion Rate
```python
def conversion_rate(conversions: int, clicks: int) -> float:
    """Fraction of clicks that lead to conversion."""
    return conversions / clicks if clicks > 0 else 0.0
```

### Engagement Metrics
- **Dwell Time**: Time spent viewing recommended item
- **Interaction Rate**: Ratings, likes, adds to list
- **Session Duration**: Time spent in app after seeing recommendations

## Evaluation Framework

### Offline Evaluation Pipeline
```python
def evaluate_model(
    model: RecommendationModel,
    test_data: List[Tuple[int, List[int], int]],
    k_values: List[int] = [5, 10, 20],
) -> Dict[str, float]:
    """Complete offline evaluation."""
    metrics = {}
    
    for k in k_values:
        precisions = []
        recalls = []
        ndcgs = []
        maps = []
        
        for user_id, history, test_item in test_data:
            # Get recommendations
            recs = model.recommend(user_id, n=k + 10)
            relevant = {test_item}
            
            # Calculate metrics
            precisions.append(precision_at_k(recs, relevant, k))
            recalls.append(recall_at_k(recs, relevant, k))
            ndcgs.append(ndcg_at_k(recs, relevant, k))
            maps.append(average_precision(recs, relevant, k))
        
        metrics[f"precision@{k}"] = np.mean(precisions)
        metrics[f"recall@{k}"] = np.mean(recalls)
        metrics[f"ndcg@{k}"] = np.mean(ndcgs)
        metrics[f"map@{k}"] = np.mean(maps)
    
    return metrics
```

### A/B Testing Framework
```python
class ABTest:
    """A/B test for comparing recommendation strategies."""
    
    def __init__(self, name: str, traffic_split: float = 0.5):
        self.name = name
        self.traffic_split = traffic_split
        self.control_metrics: List[float] = []
        self.treatment_metrics: List[float] = []
    
    def assign_group(self, user_id: int) -> str:
        """Deterministically assign user to control/treatment."""
        return "treatment" if hash(str(user_id)) % 100 < self.traffic_split * 100 else "control"
    
    def record_metric(self, group: str, metric_value: float):
        """Record a metric value for a group."""
        if group == "control":
            self.control_metrics.append(metric_value)
        else:
            self.treatment_metrics.append(metric_value)
    
    def get_results(self) -> Dict[str, Any]:
        """Get statistical comparison results."""
        from scipy import stats
        
        control_mean = np.mean(self.control_metrics) if self.control_metrics else 0
        treatment_mean = np.mean(self.treatment_metrics) if self.treatment_metrics else 0
        
        if self.control_metrics and self.treatment_metrics:
            t_stat, p_value = stats.ttest_ind(self.control_metrics, self.treatment_metrics)
        else:
            t_stat, p_value = 0, 1
        
        return {
            "control_mean": control_mean,
            "treatment_mean": treatment_mean,
            "lift": (treatment_mean - control_mean) / control_mean if control_mean > 0 else 0,
            "p_value": p_value,
            "significant": p_value < 0.05,
        }
```

## Bias & Fairness Evaluation

### Popularity Bias
```python
def popularity_bias(recommendations: List[int], item_popularity: Dict[int, int]) -> float:
    """Fraction of popular items in recommendations."""
    threshold = np.percentile(list(item_popularity.values()), 80)
    popular = sum(1 for item in recommendations if item_popularity.get(item, 0) >= threshold)
    return popular / len(recommendations) if recommendations else 0
```

### Fairness Across Groups
```python
def demographic_parity(
    recommendations: Dict[str, List[int]],
    user_groups: Dict[str, str],
) -> float:
    """Equal recommendation quality across user groups."""
    group_scores = defaultdict(list)
    
    for user_id, recs in recommendations.items():
        group = user_groups.get(user_id, "unknown")
        group_scores[group].append(len(recs))
    
    if len(group_scores) < 2:
        return 1.0
    
    means = {g: np.mean(scores) for g, scores in group_scores.items()}
    return min(means.values()) / max(means.values())
```

## Benchmark Datasets

| Dataset | Users | Items | Interactions | Domain |
|---------|-------|-------|--------------|--------|
| MovieLens 25M | 162K | 62K | 25M | Movies |
| Amazon Reviews | 233M | 37M | 233M | E-commerce |
| Netflix Prize | 480K | 18K | 100M | Movies |
| Spotify Million | 2M | 48M | 20M | Music |

## References

- "Evaluation of Recommender Systems" by Herlocker et al.
- "Offline Evaluation of Recommender Systems" bynkfke
- Netflix: "Recommendations: Benefits, Evaluation, and Impacts" (2022)
