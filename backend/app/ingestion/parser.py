import os
from pathlib import Path
from typing import List, Union, Optional
import pandas as pd

from app.core.exceptions import (
    UnsupportedTypeError,
    EmptyFileError,
    CorruptedFileError,
    SheetNotFoundError,
    FileNotFoundErrorCustom
)

SUPPORTED_TYPES = {"csv", "xlsx", "xls", "json", "parquet"}


def normalize_file_type(file_type_or_extension: str) -> str:
    ext = file_type_or_extension.lower().strip()
    if ext.startswith("."):
        ext = ext[1:]
    return ext


def get_excel_sheet_names(file_path: Union[str, Path]) -> List[str]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundErrorCustom(f"File not found at path: {path}")

    if os.path.getsize(path) == 0:
        raise EmptyFileError("Excel file is empty (0 bytes).")

    try:
        with pd.ExcelFile(path) as excel_file:
            return excel_file.sheet_names
    except Exception as e:
        raise CorruptedFileError(f"Unable to read Excel workbook sheets: {str(e)}")


def parse_file(
    file_path: Union[str, Path],
    file_type: str,
    sheet_name: Optional[Union[str, int]] = None
) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundErrorCustom(f"File not found: {path.name}")

    if os.path.getsize(path) == 0:
        raise EmptyFileError("File is empty (0 bytes).")

    normalized_type = normalize_file_type(file_type)
    if normalized_type not in SUPPORTED_TYPES:
        raise UnsupportedTypeError(f"Unsupported file type '{file_type}'. Supported types: CSV, XLSX, XLS, JSON, Parquet.")

    try:
        if normalized_type == "csv":
            df = pd.read_csv(path)
        elif normalized_type in ("xlsx", "xls"):
            sheet_names = get_excel_sheet_names(path)
            if sheet_name is not None:
                if isinstance(sheet_name, str) and sheet_name not in sheet_names:
                    raise SheetNotFoundError(f"Sheet '{sheet_name}' not found in workbook. Available sheets: {sheet_names}")
                df = pd.read_excel(path, sheet_name=sheet_name)
            else:
                # Default to first sheet if not specified
                df = pd.read_excel(path, sheet_name=0)
        elif normalized_type == "json":
            try:
                df = pd.read_json(path)
            except Exception:
                # Try orient='records' or lines=True as fallback for JSON
                try:
                    df = pd.read_json(path, lines=True)
                except Exception as ex:
                    raise CorruptedFileError(f"Unable to parse JSON file: {str(ex)}")
        elif normalized_type == "parquet":
            df = pd.read_parquet(path)
        else:
            raise UnsupportedTypeError(f"Unsupported file type '{file_type}'.")

        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        return df
    except (UnsupportedTypeError, EmptyFileError, SheetNotFoundError, FileNotFoundErrorCustom):
        raise
    except Exception as e:
        raise CorruptedFileError(f"Failed to parse file '{path.name}': {str(e)}")
