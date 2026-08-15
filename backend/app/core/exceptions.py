from fastapi import Request, status
from fastapi.responses import JSONResponse

class IngestionError(Exception):
    """Base exception for data ingestion errors."""
    def __init__(self, message: str, error_code: str = "INGESTION_ERROR", status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class UnsupportedTypeError(IngestionError):
    def __init__(self, message: str = "Unsupported file type."):
        super().__init__(message=message, error_code="UNSUPPORTED_FILE_TYPE", status_code=status.HTTP_400_BAD_REQUEST)

class EmptyFileError(IngestionError):
    def __init__(self, message: str = "Uploaded file is empty."):
        super().__init__(message=message, error_code="EMPTY_FILE", status_code=status.HTTP_400_BAD_REQUEST)

class CorruptedFileError(IngestionError):
    def __init__(self, message: str = "File is corrupted or unparseable."):
        super().__init__(message=message, error_code="CORRUPTED_FILE", status_code=status.HTTP_400_BAD_REQUEST)

class SheetNotFoundError(IngestionError):
    def __init__(self, message: str = "Selected sheet was not found."):
        super().__init__(message=message, error_code="SHEET_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

class FileNotFoundErrorCustom(IngestionError):
    def __init__(self, message: str = "File reference not found."):
        super().__init__(message=message, error_code="FILE_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)


async def ingestion_error_handler(request: Request, exc: IngestionError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "error_code": exc.error_code,
                "message": exc.message
            }
        }
    )
