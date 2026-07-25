"""Adaptador de prompts por herramienta."""

from __future__ import annotations


def adapt_prompt_for_tool(prompt_text: str, *, target_tool: str, reference_package: dict[str, object], negative_guidance: str | None = None) -> dict[str, object]:
    if target_tool == "chatgpt_images":
        usage_notes = {
            "style": "descripcion natural completa",
            "references": "lista de referencias con rol claro",
            "text": "no asumir texto perfecto",
        }
    elif target_tool == "envato_ai":
        usage_notes = {
            "style": "prompt compacto y estructurado",
            "references": "usar solo si el flujo lo permite",
            "text": "advertir sobre capacidades no verificadas",
        }
    elif target_tool == "manual_designer":
        usage_notes = {
            "style": "brief creativo con do/don't",
            "references": "ordenadas por prioridad",
            "text": "instrucciones de jerarquia y entregables",
        }
    elif target_tool == "manual_creation":
        usage_notes = {
            "style": "checklist local",
            "references": "assets necesarios",
            "text": "safe areas y recortes",
        }
    else:
        usage_notes = {
            "style": "prompt independiente",
            "references": "referencias recomendadas",
            "text": "controlar texto dentro de la imagen",
        }
    return {
        "prompt_text": prompt_text,
        "negative_guidance": negative_guidance,
        "tool_usage_notes": usage_notes,
        "reference_package": reference_package,
    }

