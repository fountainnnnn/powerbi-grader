class APIError(Exception):
    """Base exception for API errors."""
    pass

class AuthenticationError(APIError):
    """Authentication failed."""
    pass

class AuthorizationError(APIError):
    """Authorization failed."""
    pass

class NotFoundError(APIError):
    """Resource not found."""
    pass

class ValidationError(APIError):
    """Data validation failed."""
    pass

class FileUploadError(APIError):
    """File upload failed."""
    pass

class AIServiceError(APIError):
    """AI service error."""
    pass

class ChatServiceError(APIError):
    """Chat service error."""
    pass

class DatabaseError(APIError):
    """Database error."""
    pass
