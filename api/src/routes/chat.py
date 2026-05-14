from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.chat import ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse
from src.services.chat_service import chat_service
from src.utils.errors import NotFoundError, ChatServiceError, AIServiceError

router = APIRouter()

@router.post("", response_model=ChatMessageResponse)
def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """Send a message to get insights about a dashboard."""
    try:
        response = chat_service.send_message(
            db=db,
            dashboard_id=request.dashboard_id,
            pbix_id=request.pbix_id,
            message=request.message,
            student_name=request.student_name,
        )
        return ChatMessageResponse(
            id=response['id'],
            dashboard_id=response['dashboard_id'],
            pbix_id=response.get('pbix_id'),
            student_name=response.get('student_name'),
            user_message=response['user_message'],
            ai_response=response['ai_response'],
            created_at=response['created_at'],
            dashboard_filename=response.get('dashboard_filename'),
            dashboard_file_path=response.get('dashboard_file_path'),
            pbix_filename=response.get('pbix_filename'),
            pbix_file_path=response.get('pbix_file_path'),
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unavailable"
        )
    except ChatServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history(
    db: Session = Depends(get_db),
):
    """Get global chat history."""
    try:
        messages = chat_service.get_chat_history(db=db)
        message_responses = []
        for m in messages:
            msg_response = ChatMessageResponse(
                id=m['id'],
                dashboard_id=m['dashboard_id'],
                pbix_id=m.get('pbix_id'),
                student_name=m.get('student_name'),
                user_message=m['user_message'],
                ai_response=m['ai_response'],
                created_at=m['created_at'],
                dashboard_filename=m.get('dashboard_filename'),
                dashboard_file_path=m.get('dashboard_file_path'),
                pbix_filename=m.get('pbix_filename'),
                pbix_file_path=m.get('pbix_file_path'),
            )
            message_responses.append(msg_response)
        return ChatHistoryResponse(
            messages=message_responses,
            total=len(message_responses),
        )

    except ChatServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
