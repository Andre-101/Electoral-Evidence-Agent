from __future__ import annotations

from dataclasses import dataclass

from app.core.settings import get_settings


@dataclass(frozen=True)
class LlmResult:
    used_llm: bool
    provider: str
    model: str | None
    text: str | None
    error: str | None = None


class ClaudeLlmService:
    """
    Optional Anthropic/Claude integration.

    Behavior:
    - If ANTHROPIC_API_KEY is missing, return used_llm=False.
    - If the API call fails, return used_llm=False with error.
    - The caller must keep deterministic fallback.
    """

    def __init__(self):
        self.settings = get_settings()

    def is_available(self) -> bool:
        return bool(self.settings.anthropic_api_key.strip())

    def generate_dossier_sections(
        self,
        agent_context: dict,
        policy: dict,
        model: str | None = None,
    ) -> LlmResult:
        if not self.is_available():
            return LlmResult(
                used_llm=False,
                provider="anthropic",
                model=model or self.settings.anthropic_model,
                text=None,
                error="ANTHROPIC_API_KEY not configured.",
            )

        try:
            from anthropic import Anthropic
        except Exception as exc:
            return LlmResult(
                used_llm=False,
                provider="anthropic",
                model=model or self.settings.anthropic_model,
                text=None,
                error=f"anthropic package not available: {exc}",
            )

        selected_model = model or self.settings.anthropic_model
        client = Anthropic(api_key=self.settings.anthropic_api_key)

        prompt = self._build_prompt(agent_context, policy)

        try:
            response = client.messages.create(
                model=selected_model,
                max_tokens=self.settings.llm_max_tokens,
                temperature=0.2,
                system=(
                    "Eres un asistente especializado en explicar evidencia electoral. "
                    "No afirmes fraude, no acuses actores, no infieras intención y no uses lenguaje prohibido. "
                    "Produce un dossier claro, técnico y no concluyente."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            text = "".join(
                block.text for block in response.content
                if getattr(block, "type", None) == "text"
            )
            return LlmResult(
                used_llm=True,
                provider="anthropic",
                model=selected_model,
                text=text,
                error=None,
            )
        except Exception as exc:
            return LlmResult(
                used_llm=False,
                provider="anthropic",
                model=selected_model,
                text=None,
                error=str(exc),
            )

    def _build_prompt(self, agent_context: dict, policy: dict) -> str:
        return f"""
Genera un evidence_dossier en español para un caso de revisión electoral.

Reglas obligatorias:
- No concluyas fraude electoral.
- No acuses actores.
- No uses lenguaje prohibido.
- Incluye limitaciones.
- Incluye siguientes pasos.
- Incluye exactamente esta declaración metodológica al final del resumen ejecutivo:
{policy.get("required_disclaimer")}

Lenguaje prohibido:
{policy.get("forbidden_language")}

Contexto estructurado:
{agent_context}

Formato de salida requerido:

## RESUMEN_EJECUTIVO
...

## RESUMEN_TECNICO
...

## LIMITACIONES
...

## SIGUIENTES_PASOS
...
""".strip()
