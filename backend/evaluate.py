from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import json
import logging
import time

from ml.evaluation.metrics import RecommendationEvaluator
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Rating
from app.db.session import get_db_context, init_db
from app.services.model_manager import model_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


async def run_evaluation():
    """Run full evaluation pipeline."""
    logger.info("=" * 60)
    logger.info("BeautyRec Evaluation Pipeline")
    logger.info("=" * 60)

    await init_db()

    async with get_db_context() as db:
        ratings_count = await db.execute(select(Rating))
        ratings = ratings_count.scalars().all()
        if not ratings:
            logger.error("No ratings in database. Run data pipeline first.")
            return

        logger.info(f"Found {len(ratings)} ratings in database")

        logger.info("Loading models...")
        await model_manager.initialize()
        service = model_manager.get_service()

        logger.info("Generating recommendations for test users...")
        user_ids = list(set(r.user_id for r in ratings))
        user_ratings_count = {}
        for r in ratings:
            user_ratings_count[r.user_id] = user_ratings_count.get(r.user_id, 0) + 1

        test_users = [uid for uid, count in user_ratings_count.items() if count >= 10][:500]
        logger.info(f"Evaluating on {len(test_users)} test users")

        all_recommendations = {}
        start_time = time.time()

        for i, user_id in enumerate(test_users):
            try:
                response = await service.get_recommendations(
                    db=db,
                    user_id=user_id,
                    num_recommendations=20,
                    algorithm=None,
                    exclude_seen=False,
                )
                all_recommendations[user_id] = [item.movie.id for item in response.recommendations]
            except Exception as e:
                logger.warning(f"Failed for user {user_id}: {e}")

            if (i + 1) % 100 == 0:
                logger.info(f"  Progress: {i + 1}/{len(test_users)} users")

        total_time = time.time() - start_time
        avg_latency = (total_time / len(test_users)) * 1000 if test_users else 0
        logger.info(f"Generated recommendations in {total_time:.1f}s (avg {avg_latency:.1f}ms/user)")

        logger.info("Computing metrics...")
        evaluator = RecommendationEvaluator(db)
        metrics = await evaluator.evaluate_model(all_recommendations, k_values=[5, 10, 20])

        metrics["avg_latency_ms"] = round(avg_latency, 2)
        metrics["total_evaluation_time_s"] = round(total_time, 2)

        logger.info("")
        logger.info("=" * 60)
        logger.info("EVALUATION RESULTS")
        logger.info("=" * 60)
        logger.info(json.dumps(metrics, indent=2))

        results_dir = settings.DATA_DIR / "evaluation"
        results_dir.mkdir(parents=True, exist_ok=True)
        with open(results_dir / "evaluation_results.json", "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Results saved to {results_dir / 'evaluation_results.json'}")

        logger.info("")
        logger.info("METRIC SUMMARY:")
        logger.info(f"  Precision@10: {metrics['precision_at_k'].get('k=10', 'N/A')}")
        logger.info(f"  Recall@10:    {metrics['recall_at_k'].get('k=10', 'N/A')}")
        logger.info(f"  NDCG@10:      {metrics['ndcg_at_k'].get('k=10', 'N/A')}")
        logger.info(f"  MAP@10:       {metrics['map_at_k'].get('k=10', 'N/A')}")
        logger.info(f"  Hit Rate@10:  {metrics['hit_rate_at_k'].get('k=10', 'N/A')}")
        logger.info(f"  Coverage:     {metrics['coverage']}")
        logger.info(f"  Diversity:    {metrics['diversity']}")
        logger.info(f"  Novelty:      {metrics['novelty']}")
        logger.info(f"  Avg Latency:  {metrics['avg_latency_ms']}ms")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
