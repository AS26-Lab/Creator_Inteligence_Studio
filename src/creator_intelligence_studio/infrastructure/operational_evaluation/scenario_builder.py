"""Definicion de escenarios de evaluacion operativa."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.operational_evaluation.entities import OperationalEvaluationScenarioDefinition


@dataclass(frozen=True, slots=True)
class ScenarioPlan:
    definition: OperationalEvaluationScenarioDefinition
    video_styles: tuple[str, ...]
    narration_text: str
    duration_seconds: float
    use_controlled_feedback: bool = False
    force_cpu_transcription: bool = False
    repeat_for_cache_reuse: bool = False
    simulate_failure_recovery: bool = False
    export_report: bool = False


def list_operational_scenarios() -> list[OperationalEvaluationScenarioDefinition]:
    return [
        OperationalEvaluationScenarioDefinition(
            id="smoke_pipeline",
            version="1",
            name="Smoke pipeline",
            description="Video sintetico corto para validar toda la tuberia tecnica.",
            required_stage_names=(
                "create_demo_creator",
                "create_demo_project",
                "generate_demo_video",
                "register_video",
                "inspect_media",
                "prepare_audio",
                "ensure_transcription_model",
                "transcribe",
                "analyze_acoustics",
                "analyze_visuals",
                "analyze_multimodal",
                "rank_clips",
                "apply_controlled_feedback",
                "build_personalization_dataset",
                "evaluate_readiness",
            ),
        ),
        OperationalEvaluationScenarioDefinition(
            id="controlled_creator_workflow",
            version="1",
            name="Controlled creator workflow",
            description="Creador sintetico con varios videos y feedback controlado.",
            required_stage_names=(
                "create_demo_creator",
                "create_demo_project",
                "generate_demo_video",
                "register_video",
                "inspect_media",
                "prepare_audio",
                "transcribe",
                "analyze_acoustics",
                "analyze_visuals",
                "analyze_multimodal",
                "rank_clips",
                "apply_controlled_feedback",
                "build_personalization_dataset",
                "evaluate_readiness",
                "train_baseline",
                "verify_artifact",
                "activate_model",
                "score_candidates",
                "export_report",
            ),
            notes=(
                "Feedback sintetico auditable con synthetic_evaluation_rule.",
                "Escenario multivideo aislado para validacion tecnica.",
            ),
        ),
        OperationalEvaluationScenarioDefinition(
            id="failure_recovery",
            version="1",
            name="Failure recovery",
            description="Valida fallos, reintentos y estados stale sin corromper artefactos.",
            required_stage_names=(
                "create_demo_creator",
                "create_demo_project",
                "generate_demo_video",
                "register_video",
                "inspect_media",
                "prepare_audio",
                "ensure_transcription_model",
                "transcribe",
                "retry_transcribe",
                "analyze_acoustics",
                "analyze_visuals",
                "analyze_multimodal",
            ),
        ),
        OperationalEvaluationScenarioDefinition(
            id="cache_reuse",
            version="1",
            name="Cache reuse",
            description="Ejecuta dos pasadas para demostrar reutilizacion de cachÃ©.",
            required_stage_names=(
                "create_demo_creator",
                "create_demo_project",
                "generate_demo_video",
                "register_video",
                "inspect_media",
                "prepare_audio",
                "ensure_transcription_model",
                "transcribe",
                "transcribe_cached",
                "analyze_acoustics",
                "analyze_visuals",
                "analyze_multimodal",
                "rank_clips",
            ),
        ),
        OperationalEvaluationScenarioDefinition(
            id="cpu_fallback",
            version="1",
            name="CPU fallback",
            description="Ejecuta la transcripcion con device cpu para validar resiliencia.",
            required_stage_names=(
                "create_demo_creator",
                "create_demo_project",
                "generate_demo_video",
                "register_video",
                "inspect_media",
                "prepare_audio",
                "ensure_transcription_model",
                "transcribe_cpu",
                "analyze_acoustics",
                "analyze_visuals",
                "analyze_multimodal",
                "rank_clips",
            ),
        ),
    ]


def resolve_scenario_plan(scenario_id: str) -> ScenarioPlan:
    definitions = {scenario.id: scenario for scenario in list_operational_scenarios()}
    if scenario_id not in definitions:
        raise KeyError(scenario_id)
    definition = definitions[scenario_id]
    if scenario_id == "controlled_creator_workflow":
        return ScenarioPlan(
            definition=definition,
            video_styles=("cut", "fade", "static", "testsrc", "cut", "fade", "static", "testsrc"),
            narration_text="Hello from Creator Intelligence Studio. This is a controlled evaluation sample.",
            duration_seconds=6.0,
            use_controlled_feedback=True,
            force_cpu_transcription=True,
            export_report=True,
        )
    if scenario_id == "failure_recovery":
        return ScenarioPlan(
            definition=definition,
            video_styles=("static",),
            narration_text="Hello from Creator Intelligence Studio. Recovery scenario.",
            duration_seconds=4.0,
            simulate_failure_recovery=True,
        )
    if scenario_id == "cache_reuse":
        return ScenarioPlan(
            definition=definition,
            video_styles=("cut",),
            narration_text="Hello from Creator Intelligence Studio. Cache reuse scenario.",
            duration_seconds=5.0,
            repeat_for_cache_reuse=True,
        )
    if scenario_id == "cpu_fallback":
        return ScenarioPlan(
            definition=definition,
            video_styles=("static",),
            narration_text="Hello from Creator Intelligence Studio. CPU fallback scenario.",
            duration_seconds=4.0,
            force_cpu_transcription=True,
        )
    return ScenarioPlan(
        definition=definition,
        video_styles=("static",),
        narration_text="Hello from Creator Intelligence Studio.",
        duration_seconds=4.0,
    )
