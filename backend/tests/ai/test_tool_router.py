import pytest
import pandas as pd
from app.core.session import store_dataset, clear_all_sessions
from app.analytics.profiling import dataset_health
from app.analytics.chart_engine import recommend_charts
from app.ai.tool_router import (
    TOOL_REGISTRY,
    get_dataset_summary,
    calculate_statistic,
    aggregate_data,
    find_top_categories,
    recommend_chart,
    dispatch_tool_call
)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_tool_registry_schema():
    assert isinstance(TOOL_REGISTRY, list)
    assert len(TOOL_REGISTRY) >= 4

    tool_names = [t["function"]["name"] for t in TOOL_REGISTRY if t.get("type") == "function"]
    assert "get_dataset_summary" in tool_names
    assert "calculate_statistic" in tool_names
    assert "aggregate_data" in tool_names
    assert "recommend_chart" in tool_names

    summary_tool = next(t for t in TOOL_REGISTRY if t["function"]["name"] == "get_dataset_summary")
    params = summary_tool["function"]["parameters"]
    assert params["type"] == "object"
    assert "file_id" in params["properties"]


def test_get_dataset_summary_function_matches_profiling():
    """
    Assert get_dataset_summary via tool_router returns identical data
    to calling profiling.py (dataset_health) directly on the same uploaded test file.
    """
    df = pd.DataFrame({
        "col_a": [1, 2, 3, None, 5],
        "col_b": ["x", "y", "z", "w", "v"]
    })
    file_id = "test_file_summary_123"
    store_dataset(file_id, df)

    direct_health = dataset_health(df)
    summary = get_dataset_summary(file_id)

    assert summary["total_rows"] == direct_health["total_rows"] == 5
    assert summary["total_columns"] == direct_health["total_columns"] == 2
    assert summary["column_names"] == [str(c) for c in df.columns]
    assert summary["health_score"] == direct_health["quality_score"]


def test_dispatch_tool_call_success():
    df = pd.DataFrame({
        "age": [20, 30, 40],
        "income": [50000, 60000, 70000]
    })
    file_id = "test_file_dispatch"
    store_dataset(file_id, df)

    result = dispatch_tool_call("get_dataset_summary", {"file_id": file_id}, file_id=file_id)
    assert result["total_rows"] == 3
    assert result["total_columns"] == 2
    assert result["column_names"] == ["age", "income"]
    assert "health_score" in result


def test_dispatch_tool_call_authoritative_file_id_override():
    """
    Assert dispatch_tool_call uses the route's authoritative file_id even if arguments
    contain a wrong or missing file_id.
    """
    df = pd.DataFrame({"x": [10, 20]})
    real_file_id = "real_file_id_123"
    store_dataset(real_file_id, df)

    # Pass wrong file_id in arguments dict, but real_file_id as the authoritative file_id arg
    result = dispatch_tool_call("get_dataset_summary", {"file_id": "WRONG_FILE_ID"}, file_id=real_file_id)

    assert result["total_rows"] == 2
    assert result["column_names"] == ["x"]


def test_dispatch_tool_call_unknown_tool():
    with pytest.raises(ValueError, match="not registered"):
        dispatch_tool_call("non_existent_tool", {}, file_id="file_123")


def test_dispatch_tool_call_fake_user_message_tool_rejected():
    with pytest.raises(ValueError, match="not registered"):
        dispatch_tool_call("get_user_message", {"user_id": "1"}, file_id="file_123")


def test_calculate_statistic_success():
    df = pd.DataFrame({
        "score": [10.0, 20.0, 30.0, 40.0]
    })
    file_id = "test_calc_stat_real"
    store_dataset(file_id, df)

    res = calculate_statistic(file_id, column_name="score", statistic="mean")
    assert res["column"] == "score"
    assert res["statistic"] == "mean"
    assert res["value"] == df["score"].mean() == 25.0


def test_calculate_statistic_rejects_coordinate_column():
    df = pd.DataFrame({
        "latitude": [37.7749, 34.0522],
        "score": [10, 20]
    })
    file_id = "test_calc_coord"
    store_dataset(file_id, df)

    res = calculate_statistic(file_id, column_name="latitude", statistic="mean")
    assert res.get("error") == "invalid_column_type"
    assert "coordinate" in res.get("message", "").lower()


def test_calculate_statistic_rejects_mean_on_non_numeric():
    df = pd.DataFrame({
        "category": ["A", "B", "C"]
    })
    file_id = "test_calc_non_num"
    store_dataset(file_id, df)

    res = calculate_statistic(file_id, column_name="category", statistic="mean")
    assert res.get("error") == "non_numeric_column"
    assert "non-numeric" in res.get("message", "").lower()


def test_calculate_statistic_unknown_column():
    df = pd.DataFrame({
        "col1": [1, 2]
    })
    file_id = "test_calc_unknown"
    store_dataset(file_id, df)

    res = calculate_statistic(file_id, column_name="missing_col", statistic="sum")
    assert res.get("error") == "column_not_found"
    assert "available_columns" in res
    assert "col1" in res["available_columns"]


def test_aggregate_data_success():
    df = pd.DataFrame({
        "category": ["A", "A", "B", "B", "C"],
        "amount": [100, 200, 300, 400, 500]
    })
    file_id = "test_agg_success"
    store_dataset(file_id, df)

    res = aggregate_data(file_id, group_by_column="category", value_column="amount", aggregation="sum")
    assert res["group_by_column"] == "category"
    assert res["value_column"] == "amount"
    assert res["aggregation"] == "sum"
    assert res["total_groups"] == 3

    direct_groupby = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    for idx, row in enumerate(res["results"]):
        assert row["group"] == direct_groupby.index[idx]
        assert row["value"] == direct_groupby.iloc[idx]


def test_aggregate_data_capped_at_20_groups():
    categories_base = [
        "Division_North", "District_South", "Zone_East", "Region_West", "Sector_Central",
        "Block_Midtown", "Area_Uptown", "Quarters_Downtown", "Borough_Suburbs", "Ward_Metro",
        "County_Rural", "State_Capital", "Province_Coastal", "Territory_Highland", "Domain_Valley",
        "Realm_Desert", "Station_Harbor", "Base_Airport", "Node_Port", "Hub_Station",
        "Point_Junction", "Site_Square", "Spot_Park", "Loc_Plaza", "Zone_Center"
    ]
    categories = [categories_base[i % 25] for i in range(1000)]
    amounts = list(range(1000))
    df = pd.DataFrame({"category": categories, "amount": amounts})
    file_id = "test_agg_cap"
    store_dataset(file_id, df)

    res = aggregate_data(file_id, group_by_column="category", value_column="amount", aggregation="sum")
    assert res["total_groups"] == 25
    assert len(res["results"]) == 20


def test_aggregate_data_rejects_coordinate_column():
    df = pd.DataFrame({
        "latitude": [37.77, 34.05],
        "amount": [100, 200]
    })
    file_id = "test_agg_coord"
    store_dataset(file_id, df)

    res = aggregate_data(file_id, group_by_column="latitude", value_column="amount", aggregation="sum")
    assert "error" in res
    assert res["error"] == "invalid_group_by_column"


def test_calculate_statistic_currency_coercion():
    """
    Test that currency string columns like property_loss_usd (e.g. '$1,250.00')
    are coerced to numeric float64 automatically when calculating statistics.
    """
    df = pd.DataFrame({
        "property_loss_usd": ["$1,000.00", "$2,500.50", "$500.00", None]
    })
    file_id = "test_currency_coercion"
    store_dataset(file_id, df)

    res = calculate_statistic(file_id, column_name="property_loss_usd", statistic="sum")
    assert "error" not in res
    assert res["column"] == "property_loss_usd"
    assert res["statistic"] == "sum"
    assert res["value"] == 4000.50


def test_recommend_chart_resolves_user_requested_columns():
    """
    Test that recommend_chart matches user requested columns even when passed as
    a single string, plural/space variations ('weapons used'), or fuzzy names.
    """
    df = pd.DataFrame({
        "weapon_used": ["Knife", "Gun", "Knife", "Hands"],
        "suspect_age": [25, 30, 35, 40],
        "incident_datetime": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
    })
    file_id = "test_rec_weapon_used"
    store_dataset(file_id, df)

    res = recommend_chart(file_id, columns_of_interest="weapons used")
    assert "error" not in res
    assert res["x_axis"] == "weapon_used"
    assert res["chart_type"] in {"bar", "column"}


def test_recommend_chart_matches_chart_engine():
    df = pd.DataFrame({
        "category": ["A", "B", "C"],
        "sales": [100, 200, 300]
    })
    file_id = "test_rec_chart"
    store_dataset(file_id, df)

    tool_rec = recommend_chart(file_id, columns_of_interest=["category", "sales"])
    direct_rec = recommend_charts(df)

    assert direct_rec["total_charts"] > 0
    top_direct = direct_rec["charts"][0]
    assert tool_rec["chart_type"] == top_direct["chart_type"]
    assert tool_rec["x_axis"] == top_direct["x_axis"]
    assert tool_rec["y_axis"] == top_direct["y_axis"]
    assert top_direct["aggregation"] == tool_rec["aggregation"]


def test_aggregate_data_normalizes_case_and_whitespace():
    df = pd.DataFrame({
        "district": ["Central", "central", " Central", "North", "north "],
        "arrests": [10, 20, 30, 40, 50]
    })
    file_id = "test_agg_norm"
    store_dataset(file_id, df)

    res = aggregate_data(file_id, group_by_column="district", value_column="arrests", aggregation="sum")
    assert res["total_groups"] == 2
    groups_dict = {row["group"]: row["value"] for row in res["results"]}

    assert "Central" in groups_dict
    assert groups_dict["Central"] == 60

    assert "North" in groups_dict
    assert groups_dict["North"] == 90


def test_aggregate_data_prefix_abbreviations_district():
    df = pd.DataFrame({
        "district": ["Central", "Cen", "North", "Northeast", "Nor", "West", "Wes"],
        "num_arrests": [10, 20, 30, 40, 50, 60, 70]
    })
    file_id = "test_agg_prefix"
    store_dataset(file_id, df)

    res = aggregate_data(file_id, group_by_column="district", value_column="num_arrests", aggregation="sum")
    groups_dict = {row["group"]: row["value"] for row in res["results"]}

    assert "Central" in groups_dict
    assert groups_dict["Central"] == 30

    assert "West" in groups_dict
    assert groups_dict["West"] == 130

    assert "Nor" in groups_dict
    assert groups_dict["Nor"] == 50
    assert "ambiguous_abbreviations" in res
    assert "Nor" in res["ambiguous_abbreviations"]


def test_find_top_categories_success():
    df = pd.DataFrame({
        "weapon_used": ["Knife", "Knife", "Firearm", "Knife", "Hands", "Firearm", "Other"]
    })
    file_id = "test_top_categories_123"
    store_dataset(file_id, df)

    res = find_top_categories(file_id, column_name="weapon_used", top_n=5)
    assert res["column"] == "weapon_used"
    assert res["total_valid_rows"] == 7
    assert len(res["categories"]) == 4

    top_cat = res["categories"][0]
    assert top_cat["category"] == "Knife"
    assert top_cat["count"] == 3
    assert top_cat["percentage"] == round((3 / 7) * 100, 2)


def test_find_top_categories_dispatch():
    df = pd.DataFrame({
        "crime_type": ["Theft", "Theft", "Assault", "Theft", "Robbery"]
    })
    file_id = "test_top_cat_dispatch"
    store_dataset(file_id, df)

    res = dispatch_tool_call(
        tool_name="find_top_categories",
        arguments={"column_name": "crime_type", "top_n": 3},
        file_id=file_id
    )
    assert res["column"] == "crime_type"
    assert res["total_valid_rows"] == 5
    assert res["categories"][0]["category"] == "Theft"
    assert res["categories"][0]["count"] == 3
    assert res["categories"][0]["percentage"] == 60.0
