from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.events.websocket_manager import ws_manager
from app.services.model_manager import model_manager

router = APIRouter()


@router.websocket("/ws/recommendations/{user_id}")
async def websocket_recommendations(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time recommendations.

    Protocol:
    - Client sends: {"type": "subscribe", "algorithm": "hybrid"}
    - Server sends: {"type": "recommendations", "data": [...]}
    - Client sends: {"type": "interact", "movie_id": 123, "action": "like"}
    - Server sends: {"type": "ack", "status": "recorded"}
    - Client sends: {"type": "ping"}
    - Server sends: {"type": "pong"}
    """
    connection_id = await ws_manager.connect(websocket, user_id)

    try:
        await ws_manager.send_personal(user_id, {
            "type": "connected",
            "connection_id": connection_id,
            "message": "Connected to BeautyRec real-time recommendations",
        })

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(raw)
                msg_type = message.get("type")

                if msg_type == "ping":
                    await ws_manager.send_personal(user_id, {"type": "pong", "timestamp": time.time()})

                elif msg_type == "subscribe":
                    algorithm = message.get("algorithm", "hybrid")
                    num_recs = message.get("num_recommendations", 10)

                    from app.db.session import get_db_context

                    async with get_db_context() as db:
                        service = model_manager.get_service()
                        response = await service.get_recommendations(
                            db=db,
                            user_id=user_id,
                            num_recommendations=num_recs,
                            algorithm=algorithm,
                        )

                    await ws_manager.send_personal(user_id, {
                        "type": "recommendations",
                        "data": [rec.model_dump() for rec in response.recommendations],
                        "algorithm": response.algorithm_used,
                        "latency_ms": response.latency_ms,
                    })

                elif msg_type == "interact":
                    movie_id = message.get("movie_id")
                    action = message.get("action", "view")

                    from app.db.session import get_db_context

                    async with get_db_context() as db:
                        service = model_manager.get_service()
                        await service.record_interaction(
                            db=db,
                            user_id=user_id,
                            movie_id=movie_id,
                            interaction_type=action,
                        )

                    await ws_manager.send_personal(user_id, {
                        "type": "ack",
                        "status": "recorded",
                        "movie_id": movie_id,
                        "action": action,
                    })

                elif msg_type == "similar":
                    movie_id = message.get("movie_id")
                    from app.db.session import get_db_context

                    async with get_db_context() as db:
                        service = model_manager.get_service()
                        results = await service.get_similar_items(db, movie_id, top_k=10)

                    await ws_manager.send_personal(user_id, {
                        "type": "similar_results",
                        "movie_id": movie_id,
                        "data": results,
                    })

                else:
                    await ws_manager.send_personal(user_id, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })

            except TimeoutError:
                try:
                    await ws_manager.send_personal(user_id, {"type": "ping"})
                except Exception:
                    break
            except json.JSONDecodeError:
                await ws_manager.send_personal(user_id, {
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(user_id)
