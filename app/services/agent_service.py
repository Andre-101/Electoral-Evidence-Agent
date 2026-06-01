from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.settings import get_settings, load_yaml_config
from app.db.models.evidence import EvidenceDossier
from app.db.models.reports import TraceabilityEvent
from app.services.evidence_service import EvidenceService
from app.services.llm_service import ClaudeLlmService


class AgentPolicyError(ValueError):
    pass


class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.evidence_service = EvidenceService(db)
        self.settings = get_settings()

    def _load_policy(self) -> dict:
        return load_yaml_config("config/agent_policy.yaml")

    def validate_text_against_policy(self, text: str, policy: dict | None = None) -> dict:
        policy = policy or self._load_policy()
        lower_text = text.lower()
        forbidden = [
            phrase
            for phrase in policy.get("forbidden_language", [])
            if phrase.lower() in lower_text
        ]

        required_disclaimer = policy.get("required_disclaimer", "")
        has_disclaimer = required_disclaimer.strip().lower() in lower_text

        passed = not forbidden
        if policy.get("output_validation", {}).get("require_disclaimer", True):
            passed = passed and has_disclaimer

        return {
            "passed": passed,
            "forbidden_matches": forbidden,
            "has_required_disclaimer": has_disclaimer,
        }

    def generate_dossier(
        self,
        review_case_id: uuid.UUID,
        force_regenerate: bool = False,
        include_technical_summary: bool = True,
        include_traceability: bool = True,
        use_llm: bool | None = None,
        model: str | None = None,
    ) -> dict:
        policy = self._load_policy()

        existing = (
            self.db.query(EvidenceDossier)
            .filter(EvidenceDossier.review_case_id == review_case_id)
            .order_by(EvidenceDossier.created_at.desc())
            .first()
        )
        if existing and not force_regenerate:
            return self._dossier_to_dict(existing)

        context = self.evidence_service.build_agent_context(review_case_id)

        llm_decision = self._should_use_llm(use_llm)
        llm_metadata = {
            "llm_requested": llm_decision,
            "llm_used": False,
            "llm_provider": None,
            "llm_model": None,
            "llm_error": None,
        }

        if llm_decision:
            result = ClaudeLlmService().generate_dossier_sections(context, policy, model=model)
            llm_metadata.update(
                {
                    "llm_used": result.used_llm,
                    "llm_provider": result.provider,
                    "llm_model": result.model,
                    "llm_error": result.error,
                }
            )
            if result.used_llm and result.text:
                parsed = self._parse_llm_dossier(result.text)
                combined_text = "\n".join(parsed.values())
                validation = self.validate_text_against_policy(combined_text, policy)
                if validation["passed"]:
                    return self._save_dossier(
                        review_case_id=review_case_id,
                        context=context,
                        executive_summary=parsed["executive_summary"],
                        technical_summary=parsed["technical_summary"] if include_technical_summary else "Resumen técnico omitido por configuración.",
                        limitations=parsed["limitations"],
                        recommended_next_steps=parsed["recommended_next_steps"],
                        generated_by=f"claude_llm:{result.model}",
                        language_policy_status="PASSED",
                        dossier_status="GENERATED",
                        llm_metadata=llm_metadata,
                    )
                llm_metadata["llm_error"] = f"Policy validation failed: {validation}"

        # Fallback deterministic
        review_case = context["review_case"]
        evidence_items = context["evidence_items"]
        score_components = context["score_components"]

        executive_summary = self._build_executive_summary(review_case, evidence_items, policy)
        technical_summary = self._build_technical_summary(review_case, evidence_items, score_components)
        limitations = self._build_limitations(context, policy)
        recommended_next_steps = self._build_next_steps(review_case, evidence_items)

        combined_text = "\n".join([
            executive_summary,
            technical_summary,
            limitations,
            recommended_next_steps,
            policy["required_disclaimer"],
        ])

        validation = self.validate_text_against_policy(combined_text, policy)
        dossier_status = "GENERATED" if validation["passed"] else "FAILED_POLICY"
        language_policy_status = "PASSED" if validation["passed"] else "FAILED"

        return self._save_dossier(
            review_case_id=review_case_id,
            context=context,
            executive_summary=executive_summary + "\n\n" + policy["required_disclaimer"],
            technical_summary=technical_summary if include_technical_summary else "Resumen técnico omitido por configuración.",
            limitations=limitations,
            recommended_next_steps=recommended_next_steps,
            generated_by="deterministic_agent_v0.1",
            language_policy_status=language_policy_status,
            dossier_status=dossier_status,
            llm_metadata=llm_metadata,
        )

    def _should_use_llm(self, use_llm: bool | None) -> bool:
        if use_llm is not None:
            return use_llm
        if self.settings.llm_enabled.lower() in ["0", "false", "no", "off", "disabled"]:
            return False
        if self.settings.llm_enabled.lower() in ["1", "true", "yes", "on", "enabled"]:
            return True
        return bool(self.settings.anthropic_api_key.strip())

    def _parse_llm_dossier(self, text: str) -> dict:
        sections = {
            "executive_summary": "",
            "technical_summary": "",
            "limitations": "",
            "recommended_next_steps": "",
        }

        current = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            upper = line.upper().replace("#", "").strip()
            if upper == "RESUMEN_EJECUTIVO":
                current = "executive_summary"
                continue
            if upper == "RESUMEN_TECNICO":
                current = "technical_summary"
                continue
            if upper == "LIMITACIONES":
                current = "limitations"
                continue
            if upper == "SIGUIENTES_PASOS":
                current = "recommended_next_steps"
                continue
            if current:
                sections[current] += raw_line + "\n"

        # If parsing fails, keep all text as executive summary and deterministic placeholders.
        if not any(value.strip() for value in sections.values()):
            sections["executive_summary"] = text
            sections["technical_summary"] = "Resumen técnico no estructurado por el LLM."
            sections["limitations"] = "La salida fue generada por LLM y requiere revisión humana."
            sections["recommended_next_steps"] = "Revisar manualmente el caso y contrastar con fuentes oficiales."

        return {key: value.strip() for key, value in sections.items()}

    def _save_dossier(
        self,
        review_case_id: uuid.UUID,
        context: dict,
        executive_summary: str,
        technical_summary: str,
        limitations: str,
        recommended_next_steps: str,
        generated_by: str,
        language_policy_status: str,
        dossier_status: str,
        llm_metadata: dict | None = None,
    ) -> dict:
        dossier = EvidenceDossier(
            review_case_id=review_case_id,
            generated_by=generated_by,
            dossier_status=dossier_status,
            executive_summary=executive_summary,
            technical_summary=technical_summary,
            limitations=limitations,
            recommended_next_steps=recommended_next_steps,
            language_policy_status=language_policy_status,
        )
        self.db.add(dossier)
        self.db.flush()

        review_case = context["review_case"]
        trace_event = TraceabilityEvent(
            ingestion_run_id=uuid.UUID(review_case["ingestion_run_id"]),
            entity_type="REVIEW_CASE",
            entity_id=str(review_case_id),
            event_type="DOSSIER_GENERATED",
            event_description=f"Se generó evidence_dossier con estado {dossier_status} usando {generated_by}.",
        )
        self.db.add(trace_event)
        self.db.commit()

        data = self._dossier_to_dict(dossier)
        data["llm"] = llm_metadata or {
            "llm_requested": False,
            "llm_used": False,
            "llm_provider": None,
            "llm_model": None,
            "llm_error": None,
        }
        return data

    def get_dossier(self, review_case_id: uuid.UUID) -> dict:
        dossier = (
            self.db.query(EvidenceDossier)
            .filter(EvidenceDossier.review_case_id == review_case_id)
            .order_by(EvidenceDossier.created_at.desc())
            .first()
        )
        if dossier is None:
            raise ValueError(f"Evidence dossier not found for review_case_id: {review_case_id}")
        return self._dossier_to_dict(dossier)

    def _build_executive_summary(self, review_case: dict, evidence_items: list[dict], policy: dict) -> str:
        priority = review_case["priority"]
        score = review_case["review_priority_score"]
        confidence = review_case["statistical_confidence"]
        evidence_count = len(evidence_items)

        strongest = sorted(
            evidence_items,
            key=lambda item: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(item["strength"], 0),
            reverse=True,
        )[:3]

        lines = [
            "Resumen ejecutivo",
            "Resumen ejecutivo del caso de revisión.",
            f"El caso presenta prioridad {priority}, score de revisión {score:.2f} y confianza estadística {confidence}.",
            f"Se reunieron {evidence_count} piezas de evidencia estructurada.",
        ]
        if strongest:
            lines.append("Principales señales observadas:")
            for item in strongest:
                lines.append(f"- {item['evidence_type']}: {item['description']}")
        return "\n".join(lines)

    def _build_technical_summary(self, review_case: dict, evidence_items: list[dict], score_components: list[dict]) -> str:
        lines = [
            "Resumen técnico.",
            f"Entidad analizada: {review_case['entity_level']} / {review_case['entity_id']}.",
            f"Estado del caso: {review_case['status']}.",
            "Componentes principales del score:",
        ]

        for component in score_components[:10]:
            lines.append(
                f"- {component['component_type']} | {component['component_name']} | "
                f"{component['points']:.2f} puntos: {component['explanation']}"
            )

        lines.append("Evidencia estructurada:")
        for item in evidence_items[:10]:
            metric_part = ""
            if item.get("metric_name"):
                metric_part = f" Métrica: {item['metric_name']}={item.get('metric_value')}."
            lines.append(f"- {item['strength']} | {item['evidence_type']}:{metric_part} {item['description']}")

        return "\n".join(lines)

    def _build_limitations(self, context: dict, policy: dict) -> str:
        limits = list(context.get("methodological_limits", []))
        limits.extend([
            "El dossier fue generado a partir de datos estructurados.",
            "No se incorporó revisión visual de actas, imágenes, OCR ni testimonios.",
            "La calidad del resultado depende de la calidad y completitud del archivo fuente.",
        ])
        return "\n".join(f"- {limit}" for limit in limits)

    def _build_next_steps(self, review_case: dict, evidence_items: list[dict]) -> str:
        steps = [
            "Revisar el caso con un analista humano.",
            "Contrastar las señales con actas oficiales, si están disponibles.",
            "Verificar la trazabilidad del archivo fuente y versiones de reglas usadas.",
            "Comparar el caso con otros puestos o municipios antes de tomar decisiones.",
        ]
        if any(item["strength"] in ["HIGH", "CRITICAL"] for item in evidence_items):
            steps.append("Priorizar revisión documental por presencia de evidencia de fuerza alta o crítica.")
        return "\n".join(f"- {step}" for step in steps)

    def _dossier_to_dict(self, dossier: EvidenceDossier) -> dict:
        return {
            "evidence_dossier_id": str(dossier.evidence_dossier_id),
            "review_case_id": str(dossier.review_case_id),
            "generated_by": dossier.generated_by,
            "generated_at": dossier.generated_at.isoformat() if dossier.generated_at else None,
            "dossier_status": dossier.dossier_status,
            "executive_summary": dossier.executive_summary,
            "technical_summary": dossier.technical_summary,
            "limitations": dossier.limitations,
            "recommended_next_steps": dossier.recommended_next_steps,
            "language_policy_status": dossier.language_policy_status,
        }
