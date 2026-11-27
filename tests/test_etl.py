import pandas as pd
import pytest

from src import etl


def test_build_us_daily_from_cumulative():
    raw = pd.DataFrame({"date": ["2020-01-02", "2020-01-01", "2020-01-03"], "cases": [3, 1, 6], "deaths": [0, 0, 1]})
    us = etl.build_us(raw)
    assert us["date"].is_monotonic_increasing
    assert us["daily_cases"].tolist() == [1, 2, 3]
    assert us["daily_deaths"].tolist() == [0, 0, 1]


def test_build_regions_unifies_code_column_and_adds_territories():
    raw = pd.DataFrame(
        {"State": ["Alaska"], "State Code": ["AK"], "Region": ["West"], "Division": ["Pacific"]}
    )
    out = etl.build_regions(raw)
    assert list(out.columns) == ["State", "State Code", "Region", "Division"]
    assert out.set_index("State").loc["Puerto Rico", "State Code"] == "PR"
    assert "American Samoa" in out["State"].tolist()


def test_build_states_diffs_per_state_and_fills_region():
    raw = pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02", "2020-01-01", "2020-01-02"],
            "state": ["A", "A", "Mars", "Mars"],
            "fips": [1, 1, 99, 99],
            "cases": [10, 15, 100, 100],
            "deaths": [0, 1, 5, 5],
        }
    )
    regions = pd.DataFrame({"State": ["A"], "Region": ["West"]})
    out = etl.build_states(raw, regions).set_index(["State", "Date"])
    assert out.loc[("A", pd.Timestamp("2020-01-02")), "daily_cases"] == 5
    assert out.loc[("A", pd.Timestamp("2020-01-01")), "daily_cases"] == 10  # first day = total
    assert out.loc[("Mars", pd.Timestamp("2020-01-02")), "daily_cases"] == 0
    assert out["Region"].notna().all()
    assert out.loc[("Mars", pd.Timestamp("2020-01-01")), "Region"] == "Other"


def test_mask_spikes_removes_isolated_outlier_only():
    values = [10] * 10 + [13_738] + [10] * 10
    out = etl.mask_spikes(pd.DataFrame({"state": "TX", "x": values}), ["x"])
    assert pd.isna(out.loc[10, "x"])
    assert out["x"].isna().sum() == 1
    # A sustained high level is real data, not a spike.
    high = etl.mask_spikes(pd.DataFrame({"state": "TX", "x": [1000] * 21}), ["x"])
    assert high["x"].notna().all()


def test_build_hospital_shifts_admission_date_and_validates_columns():
    cols = {c: 1 for c in etl.HOSPITAL_COLUMNS}
    raw = pd.DataFrame({"state": ["NY"], "date": ["2021-03-02"], **cols})
    out = etl.build_hospital(raw)
    assert out.loc[0, "admission_date"] == pd.Timestamp("2021-03-01")
    assert "admission_18-19" in out.columns
    with pytest.raises(ValueError, match="missing expected columns"):
        etl.build_hospital(raw.drop(columns=["inpatient_beds"]))
