from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies.current_user import get_current_user
from app.api.schemas.chat_message import (
    ChatHistoryMessageResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.application.use_cases.send_chat_message import SendChatMessage
from app.dependency_container import get_send_chat_message
from app.domain.interfaces.application_error import ApplicationError
from app.domain.models.user_identity import UserIdentity

router = APIRouter(tags=["chat"])


@router.post("/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    http_request: Request,
    current_user: Annotated[UserIdentity, Depends(get_current_user)],
    use_case: SendChatMessage = Depends(get_send_chat_message),
) -> ChatMessageResponse:
    reply = await use_case.execute(
        owner_id=current_user.owner_id,
        content=request.content,
        request_id=http_request.state.request_id,
        conversation_id=request.conversation_id,
    )
    if reply.conversation_id is None:
        raise ApplicationError(
            "The use case did not return a conversation ID.",
            code="conversation_id_missing",
            status_code=500,
        )

    return ChatMessageResponse(
        id=reply.id,
        message_id=reply.message_id,
        conversation_id=reply.conversation_id,
        chat_id=reply.chat_id,
        content=reply.content,
        timestamp=reply.timestamp,
        evaluation_score=reply.evaluation_score,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ChatHistoryMessageResponse],
)
async def get_conversation_history(
    conversation_id: str,
    current_user: Annotated[UserIdentity, Depends(get_current_user)],
    use_case: SendChatMessage = Depends(get_send_chat_message),
) -> list[ChatHistoryMessageResponse]:
    history = await use_case.get_history(
        conversation_id=conversation_id,
        owner_id=current_user.owner_id,
    )
    return [
        ChatHistoryMessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            timestamp=message.timestamp,
        )
        for message in history
    ]
