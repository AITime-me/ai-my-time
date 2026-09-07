import uuid

from fastapi import APIRouter, Header, HTTPException, Request

from app.db.dependencies import get_session_factory
from app.db.session import session_scope
from app.schemas.assistant import PublicAssistantMessageCreate, PublicConversationCreate, PublicConversationCreated, PublicIntakeCreate, IntakeView
from app.services.assistant_boundary import AssistantBoundaryService

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/conversations", response_model=PublicConversationCreated, status_code=201)
async def create_conversation(payload: PublicConversationCreate, request: Request) -> PublicConversationCreated:
    async with session_scope(get_session_factory(request)) as session:
        try: row, token = await AssistantBoundaryService(session).create_conversation(payload.channel)
        except ValueError: raise HTTPException(status_code=503, detail="assistant is unavailable") from None
        return PublicConversationCreated(conversation_id=row.id, session_token=token)


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def message(conversation_id: uuid.UUID, payload: PublicAssistantMessageCreate, request: Request, x_assistant_session: str | None = Header(default=None)) -> dict[str, object]:
    if not x_assistant_session: raise HTTPException(status_code=401, detail="assistant session is required")
    async with session_scope(get_session_factory(request)) as session:
        row = await AssistantBoundaryService(session).message(conversation_id, x_assistant_session, payload.content)
        if row is None: raise HTTPException(status_code=404, detail="conversation not found")
        return {"message_id": str(row.id), "created_at": row.created_at}


@router.post("/conversations/{conversation_id}/intakes", response_model=IntakeView, status_code=201)
async def intake(conversation_id: uuid.UUID, payload: PublicIntakeCreate, request: Request, x_assistant_session: str | None = Header(default=None)) -> IntakeView:
    if not x_assistant_session: raise HTTPException(status_code=401, detail="assistant session is required")
    async with session_scope(get_session_factory(request)) as session:
        row = await AssistantBoundaryService(session).intake(conversation_id, x_assistant_session, **payload.model_dump())
        if row is None: raise HTTPException(status_code=404, detail="conversation not found")
        return IntakeView.model_validate(row)
