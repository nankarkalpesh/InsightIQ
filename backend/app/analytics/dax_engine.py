def format_measure_name(name: str) -> str:
    """Sanitize measure name for DAX syntax."""
    clean = name.strip()
    return clean if clean else "Measure"


def generate_sum_dax(table_name: str, col_name: str, measure_name: str) -> str:
    """Generate DAX SUM measure using real column name."""
    m_name = format_measure_name(measure_name)
    return f"{m_name} = SUM('{table_name}'[{col_name}])"


def generate_average_dax(table_name: str, col_name: str, measure_name: str) -> str:
    """Generate DAX AVERAGE measure using real column name."""
    m_name = format_measure_name(measure_name)
    return f"{m_name} = AVERAGE('{table_name}'[{col_name}])"


def generate_count_rows_dax(table_name: str, measure_name: str) -> str:
    """Generate DAX COUNTROWS measure."""
    m_name = format_measure_name(measure_name)
    return f"{m_name} = COUNTROWS('{table_name}')"


def generate_distinct_count_dax(table_name: str, col_name: str, measure_name: str) -> str:
    """Generate DAX DISTINCTCOUNT measure using real column name."""
    m_name = format_measure_name(measure_name)
    return f"{m_name} = DISTINCTCOUNT('{table_name}'[{col_name}])"


def generate_ratio_dax(
    table_name: str,
    numerator_col: str,
    denominator_col: str,
    measure_name: str
) -> str:
    """Generate DAX DIVIDE ratio measure using real column names."""
    m_name = format_measure_name(measure_name)
    return f"{m_name} = DIVIDE(SUM('{table_name}'[{numerator_col}]), SUM('{table_name}'[{denominator_col}]), 0)"
