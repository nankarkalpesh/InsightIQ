from typing import List, Optional
from pydantic import BaseModel, Field

class ColumnMetadata(BaseModel):
    name: str
    dtype: str

class DatasetMetadataResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    file_size: int
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[List[ColumnMetadata]] = None
    sheet_names: Optional[List[str]] = None
    selected_sheet: Optional[str] = None
    requires_sheet_selection: bool = False

class SelectSheetRequest(BaseModel):
    file_id: str = Field(..., description="ID or stored filename reference of uploaded dataset")
    sheet_name: str = Field(..., description="Name of the Excel sheet to parse")
