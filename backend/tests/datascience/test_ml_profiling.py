import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.session import clear_all_sessions
from app.datascience.ml_profiling import detect_ml_problem_hints, evaluate_feature_candidates

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_session():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_target_detection_classification_and_regression():
    data = {
        "churn": ["Yes", "No", "Yes", "No", "Yes", "No", "Yes", "No"],
        "status": ["Active", "Pending", "Closed", "Active", "Pending", "Closed", "Active", "Pending"],
        "monthly_charges": [50.0, 75.0, 60.0, 100.0, 45.0, 80.0, 90.0, 110.0]
    }
    df = pd.DataFrame(data)
    result = detect_ml_problem_hints(df)

    assert result["total_candidates"] == 3
    candidates_map = {c["column"]: c for c in result["candidates"]}

    # Churn binary classification
    assert "churn" in candidates_map
    assert candidates_map["churn"]["problem_type"] == "binary_classification"
    assert candidates_map["churn"]["unique_value_count"] == 2

    # Status multiclass classification
    assert "status" in candidates_map
    assert candidates_map["status"]["problem_type"] == "multiclass_classification"
    assert candidates_map["status"]["unique_value_count"] == 3

    # Monthly charges regression
    assert "monthly_charges" in candidates_map
    assert candidates_map["monthly_charges"]["problem_type"] == "regression"


def test_categorical_target_normalization_data_quality_note():
    data = {
        "suspect_gender": ["F", "female", "f", "Female", "FEMALE", "M", "male", "MALE", "f", "M"],
        "reported_online": ["0", "1", "yes", "Yes", "YES", "no", "No", "NO", "True", "False"],
        "resolution": ["Arres Made", "Arrest Made", "No Arrest", "No Arrest", "Arrest Made", "Arres Made", "No Arrest", "Arrest Made", "Arrest Made", "No Arrest"]
    }
    df = pd.DataFrame(data)
    result = detect_ml_problem_hints(df)

    candidates_map = {c["column"]: c for c in result["candidates"]}

    assert "suspect_gender" in candidates_map
    gender_c = candidates_map["suspect_gender"]
    assert gender_c["problem_type"] == "binary_classification"
    assert gender_c["unique_value_count"] == 2
    assert gender_c["raw_unique_value_count"] == 8
    assert gender_c["data_quality_note"] is not None
    assert "variants that normalize to 2 categories" in gender_c["data_quality_note"]

    assert "reported_online" in candidates_map
    online_c = candidates_map["reported_online"]
    assert online_c["problem_type"] == "binary_classification"
    assert online_c["unique_value_count"] == 2
    assert online_c["raw_unique_value_count"] == 10
    assert online_c["data_quality_note"] is not None

    assert "resolution" in candidates_map
    res_c = candidates_map["resolution"]
    assert res_c["unique_value_count"] == 2
    assert res_c["raw_unique_value_count"] == 3
    assert res_c["data_quality_note"] is not None


def test_regression_target_implausible_values_data_quality_note():
    data = {
        "suspect_age": [-75.0, 25.0, 30.0, 40.0, 298.0]
    }
    df = pd.DataFrame(data)
    result = detect_ml_problem_hints(df)

    assert result["total_candidates"] == 1
    age_c = result["candidates"][0]
    assert age_c["column"] == "suspect_age"
    assert age_c["problem_type"] == "regression"
    assert age_c["data_quality_note"] is not None
    assert "Contains implausible values" in age_c["data_quality_note"]
    assert "min=-75.0" in age_c["data_quality_note"]


def test_normalized_distribution_sum_invariant():
    # 500 rows dataset with messy gender variants and nulls
    genders = ["F", "female", "f", "Female", "FEMALE", "M", "male", "MALE", None, None] * 50
    data = {
        "suspect_gender": genders,
        "monthly_charges": [50.0 + i for i in range(500)]
    }
    df = pd.DataFrame(data)
    result = detect_ml_problem_hints(df)

    gender_c = next(c for c in result["candidates"] if c["column"] == "suspect_gender")

    null_count = int(df["suspect_gender"].isna().sum())
    total_non_null = len(df) - null_count

    # Invariant: sum of distribution counts MUST equal total non-null row count
    dist_sum = sum(gender_c["distribution"].values())
    assert dist_sum == total_non_null
    assert dist_sum == 400
    assert gender_c["distribution"]["Female"] == 250
    assert gender_c["distribution"]["Male"] == 150


def test_target_detection_never_includes_ids_coordinates_or_freetext():
    data = {
        "user_id": ["USR-1", "USR-2", "USR-3", "USR-4", "USR-5"],
        "badge_number": [101, 102, 103, 104, 105],
        "latitude": [37.7749, 37.7750, 37.7751, 37.7752, 37.7753],
        "longitude": [-122.4194, -122.4195, -122.4196, -122.4197, -122.4198],
        "description": [
            "Detailed narrative log regarding customer support inquiry and ticket resolution details.",
            "Officer notes regarding traffic incident investigation and patrol response timeline.",
            "Comprehensive investigation report detailing commercial burglary incident and evidence log.",
            "Customer feedback summary regarding service delivery and account cancellation request.",
            "Patrol unit report describing routine security audit and facility inspection notes."
        ],
        "churn": ["Yes", "No", "Yes", "No", "Yes"]
    }
    df = pd.DataFrame(data)
    result = detect_ml_problem_hints(df)

    candidate_cols = [c["column"] for c in result["candidates"]]
    excluded_cols = {"user_id", "badge_number", "latitude", "longitude", "description"}

    for col in excluded_cols:
        assert col not in candidate_cols, f"Excluded column '{col}' should not appear as ML target candidate"


def test_feature_candidate_exclusions():
    data = {
        "churn": ["Yes", "No", "Yes", "No"],
        "churn_status": ["Yes", "No", "Yes", "No"],  # Leakage
        "user_id": ["U1", "U2", "U3", "U4"],         # Identifier
        "missing_col": [1.0, None, None, None],       # >50% missing
        "tenure_months": [12, 24, 6, 48]            # Recommended feature
    }
    df = pd.DataFrame(data)
    result = evaluate_feature_candidates(df, target_col="churn")

    features_map = {f["column"]: f for f in result["features"]}

    assert features_map["churn_status"]["status"] == "excluded_leakage"
    assert features_map["user_id"]["status"] == "excluded_identifier"
    assert features_map["missing_col"]["status"] == "excluded_high_missing"
    assert features_map["tenure_months"]["status"] == "recommended"


def test_no_target_candidates_dataset():
    data = {
        "id": ["1", "2", "3"],
        "lat": [1.0, 2.0, 3.0]
    }
    df = pd.DataFrame(data)
    result = detect_ml_problem_hints(df)

    assert result["total_candidates"] == 0
    assert result["message"] is not None
    assert "No viable" in result["message"]


def test_ml_profiling_api_endpoints():
    csv_data = "user_id,churn,churn_flag,tenure,monthly_charges\nU101,Yes,1,12,65.0\nU102,No,0,24,80.0\nU103,Yes,1,6,45.0\nU104,No,0,36,95.0\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))

    upload_res = client.post(
        "/api/upload",
        files={"file": ("churn.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file_id"]

    # 1. Target candidates endpoint
    target_res = client.get(f"/api/dataset/{file_id}/target-candidates")
    assert target_res.status_code == 200
    target_json = target_res.json()

    assert target_json["file_id"] == file_id
    assert target_json["total_candidates"] > 0
    candidate_names = [c["column"] for c in target_json["candidates"]]
    assert "churn" in candidate_names
    assert "user_id" not in candidate_names

    # 2. Feature candidates endpoint
    feature_res = client.get(f"/api/dataset/{file_id}/feature-candidates?target=churn")
    assert feature_res.status_code == 200
    feature_json = feature_res.json()

    assert feature_json["file_id"] == file_id
    assert feature_json["target"] == "churn"
    assert feature_json["total_features"] == 4  # user_id, churn_flag, tenure, monthly_charges
    assert feature_json["recommended_count"] == 2  # tenure, monthly_charges

    features_map = {f["column"]: f["status"] for f in feature_json["features"]}
    assert features_map["churn_flag"] == "excluded_leakage"
    assert features_map["tenure"] == "recommended"
    assert features_map["monthly_charges"] == "recommended"


def test_name_pattern_columns_excluded():
    data = {
        "suspect_gender": ["Male", "Female", "Male", "Female", "Male", "Female", "Male", "Female", "Male", "Female"],
        "suspect_first_name": ["John", "Jane", "Bob", "Alice", "Charlie", "David", "Emma", "Frank", "Grace", "Henry"],
        "victim_last_name": ["Smith", "Doe", "Johnson", "Brown", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris"],
        "officer_first_name": ["Officer1", "Officer2", "Officer3", "Officer4", "Officer5", "Officer6", "Officer7", "Officer8", "Officer9", "Officer10"]
    }
    df = pd.DataFrame(data)
    result = evaluate_feature_candidates(df, target_col="suspect_gender")

    features_map = {f["column"]: f for f in result["features"]}
    assert features_map["suspect_first_name"]["status"] == "excluded_identifier_like_name"
    assert features_map["victim_last_name"]["status"] == "excluded_identifier_like_name"
    assert features_map["officer_first_name"]["status"] == "excluded_identifier_like_name"


def test_case_status_classified_as_categorical_not_identifier():
    data = {
        "suspect_gender": ["Male", "Female", "Male", "Female", "Male"],
        "case_status": ["Open", "Closed", "Pending", "Under Investigation", "Open"]
    }
    df = pd.DataFrame(data)

    from app.analytics.kpi_engine import classify_column
    assert classify_column(df["case_status"], "case_status") == "CATEGORICAL"

    result = evaluate_feature_candidates(df, target_col="suspect_gender")
    features_map = {f["column"]: f for f in result["features"]}
    assert features_map["case_status"]["status"] == "recommended"


def test_num_arrests_classified_as_measure():
    data = {
        "suspect_gender": ["Male", "Female", "Male", "Female", "Male"],
        "num_arrests": [0.0, 1.0, 3.0, 0.0, 2.0]
    }
    df = pd.DataFrame(data)

    from app.analytics.kpi_engine import classify_column
    assert classify_column(df["num_arrests"], "num_arrests") == "MEASURE"

    result = evaluate_feature_candidates(df, target_col="suspect_gender")
    features_map = {f["column"]: f for f in result["features"]}
    assert features_map["num_arrests"]["status"] == "recommended"


def test_property_loss_usd_numeric_coercion_detection():
    data = {
        "suspect_gender": ["Male", "Female", "Male", "Female", "Male"],
        "property_loss_usd": ["$1,500.00", "$250.50", " $10,000 ", "$0.00", "$4,200.75"]
    }
    df = pd.DataFrame(data)

    from app.analytics.kpi_engine import classify_column
    assert classify_column(df["property_loss_usd"], "property_loss_usd") == "MEASURE"

    result = evaluate_feature_candidates(df, target_col="suspect_gender")
    features_map = {f["column"]: f for f in result["features"]}
    assert features_map["property_loss_usd"]["status"] == "recommended"
    assert features_map["property_loss_usd"]["data_quality_note"] is not None
    assert "coerced to numeric" in features_map["property_loss_usd"]["data_quality_note"]

