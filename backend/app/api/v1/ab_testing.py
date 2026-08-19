from __future__ import annotations

from fastapi import APIRouter

from app.serving.ab_testing.manager import ab_test_manager

router = APIRouter()


@router.get("/")
async def list_experiments():
    """List all A/B test experiments."""
    return {"experiments": ab_test_manager.list_experiments()}


@router.post("/{experiment_name}/assign")
async def assign_variant(
    experiment_name: str,
    user_id: str,
):
    """Get variant assignment for a user."""
    variant = ab_test_manager.assign_variant(experiment_name, user_id)
    config = ab_test_manager.get_variant_config(experiment_name, user_id)
    return {
        "experiment": experiment_name,
        "user_id": user_id,
        "variant": variant,
        "config": config,
    }


@router.post("/{experiment_name}/convert")
async def track_conversion(
    experiment_name: str,
    user_id: str,
    metric_name: str = "click",
    metric_value: float = 1.0,
):
    """Track a conversion event."""
    ab_test_manager.track_conversion(experiment_name, user_id, metric_name, metric_value)
    return {"status": "tracked"}


@router.get("/{experiment_name}/results")
async def get_results(experiment_name: str):
    """Get experiment results with statistical analysis."""
    return ab_test_manager.get_experiment_results(experiment_name)


@router.post("/{experiment_name}/stop")
async def stop_experiment(experiment_name: str):
    """Stop an experiment."""
    ab_test_manager.stop_experiment(experiment_name)
    return {"status": "stopped", "experiment": experiment_name}
