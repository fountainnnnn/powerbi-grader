from fastapi import APIRouter, HTTPException, status
from src.models.schemas import GradeRequest, GradeResponse
from src.services.claude import gemini_service

router = APIRouter()

@router.post("/grade", response_model=GradeResponse)
async def grade_dashboard(request: GradeRequest):
    """
    Analyze a PowerBI dashboard image using Gemini Vision.

    Returns the raw Gemini API response as JSON.
    """
    try:
        # Call Gemini to analyze the dashboard
        response = gemini_service.analyze_dashboard(
            image_data=request.image_data,
            query=request.query,
            context=request.context,
        )

        # Return raw Gemini response
        return GradeResponse(response=response)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing dashboard: {str(e)}"
        )
