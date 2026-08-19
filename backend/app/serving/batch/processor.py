from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BatchJob:
    job_id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    status: str = "pending"
    result: Any = None
    error: str | None = None


class BatchProcessor:
    """Asynchronous batch processor for background jobs.

    Processes items in configurable batch sizes with:
    - Priority queue scheduling
    - Concurrent worker pool
    - Automatic retries with exponential backoff
    - Progress tracking and metrics
    - Graceful shutdown

    Use cases:
    - Bulk model retraining
    - Feature computation for all users
    - Index rebuilding
    - Data pipeline ETL jobs
    """

    def __init__(
        self,
        max_workers: int = 4,
        batch_size: int = 1000,
        max_retries: int = 3,
    ):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._jobs: dict[str, BatchJob] = {}
        self._queue: list[BatchJob] = []
        self._running = False
        self._workers: list[asyncio.Task] = []
        self._completed_jobs: list[BatchJob] = []
        self._stats = {
            "total_processed": 0,
            "total_failed": 0,
            "total_batches": 0,
        }

    async def submit(
        self,
        job_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: int = 0,
    ) -> str:
        """Submit a job for batch processing."""
        job = BatchJob(
            job_id=job_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
        )
        self._jobs[job_id] = job
        self._queue.append(job)
        self._queue.sort(key=lambda j: j.priority, reverse=True)
        logger.info(f"Job submitted: {job_id} (priority={priority})")
        return job_id

    async def process_items(
        self,
        items: list[Any],
        process_fn: Callable,
        batch_size: int | None = None,
    ) -> list[Any]:
        """Process a large list of items in batches."""
        batch_size = batch_size or self.batch_size
        results = []
        total_batches = (len(items) + batch_size - 1) // batch_size

        logger.info(
            f"Processing {len(items)} items in {total_batches} batches "
            f"(batch_size={batch_size})"
        )

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batch_num = i // batch_size + 1

            try:
                batch_results = await self._process_batch(batch, process_fn)
                results.extend(batch_results)
                self._stats["total_batches"] += 1
                self._stats["total_processed"] += len(batch)

                if batch_num % 10 == 0:
                    logger.info(
                        f"Batch progress: {batch_num}/{total_batches} "
                        f"({self._stats['total_processed']} items processed)"
                    )
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                self._stats["total_failed"] += len(batch)

        logger.info(
            f"Processing complete: {len(results)} results, "
            f"{self._stats['total_failed']} failures"
        )
        return results

    async def _process_batch(
        self, batch: list[Any], process_fn: Callable
    ) -> list[Any]:
        """Process a single batch."""
        if asyncio.iscoroutinefunction(process_fn):
            results = await asyncio.gather(
                *[process_fn(item) for item in batch],
                return_exceptions=True,
            )
        else:
            loop = asyncio.get_event_loop()
            results = await asyncio.gather(
                *[loop.run_in_executor(None, process_fn, item) for item in batch],
                return_exceptions=True,
            )

        processed = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Item processing failed: {r}")
            else:
                processed.append(r)
        return processed

    async def start_workers(self) -> None:
        """Start background worker pool."""
        self._running = True
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        logger.info(f"Started {self.max_workers} batch workers")

    async def stop_workers(self) -> None:
        """Gracefully stop all workers."""
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("All batch workers stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop that processes jobs from the queue."""
        while self._running:
            if self._queue:
                job = self._queue.pop(0)
                job.started_at = time.time()
                job.status = "running"

                try:
                    for attempt in range(self.max_retries):
                        try:
                            if asyncio.iscoroutinefunction(job.func):
                                job.result = await job.func(*job.args, **job.kwargs)
                            else:
                                loop = asyncio.get_event_loop()
                                job.result = await loop.run_in_executor(
                                    None, lambda: job.func(*job.args, **job.kwargs)
                                )
                            job.status = "completed"
                            break
                        except Exception as e:
                            if attempt < self.max_retries - 1:
                                wait_time = 2 ** attempt
                                logger.warning(
                                    f"Job {job.job_id} attempt {attempt + 1} "
                                    f"failed, retrying in {wait_time}s: {e}"
                                )
                                await asyncio.sleep(wait_time)
                            else:
                                job.status = "failed"
                                job.error = str(e)

                finally:
                    job.completed_at = time.time()
                    self._completed_jobs.append(job)
            else:
                await asyncio.sleep(0.1)

    def get_job_status(self, job_id: str) -> dict | None:
        """Get status of a specific job."""
        job = self._jobs.get(job_id)
        if job:
            return {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "duration": (
                    (job.completed_at - job.started_at)
                    if job.completed_at and job.started_at
                    else None
                ),
                "error": job.error,
            }
        return None

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "queue_size": len(self._queue),
            "active_workers": len(self._workers),
            "running": self._running,
        }


batch_processor = BatchProcessor(max_workers=4, batch_size=1000)
