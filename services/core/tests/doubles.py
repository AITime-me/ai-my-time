"""Deterministic diagnostic provider used by tests only, never by application runtime."""

from __future__ import annotations

from app.schemas.diagnostic_result_v2 import DiagnosticResultV2
from app.services.diagnostic_generation import (
    DiagnosticConversationInput,
    DiagnosticConversationResponse,
)


class ScriptedDiagnosticProvider:
    async def advance(self, diagnostic_input: DiagnosticConversationInput) -> DiagnosticConversationResponse:
        answers = diagnostic_input.profile_snapshot["profile_answers"]
        values = {key: value["value"] for key, value in answers.items()}
        user_answers = [content for actor, content in diagnostic_input.turns if actor == "user"]
        if not user_answers:
            if values["current_tools"] in {"В чатах", "В нескольких местах", "Нигде системно"}:
                return DiagnosticConversationResponse(question=(
                    f"Когда новое обращение приходит через «{values['client_flow']}», кто первым его видит и где команда сейчас фиксирует следующий шаг?"
                ))
            return DiagnosticConversationResponse(question=(
                f"Когда обращение попадает в «{values['current_tools']}», на каком шаге команда чаще всего действует вручную?"
            ))
        if len(user_answers) == 1:
            return DiagnosticConversationResponse(question=(
                f"Вы описали: «{user_answers[0][:180]}». Где при этом чаще всего теряется «{values['primary_pain']}»?"
            ))
        return DiagnosticConversationResponse(diagnostic=DiagnosticResultV2.model_validate({
            "contract_version": "v2",
            "evidence": {"facts": [f"Обращения приходят через {values['client_flow']}"]},
            "mechanism": "Передача обращения не закрепляет ответственного и следующий шаг.",
            "problem_types": ["execution_gap", "observability_gap"],
            "problem_scale": "process",
            "solution_class_id": "lead_intake_contour",
            "client_view": {
                "what_is_happening": f"Обращения проходят через «{values['current_tools']}» и передаются вручную.",
                "where_result_is_lost": "После передачи не всегда видно ответственного и следующий шаг.",
                "future_process": "Каждое обращение фиксируется, получает ответственного и следующий шаг.",
                "system_responsibilities": ["Фиксировать обращение, ответственного и следующий шаг"],
                "human_responsibilities": ["Решать нестандартные клиентские случаи"],
                "open_questions": ["Нужно уточнить реальные роли и порядок передачи обращения."],
            },
        }))
