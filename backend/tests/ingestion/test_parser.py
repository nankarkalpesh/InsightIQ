import os
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from app.ingestion.parser import parse_file, get_excel_sheet_names
from app.core.exceptions import (
    UnsupportedTypeError,
    EmptyFileError,
    CorruptedFileError,
    SheetNotFoundError,
    FileNotFoundErrorCustom
)


def test_parse_valid_csv():
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tmp:
        tmp.write("id,name,val\n1,Alice,10.5\n2,Bob,20.0\n")
        tmp_path = tmp.name

    try:
        df = parse_file(tmp_path, "csv")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["id", "name", "val"]
        assert df["name"].tolist() == ["Alice", "Bob"]
    finally:
        os.unlink(tmp_path)


def test_parse_valid_xlsx_multi_sheet():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df_sheet1 = pd.DataFrame({"col_a": [1, 2], "col_b": ["x", "y"]})
        df_sheet2 = pd.DataFrame({"metrics": [100, 200]})
        with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
            df_sheet1.to_excel(writer, sheet_name="Summary", index=False)
            df_sheet2.to_excel(writer, sheet_name="Details", index=False)

        # Test sheet name list extraction
        sheets = get_excel_sheet_names(tmp_path)
        assert sheets == ["Summary", "Details"]

        # Test reading specific sheet
        parsed_summary = parse_file(tmp_path, "xlsx", sheet_name="Summary")
        assert len(parsed_summary) == 2
        assert list(parsed_summary.columns) == ["col_a", "col_b"]

        parsed_details = parse_file(tmp_path, "xlsx", sheet_name="Details")
        assert len(parsed_details) == 2
        assert list(parsed_details.columns) == ["metrics"]
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_parse_valid_json():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
        tmp.write('[{"category": "tech", "score": 98}, {"category": "health", "score": 85}]')
        tmp_path = tmp.name

    try:
        df = parse_file(tmp_path, "json")
        assert len(df) == 2
        assert list(df.columns) == ["category", "score"]
        assert df["score"].tolist() == [98, 85]
    finally:
        os.unlink(tmp_path)


def test_parse_empty_file():
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tmp:
        tmp_path = tmp.name  # 0 bytes

    try:
        with pytest.raises(EmptyFileError):
            parse_file(tmp_path, "csv")
    finally:
        os.unlink(tmp_path)


def test_parse_corrupted_file():
    with tempfile.NamedTemporaryFile(suffix=".parquet", mode="wb", delete=False) as tmp:
        tmp.write(b"NOT_A_VALID_PARQUET_FILE_HEADER_BINARY_GARBAGE")
        tmp_path = tmp.name

    try:
        with pytest.raises(CorruptedFileError):
            parse_file(tmp_path, "parquet")
    finally:
        os.unlink(tmp_path)


def test_parse_unsupported_extension():
    with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as tmp:
        tmp.write("data")
        tmp_path = tmp.name

    try:
        with pytest.raises(UnsupportedTypeError):
            parse_file(tmp_path, "xyz")
    finally:
        os.unlink(tmp_path)
