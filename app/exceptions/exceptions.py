"""
Custom exception classes for the Search API.
"""


class APIException(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SearchException(APIException):
    """Exception raised for search-related errors."""
    
    def __init__(self, message: str = "Search operation failed"):
        super().__init__(message, 400)


class ExternalAPIError(APIException):
    """Exception raised when external API fails."""
    
    def __init__(self, message: str = "External API request failed"):
        super().__init__(message, 502)
