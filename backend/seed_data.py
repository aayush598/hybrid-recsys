from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging

from ml.pipelines.data_pipeline import FeatureEngineer, MovieLensDataPipeline

from app.core.config import get_settings
from app.db.session import get_db_context, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


async def main():
    """Run the complete data pipeline."""
    logger.info("Initializing database")
    await init_db()

    async with get_db_context() as db:
        logger.info("Starting MovieLens data pipeline")
        pipeline = MovieLensDataPipeline(db)

        sample_size = None
        if "--sample" in sys.argv:
            sample_size = 10000
            logger.info(f"Using sample mode: {sample_size} ratings")

        stats = await pipeline.run_full_pipeline(sample_size=sample_size)
        logger.info(f"Data pipeline complete: {stats}")

        logger.info("Building content features")
        feature_engineer = FeatureEngineer(db)
        await feature_engineer.build_content_features()
        logger.info("Feature engineering complete")


if __name__ == "__main__":
    asyncio.run(main())
