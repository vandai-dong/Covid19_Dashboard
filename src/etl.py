"""Offline data pipeline. Run it manually (or on a schedule) to refresh ``data/``:

    python -m src.etl                 # NYT + census regions (network)
    python -m src.etl --hhs           # also rebuild the hospital file from the HHS raw CSV

The Streamlit app never calls this module; it only reads the files this writes.
"""
from __future__ import annotations

import argparse
import logging
import os
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd

from src import config

log = logging.getLogger("etl")

TERRITORIES = pd.DataFrame(
    {
        "State": ["Puerto Rico", "Virgin Islands", "Guam", "Northern Mariana Islands", "American Samoa"],
        "State Code": ["PR", "VI", "GU", "MP", "AS"],
        "Region": ["Other"] * 5,
        "Division": ["Other"] * 5,
    }
)

HOSPITAL_COLUMNS = {
    **{f"previous_day_admission_adult_covid_confirmed_{b}": f"admission_{b}" for b in config.AGE_BANDS},
    "previous_day_admission_pediatric_covid_confirmed": "admission_pediatric",
    "critical_staffing_shortage_today_yes": "staff_shortage_hospitals",
    "inpatient_beds": "inpatient_beds",
    "inpatient_beds_used_covid": "inpatient_beds_covid",
    "total_staffed_adult_icu_beds": "icu_beds",
    "staffed_icu_adult_patients_confirmed_covid": "icu_covid_patients",
}


# ---------------------------------------------------------------- transforms
def build_regions(regions: pd.DataFrame) -> pd.DataFrame:
    """Census regions plus territories, with one consistent ``State Code`` column."""
    regions = regions.rename(columns={"State.Code": "State Code"})
    regions = regions[["State", "State Code", "Region", "Division"]]
    return pd.concat([regions, TERRITORIES], ignore_index=True).drop_duplicates("State")


def build_us(us: pd.DataFrame) -> pd.DataFrame:
    us = us.copy()
    us["date"] = pd.to_datetime(us["date"])
    us = us.sort_values("date").reset_index(drop=True)
    us["daily_cases"] = us["cases"].diff().fillna(us["cases"]).astype("int64")
    us["daily_deaths"] = us["deaths"].diff().fillna(us["deaths"]).astype("int64")
    return us


def build_states(states: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    states = states.copy()
    states["date"] = pd.to_datetime(states["date"])
    states = states.sort_values(["state", "date"]).reset_index(drop=True)
    for src, dst in (("cases", "daily_cases"), ("deaths", "daily_deaths")):
        states[dst] = states.groupby("state")[src].diff().fillna(states[src]).astype("int64")
    states = states.merge(regions[["State", "Region"]], left_on="state", right_on="State", how="left")
    states["Region"] = states["Region"].fillna("Other")
    states = states.drop(columns=["State"]).rename(
        columns={"state": "State", "date": "Date", "cases": "Total_Cases", "deaths": "Total_Deaths"}
    )
    return states.sort_values(["Date", "State"]).reset_index(drop=True)


def build_hospital(raw: pd.DataFrame) -> pd.DataFrame:
    """Slim the 135-column HHS timeseries to the columns the dashboard uses.

    ``previous_day_admission_*`` columns describe the day before the report date, so the
    date is shifted back one day to the actual admission date.
    """
    missing = [c for c in HOSPITAL_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"HHS file is missing expected columns: {missing}")
    df = raw[["state", "date", *HOSPITAL_COLUMNS]].rename(columns=HOSPITAL_COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    df["admission_date"] = df["date"] - pd.Timedelta(days=1)
    df = df.sort_values(["date", "state"]).reset_index(drop=True)
    return mask_spikes(df, [c for c in df.columns if c.startswith("admission_") and c != "admission_date"])


def mask_spikes(df: pd.DataFrame, columns: list[str], factor: float = 20, floor: float = 500) -> pd.DataFrame:
    """Blank out obvious reporting errors (e.g. TX reported 13,738 admissions for ages 18-19 on 2020-08-15).

    A value is a spike if it exceeds ``floor`` and ``factor`` times the state's centred 15-day median.
    """
    df = df.copy()
    for col in columns:
        median = df.groupby("state")[col].transform(lambda s: s.rolling(15, center=True, min_periods=3).median())
        df.loc[(df[col] > floor) & (df[col] > factor * median.clip(lower=1)), col] = float("nan")
    return df


# ----------------------------------------------------------------------- IO
def _atomic_write(path: Path, writer) -> None:
    """Write via a temp file then rename so readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=path.suffix)
    os.close(fd)
    try:
        writer(tmp)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _download(url: str, dest: Path) -> None:
    log.info("Downloading %s", url)
    _atomic_write(dest, lambda tmp: urllib.request.urlretrieve(url, tmp))


def run_core() -> None:
    us_raw = pd.read_csv(config.NYT_US_URL)
    states_raw = pd.read_csv(config.NYT_STATES_URL)
    regions_raw = pd.read_csv(config.REGIONS_URL)

    regions = build_regions(regions_raw)
    states = build_states(states_raw, regions)
    us = build_us(us_raw)

    _atomic_write(config.REGIONS_FILE, lambda p: regions.to_csv(p, index=False))
    _atomic_write(config.STATES_FILE, lambda p: states.to_csv(p, index=False))
    _atomic_write(config.US_FILE, lambda p: us.to_csv(p, index=False))
    log.info("Wrote US (%d rows), states (%d rows), regions (%d rows)", len(us), len(states), len(regions))


def run_hospital(download: bool = False) -> None:
    if download or not config.HHS_RAW_FILE.exists():
        _download(config.HHS_URL, config.HHS_RAW_FILE)
    usecols = ["state", "date", *HOSPITAL_COLUMNS]
    raw = pd.read_csv(config.HHS_RAW_FILE, usecols=lambda c: c in usecols)
    hospital = build_hospital(raw)
    _atomic_write(config.HOSPITAL_FILE, lambda p: hospital.to_parquet(p, index=False))
    log.info("Wrote hospital file (%d rows)", len(hospital))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hhs", action="store_true", help="rebuild the hospital parquet from the HHS raw CSV")
    parser.add_argument("--download-hhs", action="store_true", help="re-download the HHS raw CSV first")
    parser.add_argument("--skip-core", action="store_true", help="skip the NYT/regions refresh")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not args.skip_core:
        run_core()
    if args.hhs or args.download_hhs:
        run_hospital(download=args.download_hhs)


if __name__ == "__main__":
    main()
