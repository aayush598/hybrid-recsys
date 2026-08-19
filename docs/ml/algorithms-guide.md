# ML Algorithms Guide

## Collaborative Filtering

### User-Based CF
- **Idea**: Users who agreed in past will agree in future
- **Similarity**: Cosine, Pearson, Jaccard
- **Pros**: Simple, interpretable
- **Cons**: Sparsity, cold start, scalability

### Item-Based CF
- **Idea**: Items similar to previously liked items
- **Similarity**: Cosine, adjusted cosine, Pearson
- **Pros**: More stable than user-based, scalable
- **Cons**: Still cold start, limited serendipity

### Matrix Factorization (ALS)
- **Idea**: Decompose user-item matrix into latent factors
- **Algorithm**: Alternating Least Squares
- **Pros**: Handles sparsity, scalable, implicit feedback
- **Cons**: Cold start, needs retraining
- **Implementation**: `backend/ml/models/collaborative_filtering.py`

### SVD-Based
- **Idea**: Singular Value Decomposition for matrix factorization
- **Variants**: FunkSVD, BiasSVD, SVD++
- **Pros**: Better than basic MF for explicit feedback
- **Cons**: Computational complexity O(min(m,n)³)

## Content-Based Filtering

### TF-IDF Approach
- **Idea**: Recommend items with similar content features
- **Features**: Text descriptions, genres, tags
- **Pros**: No cold start for items, interpretable
- **Cons**: Limited serendipity, feature engineering
- **Implementation**: `backend/ml/models/content_based.py`

### Embedding-Based
- **Idea**: Learn dense embeddings for items
- **Models**: Word2Vec, Doc2Vec, Sentence Transformers
- **Pros**: Captures semantic similarity
- **Cons**: Needs large training data

## Hybrid Approaches

### Weighted Hybrid
- **Idea**: Combine scores from multiple models
- **Formula**: `score = w1*cf + w2*content + w3*trending`
- **Pros**: Simple, flexible
- **Cons**: Weight tuning

### Switching Hybrid
- **Idea**: Use different models based on context
- **Example**: Content-based for new users, CF for active users
- **Pros**: Best of both worlds
- **Cons**: Context detection overhead

### Cascade Hybrid
- **Idea**: Use first model to filter, second to rank
- **Example**: CF for candidates, LTR for ranking
- **Pros**: Specialized models
- **Cons**: Error propagation

### Feature Combination
- **Idea**: Concatenate features from different models
- **Example**: CF embeddings + content features → neural network
- **Pros**: Cross-model interactions
- **Cons**: Complex training

### Meta-Learning
- **Idea**: Learn to combine model predictions
- **Models**: Stacking, blending, learned weights
- **Pros**: Adaptive combination
- **Cons**: Needs held-out data

## Deep Learning Models

### Autoencoders
- **Idea**: Learn compressed representations
- **Variants**: DAE, VAE, CVAE
- **Pros**: Non-linear, denoising
- **Cons**: Training instability

### Neural Collaborative Filtering
- **Idea**: Replace dot product with neural network
- **Architecture**: GMF + MLP + Output
- **Pros**: Captures non-linear interactions
- **Cons**: Cold start, needs large data
- **Implementation**: `backend/ml/models/neural_cf.py`

### Two-Tower Model
- **Idea**: Separate encoders for users and items
- **Architecture**: User tower + Item tower + dot product
- **Pros**: Efficient ANN search, scalable
- **Cons**: Limited interaction modeling
- **Implementation**: `backend/ml/models/two_tower.py`

### Transformer-Based
- **Idea**: Self-attention for sequential recommendations
- **Models**: SASRec, BERT4Rec, SASRec
- **Pros**: Captures long-range dependencies
- **Cons**: O(n²) complexity, needs large data

## Sequence Models

### RNN-Based
- **Idea**: Model user interaction sequences
- **Architecture**: GRU/LSTM for session modeling
- **Pros**: Temporal patterns
- **Cons**: Vanishing gradients

### Session-Based
- **Idea**: Recommendations within a session
- **Models**: GRU4Rec, NARM, STAMP
- **Pros**: Real-time adaptation
- **Cons**: Limited long-term patterns

### Markov Chains
- **Idea**: Next item depends on previous items
- **Pros**: Simple, interpretable
- **Cons**: Limited context window

## Graph-Based

### Knowledge Graph
- **Idea**: Use entity relationships for recommendations
- **Models**: KGAT, KGCN, RippleNet
- **Pros**: Rich side information
- **Cons**: Graph construction overhead

### Graph Neural Networks
- **Idea**: Learn embeddings from graph structure
- **Models**: GCN, GraphSAGE, PinSage
- **Pros**: Captures graph structure
- **Cons**: Scalability challenges

### Social Network
- **Idea**: Friends' preferences influence recommendations
- **Models**: Social MF, TrustSVD
- **Pros**: Social signals
- **Cons**: Privacy concerns

## Reinforcement Learning

### Bandit Approaches
- **Idea**: Balance exploration and exploitation
- **Models**: LinUCB, Thompson Sampling
- **Pros**: Online learning
- **Cons**: Cold start, exploration cost

### Q-Learning
- **Idea**: Learn optimal recommendation policy
- **Models**: DQN, Double DQN
- **Pros**: Long-term optimization
- **Cons**: Sample inefficiency

### Policy Gradient
- **Idea**: Optimize recommendation policy directly
- **Models**: REINFORCE, PPO
- **Pros**: Direct optimization
- **Cons**: Variance, training instability

## Ensemble Methods

### Stacking
- **Idea**: Train meta-learner on base model predictions
- **Pros**: Captures model interactions
- **Cons**: Complex, needs held-out data

### Blending
- **Idea**: Weighted average of base model predictions
- **Pros**: Simple, robust
- **Cons**: Fixed weights

### Bagging
- **Idea**: Train multiple models on different subsets
- **Pros**: Reduces variance
- **Cons**: Computational cost

### Boosting
- **Idea**: Sequentially improve weak models
- **Models**: AdaBoost, Gradient Boosting, XGBoost
- **Pros**: Strong performance
- **Cons**: Overfitting risk

## Model Selection Guide

| Scenario | Recommended Model |
|----------|------------------|
| Cold Start (New User) | Content-Based + Trending |
| Cold Start (New Item) | Content-Based + Social |
| Active User | Collaborative Filtering + LTR |
| Sparse Data | Matrix Factorization (ALS) |
| Sequential Behavior | Session-Based (GRU4Rec) |
| Graph Structure | Graph Neural Network |
| Real-Time Adaptation | Bandit / Online Learning |

## References

- "Recommender Systems Handbook" by Ricci et al.
- "Deep Learning for Recommender Systems" by Zhang et al.
- Netflix: "Machine Learning Recommendations" (2022)
- YouTube: "Deep Neural Networks for YouTube Recommendations" (2016)
