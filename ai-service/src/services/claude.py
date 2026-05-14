import base64
import io
from PIL import Image
import google.generativeai as genai
from src.config import settings

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self.temperature = settings.temperature

    def analyze_dashboard(self, image_data: str, query: str, context: str = "") -> dict:
        """
        Analyze a PowerBI dashboard image using Gemini Vision.

        Args:
            image_data: Base64 encoded image data
            query: User's question about the dashboard
            context: Additional context from chat history

        Returns:
            Raw response from Gemini API as dict containing:
            - response text and metadata
        """
        # Build system prompt
        system_prompt = """You are an expert PowerBI analyst. You analyze dashboard images and answer questions about the data, visualizations, and insights.

When analyzing dashboards:
1. Identify all key visualizations and metrics
2. Understand the data hierarchy and relationships
3. Provide clear, actionable insights
4. Answer specific questions about the data shown
5. Suggest additional analysis if relevant

Be concise but thorough in your responses."""

        # Build user message with image and query
        user_message = f"""{"Previous context:\n" + context if context else ""}

Please analyze this PowerBI dashboard image and answer the following question:

{query}"""

        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Call Gemini API with vision
        client = genai.GenerativeModel(
            model_name=self.model,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
            ),
            system_instruction=system_prompt,
        )

        response = client.generate_content(
            [user_message, image],
            stream=False,
        )

        # Return raw response as dict
        return {
            "text": response.text,
            "model": self.model,
            "usage": {
                "prompt_tokens": None,
                "completion_tokens": None,
            },
            "finish_reason": response.candidates[0].finish_reason if response.candidates else None,
        }

gemini_service = GeminiService()
