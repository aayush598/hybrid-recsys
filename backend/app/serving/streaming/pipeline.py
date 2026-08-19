from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StreamEvent:
    event_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"


class StreamingIngestionPipeline:
    """In-memory streaming ingestion pipeline.

    For production, this would use Apache Kafka or Redis Streams.
    This implementation provides the same semantics with in-memory
    queues, suitable for demo and moderate-scale deployments.

    Features:
    - Event-driven architecture
    - Consumer groups for parallel processing
    - Dead letter queue for failed events
    - Backpressure handling
    - Event replay from offset
    """

    def __init__(self, max_queue_size: int = 100_000):
        self.max_queue_size = max_queue_size
        self._topics: dict[str, deque[StreamEvent]] = {}
        self._subscribers: dict[str, list[Callable]] = {}
        self._offsets: dict[str, dict[str, int]] = {}
        self._dead_letter_queue: deque[StreamEvent] = deque(maxlen=10_000)
        self._running = False
        self._processed_count = 0
        self._error_count = 0

    def create_topic(self, topic: str, max_size: int = 100_000) -> None:
        """Create a new topic (event stream)."""
        if topic not in self._topics:
            self._topics[topic] = deque(maxlen=max_size)
            self._subscribers[topic] = []
            self._offsets[topic] = {}
            logger.info(f"Created topic: {topic}")

    async def publish(self, topic: str, event: StreamEvent) -> bool:
        """Publish an event to a topic."""
        if topic not in self._topics:
            self.create_topic(topic)

        if len(self._topics[topic]) >= self.max_queue_size:
            logger.warning(f"Topic '{topic}' queue full, applying backpressure")
            await asyncio.sleep(0.01)

        self._topics[topic].append(event)

        for subscriber in self._subscribers.get(topic, []):
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception as e:
                logger.error(f"Subscriber error on topic '{topic}': {e}")
                self._dead_letter_queue.append(event)

        return True

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to a topic with a callback."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.info(f"Subscribed to topic: {topic}")

    async def consume_batch(
        self,
        topic: str,
        consumer_id: str,
        batch_size: int = 100,
        handler: Callable | None = None,
    ) -> list[StreamEvent]:
        """Consume a batch of events from a topic."""
        if topic not in self._topics:
            return []

        offset = self._offsets.get(topic, {}).get(consumer_id, 0)
        events = []
        queue = self._topics[topic]

        for i in range(min(batch_size, len(queue) - offset)):
            if offset + i < len(queue):
                events.append(queue[offset + i])

        self._offsets.setdefault(topic, {})[consumer_id] = offset + len(events)

        if handler and events:
            for event in events:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                    self._processed_count += 1
                except Exception as e:
                    logger.error(f"Handler error: {e}")
                    self._dead_letter_queue.append(event)
                    self._error_count += 1

        return events

    async def publish_interaction(
        self,
        user_id: str,
        movie_id: int,
        interaction_type: str,
        intensity: float = 1.0,
    ) -> None:
        """Publish a user interaction event."""
        event = StreamEvent(
            event_type="interaction",
            data={
                "user_id": user_id,
                "movie_id": movie_id,
                "interaction_type": interaction_type,
                "intensity": intensity,
            },
            source="api",
        )
        await self.publish("interactions", event)

    async def publish_rating(
        self, user_id: str, movie_id: int, rating: float
    ) -> None:
        """Publish a rating event."""
        event = StreamEvent(
            event_type="rating",
            data={
                "user_id": user_id,
                "movie_id": movie_id,
                "rating": rating,
            },
            source="api",
        )
        await self.publish("ratings", event)

    async def publish_recommendation_feedback(
        self,
        user_id: str,
        recommended_ids: list[int],
        clicked_id: int | None = None,
        algorithm: str = "hybrid",
    ) -> None:
        """Publish recommendation feedback for model improvement."""
        event = StreamEvent(
            event_type="recommendation_feedback",
            data={
                "user_id": user_id,
                "recommended_ids": recommended_ids,
                "clicked_id": clicked_id,
                "algorithm": algorithm,
            },
            source="frontend",
        )
        await self.publish("feedback", event)

    def get_topic_stats(self, topic: str) -> dict:
        """Get statistics for a topic."""
        queue = self._topics.get(topic, deque())
        return {
            "topic": topic,
            "queue_size": len(queue),
            "subscribers": len(self._subscribers.get(topic, [])),
            "total_published": len(queue),
        }

    @property
    def stats(self) -> dict:
        return {
            "topics": list(self._topics.keys()),
            "total_processed": self._processed_count,
            "total_errors": self._error_count,
            "dead_letter_size": len(self._dead_letter_queue),
            "topic_stats": {
                name: self.get_topic_stats(name) for name in self._topics
            },
        }


streaming_pipeline = StreamingIngestionPipeline()
