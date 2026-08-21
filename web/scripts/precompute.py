"""Pre-compute all recommendations and similar movies using the exported JSON data.
This avoids needing to load large factor matrices in the Next.js serverless functions."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"


def precompute_recommendations():
    """For each user, compute top-50 recommendations using dot product."""
    print("Loading model data...")
    with open(OUTPUT_DIR / "user_factors.json") as f:
        user_factors = np.array(json.load(f), dtype=np.float32)
    with open(OUTPUT_DIR / "item_factors.json") as f:
        item_factors = np.array(json.load(f), dtype=np.float32)
    with open(OUTPUT_DIR / "cf_mappings.json") as f:
        mappings = json.load(f)
    with open(OUTPUT_DIR / "ratings.json") as f:
        ratings = json.load(f)

    user_id_map = mappings["user_id_map"]
    item_id_map = mappings["item_id_map"]
    reverse_item_map = mappings["reverse_item_map"]

    # Build user->seen items
    user_seen = {}
    for r in ratings:
        uid = r["user_id"]
        mid = r["movie_id"]
        if str(mid) in item_id_map:
            user_seen.setdefault(uid, set()).add(mid)

    print(f"Pre-computing recommendations for {len(user_id_map)} users...")
    user_recs = {}
    for user_id, user_idx in user_id_map.items():
        u_vec = user_factors[user_idx]
        scores = item_factors @ u_vec

        seen = user_seen.get(user_id, set())
        scored = []
        for item_idx in np.argsort(scores)[::-1]:
            movie_id = reverse_item_map.get(str(item_idx))
            if movie_id is None:
                continue
            if movie_id in seen:
                continue
            scored.append({"movie_id": int(movie_id), "score": round(float(scores[item_idx]), 4)})
            if len(scored) >= 50:
                break

        user_recs[user_id] = scored

    with open(OUTPUT_DIR / "user_recommendations.json", "w") as f:
        json.dump(user_recs, f)

    size = (OUTPUT_DIR / "user_recommendations.json").stat().st_size
    print(f"  User recommendations: {len(user_recs)} users, {size / 1024 / 1024:.2f} MB")


def precompute_similar_movies():
    """For each movie, compute top-20 similar movies using cosine similarity on item factors."""
    print("Loading item factors...")
    with open(OUTPUT_DIR / "item_factors.json") as f:
        item_factors = np.array(json.load(f), dtype=np.float32)
    with open(OUTPUT_DIR / "cf_mappings.json") as f:
        mappings = json.load(f)

    reverse_item_map = mappings["reverse_item_map"]

    # Normalize for cosine similarity
    norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = item_factors / norms

    # Compute similarity matrix: item_factors @ item_factors.T
    print("Computing similarity matrix...")
    sim_matrix = normalized @ normalized.T

    print(f"Pre-computing similar movies for {len(reverse_item_map)} items...")
    similar = {}
    for item_idx_str, movie_id in reverse_item_map.items():
        item_idx = int(item_idx_str)
        sim_scores = sim_matrix[item_idx]

        top_indices = np.argsort(sim_scores)[::-1][1:21]  # skip self, top 20

        results = []
        for idx in top_indices:
            mid = reverse_item_map.get(str(idx))
            if mid is not None:
                results.append({
                    "movie_id": int(mid),
                    "score": round(float(sim_scores[idx]), 4),
                })

        similar[str(movie_id)] = results

    with open(OUTPUT_DIR / "similar_movies.json", "w") as f:
        json.dump(similar, f)

    size = (OUTPUT_DIR / "similar_movies.json").stat().st_size
    print(f"  Similar movies: {len(similar)} items, {size / 1024 / 1024:.2f} MB")


def precompute_content_similar():
    """For each movie, compute top-20 content-similar movies."""
    print("Loading content features...")
    with open(OUTPUT_DIR / "content_movie_ids.json") as f:
        movie_ids = json.load(f)
    with open(OUTPUT_DIR / "content_features.json") as f:
        features = np.array(json.load(f), dtype=np.float32)

    # Normalize
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = features / norms

    print("Computing content similarity matrix...")
    sim_matrix = normalized @ normalized.T

    print(f"Pre-computing content similar for {len(movie_ids)} items...")
    similar = {}
    for i, movie_id in enumerate(movie_ids):
        sim_scores = sim_matrix[i]
        top_indices = np.argsort(sim_scores)[::-1][1:21]

        results = []
        for idx in top_indices:
            if idx < len(movie_ids):
                results.append({
                    "movie_id": int(movie_ids[idx]),
                    "score": round(float(sim_scores[idx]), 4),
                })

        similar[str(movie_id)] = results

    with open(OUTPUT_DIR / "content_similar.json", "w") as f:
        json.dump(similar, f)

    size = (OUTPUT_DIR / "content_similar.json").stat().st_size
    print(f"  Content similar: {len(similar)} items, {size / 1024 / 1024:.2f} MB")


def build_hybrid_similar():
    """Combine CF and content similarity with weights."""
    print("Building hybrid similar movies...")

    with open(OUTPUT_DIR / "similar_movies.json") as f:
        cf_similar = json.load(f)
    with open(OUTPUT_DIR / "content_similar.json") as f:
        content_similar = json.load(f)

    hybrid = {}
    all_movie_ids = set(cf_similar.keys()) | set(content_similar.keys())

    for movie_id_str in all_movie_ids:
        cf = {str(r["movie_id"]): r["score"] for r in cf_similar.get(movie_id_str, [])}
        cb = {str(r["movie_id"]): r["score"] for r in content_similar.get(movie_id_str, [])}

        all_candidates = set(cf.keys()) | set(cb.keys())
        combined = []
        for mid in all_candidates:
            score = 0.45 * cf.get(mid, 0) + 0.30 * cb.get(mid, 0)
            if score > 0:
                combined.append({"movie_id": int(mid), "score": round(score, 4)})

        combined.sort(key=lambda x: x["score"], reverse=True)
        hybrid[movie_id_str] = combined[:20]

    with open(OUTPUT_DIR / "hybrid_similar.json", "w") as f:
        json.dump(hybrid, f)

    size = (OUTPUT_DIR / "hybrid_similar.json").stat().st_size
    print(f"  Hybrid similar: {len(hybrid)} items, {size / 1024 / 1024:.2f} MB")


def build_hybrid_recommendations():
    """Combine CF recommendations with content similarity for a hybrid approach."""
    print("Building hybrid recommendations...")

    with open(OUTPUT_DIR / "user_recommendations.json") as f:
        user_recs = json.load(f)
    with open(OUTPUT_DIR / "ratings.json") as f:
        ratings = json.load(f)
    with open(OUTPUT_DIR / "trending.json") as f:
        trending = json.load(f)

    trending_ids = [t["movie_id"] for t in trending[:200]]

    user_seen = {}
    for r in ratings:
        uid = r["user_id"]
        mid = r["movie_id"]
        user_seen.setdefault(uid, set()).add(mid)

    hybrid = {}
    for user_id, recs in user_recs.items():
        seen = user_seen.get(user_id, set())
        combined = {}
        for i, r in enumerate(recs):
            mid = str(r["movie_id"])
            combined[mid] = combined.get(mid, 0) + 0.60 * r["score"]

        for mid in trending_ids:
            if mid in seen:
                continue
            mid_str = str(mid)
            if mid_str not in combined:
                combined[mid_str] = combined.get(mid_str, 0) + 0.10 * 0.5

        results = [{"movie_id": int(mid), "score": round(score, 4)} for mid, score in sorted(combined.items(), key=lambda x: x[1], reverse=True)[:50]]
        hybrid[user_id] = results

    with open(OUTPUT_DIR / "hybrid_recommendations.json", "w") as f:
        json.dump(hybrid, f)

    size = (OUTPUT_DIR / "hybrid_recommendations.json").stat().st_size
    print(f"  Hybrid recommendations: {len(hybrid)} users, {size / 1024 / 1024:.2f} MB")


def main():
    precompute_recommendations()
    precompute_similar_movies()
    precompute_content_similar()
    build_hybrid_similar()
    build_hybrid_recommendations()

    # Remove large model files no longer needed
    large_files = ["user_factors.json", "item_factors.json", "content_features.json", "content_movie_ids.json"]
    for fname in large_files:
        fp = OUTPUT_DIR / fname
        if fp.exists():
            fp.unlink()
            print(f"  Removed {fname}")

    print("\nPre-computation complete!")
    total = 0
    for f in sorted(OUTPUT_DIR.glob("*.json")):
        size = f.stat().st_size
        total += size
        print(f"  {f.name}: {size / 1024 / 1024:.2f} MB")
    print(f"  TOTAL: {total / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
