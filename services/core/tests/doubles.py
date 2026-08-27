"""Deterministic diagnostic provider used by tests only, never by application runtime."""

from __future__ import annotations

from app.schemas.diagnostic_report import DiagnosticNextStepInput, DiagnosticPriorityInput, DiagnosticRoleSplitInput
from app.services.diagnostic_generation import (
    DiagnosticConversationInput,
    DiagnosticConversationResponse,
    GeneratedDiagnostic,
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
        return DiagnosticConversationResponse(diagnostic=GeneratedDiagnostic(
            summary=(f"Обращения из «{values['client_flow']}» проходят через «{values['current_tools']}». "
                     f"Гипотеза: сначала стоит снизить риск потери «{values['primary_pain']}»."),
            priorities=[DiagnosticPriorityInput(title="Сделать следующий шаг видимым", reason="Передача обращения не закрепляет ответственного и следующий шаг.", confidence="medium")],
            next_steps=[DiagnosticNextStepInput(title="Неделя прозрачных передач", action="В течение недели перед каждой передачей фиксируйте ответственного и следующий шаг в выбранном канале.")],
            limitations=["Нужно уточнить реальные роли и порядок передачи обращения."],
            role_split=DiagnosticRoleSplitInput(
                automation=["Фиксировать обращение, ответственного и следующий шаг"],
                ai=["Выделять суть свободного текста обращения"],
                human=["Решать нестандартные клиентские случаи"],
            ),
        ))
