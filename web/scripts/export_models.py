"""Export MovieLens CSV data and trained models directly to JSON for Next.js.
Skips SQLite entirely — reads CSVs directly."""
from __future__ import annotations

import csv
import json
import math
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "backend" / "data" / "raw" / "ml-25m"
MODEL_DIR = PROJECT_ROOT / "backend" / "data" / "models"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"


def export_cf_model():
    print("Exporting CF model...")
    with open(MODEL_DIR / "cf_model.pkl", "rb") as f:
        data = pickle.load(f)

    user_id_map = data["user_id_map"]
    item_id_map = data["item_id_map"]
    reverse_item_map = data["reverse_item_map"]
    model = data["model"]

    user_factors = np.array(model.user_factors, dtype=np.float32)
    item_factors = np.array(model.item_factors, dtype=np.float32)

    print(f"  Users: {user_factors.shape}, Items: {item_factors.shape}")

    with open(OUTPUT_DIR / "user_factors.json", "w") as f:
        json.dump(user_factors.tolist(), f)

    with open(OUTPUT_DIR / "item_factors.json", "w") as f:
        json.dump(item_factors.tolist(), f)

    with open(OUTPUT_DIR / "cf_mappings.json", "w") as f:
        json.dump({
            "user_id_map": {str(k): int(v) for k, v in user_id_map.items()},
            "item_id_map": {str(k): int(v) for k, v in item_id_map.items()},
            "reverse_item_map": {str(k): int(v) for k, v in reverse_item_map.items()},
        }, f)

    print("  Done.")


def export_content_model():
    print("Exporting content model...")
    with open(MODEL_DIR / "content_movie_ids.pkl", "rb") as f:
        movie_ids = pickle.load(f)
    feature_matrix = np.load(MODEL_DIR / "content_feature_matrix.npy")

    print(f"  Movies: {len(movie_ids)}, Features: {feature_matrix.shape}")

    with open(OUTPUT_DIR / "content_movie_ids.json", "w") as f:
        json.dump(movie_ids, f)

    with open(OUTPUT_DIR / "content_features.json", "w") as f:
        json.dump(feature_matrix.tolist(), f)

    print("  Done.")


def export_movies():
    print("Exporting movies...")
    movies_path = DATA_DIR / "movies.csv"
    movies = []
    with open(movies_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = int(row["movieId"])
            title = row["title"]
            genres = row["genres"]
            year = None
            if "(" in title and title.endswith(")"):
                try:
                    year = int(title.split("(")[-1].replace(")", "").strip())
                except ValueError:
                    pass
            movies.append({
                "id": movie_id,
                "title": title,
                "genres": genres,
                "year": year,
                "overview": "",
                "poster_url": "",
                "vote_average": None,
                "vote_count": None,
                "popularity": None,
            })

    with open(OUTPUT_DIR / "movies.json", "w") as f:
        json.dump(movies, f)

    print(f"  Movies: {len(movies)} exported.")
    return {m["id"] for m in movies}


def export_ratings(valid_movie_ids: set[int]):
    print("Exporting ratings (filtered to model users only)...")
    ratings_path = DATA_DIR / "ratings.csv"

    with open(OUTPUT_DIR / "cf_mappings.json") as f:
        cf_maps = json.load(f)
    valid_user_ids = set(cf_maps["user_id_map"].keys())

    ratings = []
    with open(ratings_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = str(int(row["userId"]))
            movie_id = int(row["movieId"])
            if user_id not in valid_user_ids:
                continue
            if movie_id not in valid_movie_ids:
                continue
            ratings.append({
                "user_id": user_id,
                "movie_id": movie_id,
                "rating": float(row["rating"]),
                "timestamp": int(row["timestamp"]),
            })

    with open(OUTPUT_DIR / "ratings.json", "w") as f:
        json.dump(ratings, f)

    print(f"  Ratings: {len(ratings)} exported (filtered to {len(valid_user_ids)} users).")


def export_trending(valid_movie_ids: set[int]):
    print("Exporting trending...")
    ratings_path = DATA_DIR / "ratings.csv"
    movie_scores = defaultdict(list)

    with open(ratings_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = int(row["movieId"])
            if movie_id not in valid_movie_ids:
                continue
            movie_scores[movie_id].append(float(row["rating"]))

    scored = []
    for movie_id, ratings_list in movie_scores.items():
        avg_rating = sum(ratings_list) / len(ratings_list)
        count = len(ratings_list)
        score = avg_rating * math.log1p(count)
        scored.append({"movie_id": movie_id, "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)

    with open(OUTPUT_DIR / "trending.json", "w") as f:
        json.dump(scored[:500], f)

    print(f"  Trending: top 500 exported.")


def export_genres():
    print("Exporting genres...")
    movies_path = OUTPUT_DIR / "movies.json"
    with open(movies_path) as f:
        movies = json.load(f)

    all_genres = set()
    for m in movies:
        if m["genres"] and m["genres"] != "(no genres listed)":
            for g in m["genres"].split("|"):
                g = g.strip()
                if g:
                    all_genres.add(g)

    with open(OUTPUT_DIR / "genres.json", "w") as f:
        json.dump(sorted(all_genres), f)

    print(f"  Genres: {sorted(all_genres)}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    export_cf_model()
    export_content_model()
    valid_movie_ids = export_movies()
    export_ratings(valid_movie_ids)
    export_trending(valid_movie_ids)
    export_genres()

    print(f"\nAll models exported to {OUTPUT_DIR}")
    total = 0
    for f in sorted(OUTPUT_DIR.glob("*.json")):
        size = f.stat().st_size
        total += size
        print(f"  {f.name}: {size / 1024 / 1024:.2f} MB")
    print(f"  TOTAL: {total / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
