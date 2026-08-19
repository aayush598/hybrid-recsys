# Model Training Guide

## Training Infrastructure

### Local Development
- **CPU**: Single machine training (good for prototyping)
- **GPU**: CUDA-enabled training for deep learning models
- **Memory**: 8GB+ RAM for medium datasets

### Production Training
- **Distributed**: Multi-node training with PyTorch DDP
- **Cloud**: AWS SageMaker, GCP Vertex AI
- **Kubernetes**: Training operators for orchestrated jobs

## Training Pipeline

### Data Preparation
```python
# 1. Load and validate data
df = pd.read_parquet("train.parquet")
validate_schema(df, expected_schema)

# 2. Split data (temporal for recsys)
train = df[df["timestamp"] < cutoff_date]
val = df[(df["timestamp"] >= cutoff_date) & (df["timestamp"] < val_date)]
test = df[df["timestamp"] >= val_date]

# 3. Build interaction matrix
from scipy.sparse import csr_matrix
interactions = csr_matrix(
    (train["rating"], (train["user_id"], train["item_id"])),
    shape=(n_users, n_items)
)
```

### Model Training
```python
# ALS Collaborative Filtering
from implicit.als import AlternatingLeastSquares

model = AlternatingLeastSquares(
    factors=128,
    regularization=0.01,
    iterations=50,
    use_gpu=True
)
model.fit(interactions)

# Neural Collaborative Filtering
import torch
from ml.models.neural_cf import NCF, NCFTrainer

model = NCF(
    n_users=162000,
    n_items=62000,
    embedding_dim=64,
    mlp_layers=[256, 128, 64]
)
trainer = NCFTrainer(model, lr=0.001, epochs=20)
trainer.fit(train_loader, val_loader)
```

### Hyperparameter Tuning
```python
# Grid Search
param_grid = {
    "factors": [64, 128, 256],
    "regularization": [0.001, 0.01, 0.1],
    "iterations": [30, 50, 100]
}

# Random Search
from scipy.stats import uniform, randint
param_distributions = {
    "factors": randint(32, 256),
    "regularization": uniform(0.001, 0.1),
    "lr": uniform(0.0001, 0.01)
}

# Bayesian Optimization (future)
# optuna, hyperopt, or scikit-optimize
```

### Evaluation
```python
from ml.evaluation.metrics import evaluate

metrics = evaluate(
    model=model,
    test_data=test,
    k_values=[5, 10, 20],
    metrics=["precision", "recall", "ndcg", "map"]
)
print(f"Precision@10: {metrics['precision@10']:.4f}")
print(f"NDCG@10: {metrics['ndcg@10']:.4f}")
```

## Experiment Tracking

### MLflow Integration
```python
import mlflow

with mlflow.start_run(run_name="als_v1"):
    mlflow.log_param("factors", 128)
    mlflow.log_param("regularization", 0.01)
    mlflow.log_metric("precision@10", 0.15)
    mlflow.log_metric("ndcg@10", 0.38)
    mlflow.sklearn.log_model(model, "model")
```

### Model Registry
```python
# Register model
mlflow.register_model(
    "runs:/<run_id>/model",
    "BeautyRec-CF"
)

# Promote to production
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="BeautyRec-CF",
    version=1,
    stage="production"
)
```

## Model Optimization

### Quantization
```python
# INT8 quantization for embeddings
import numpy as np

embeddings = model.user_embeddings
quantized = np.quantile(embeddings, np.arange(256) / 255)
indices = np.searchsorted(quantized, embeddings)
```

### Pruning
```python
# Structured pruning for neural networks
import torch.nn.utils.prune as prune

for name, module in model.named_modules():
    if isinstance(module, torch.nn.Linear):
        prune.l1_unstructured(module, name="weight", amount=0.3)
```

### Knowledge Distillation
```python
# Distill large model to smaller one
teacher = load_model("teacher_model")
student = SmallerModel()

for batch in dataloader:
    with torch.no_grad():
        teacher_logits = teacher(batch)
    student_logits = student(batch)
    loss = kl_divergence(teacher_logits, student_logits)
    loss.backward()
```

## Reproducibility

### Seed Management
```python
import random
import numpy as np
import torch

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
```

### Environment Tracking
```python
# Save environment
import pip

with open("requirements.txt", "w") as f:
    for package in pip.get_installed_distributions():
        f.write(f"{package.project_name}=={package.version}\n")
```

### Data Versioning
- **DVC**: Data version control
- **LakeFS**: Git-like interface for data lakes
- **Delta Lake**: ACID transactions for data lakes

## Deployment

### Model Serialization
```python
# PyTorch
torch.save(model.state_dict(), "model.pth")

# ONNX export
torch.onnx.export(model, dummy_input, "model.onnx")

# Pickle (for sklearn)
import joblib
joblib.dump(model, "model.pkl")
```

### Model Serving
```python
# FastAPI endpoint
@app.post("/predict")
async def predict(user_id: int):
    model = get_production_model()
    recommendations = model.predict(user_id)
    return {"recommendations": recommendations}
```

## References

- "Designing Machine Learning Systems" by Chip Huyen
- "Building Machine Learning Pipelines" by Hannes Hapke
- MLflow: https://mlflow.org/
- PyTorch Lightning: https://lightning.ai/
