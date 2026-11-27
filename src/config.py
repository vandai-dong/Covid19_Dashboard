"""Paths, data-source URLs and constants shared across the project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

US_FILE = DATA_DIR / "us.csv"
STATES_FILE = DATA_DIR / "states.csv"
REGIONS_FILE = DATA_DIR / "regions.csv"
POPULATION_FILE = DATA_DIR / "population.csv"
HOSPITAL_FILE = DATA_DIR / "hospital_state_daily.parquet"
WORLD_HOSPITAL_FILE = DATA_DIR / "current-covid-patients-hospital.csv"
HHS_RAW_FILE = RAW_DIR / "hhs_hospital_capacity_raw.csv"

# Music & COVID: derived aggregates only (never track-level Spotify rows) are committed.
MUSIC_RAW_FILE = RAW_DIR / "spotify_top200_raw.csv"
MUSIC_WEEKLY_FILE = DATA_DIR / "music_weekly.csv"
MUSIC_STATS_FILE = DATA_DIR / "music_period_stats.csv"
MUSIC_HIST_FILE = DATA_DIR / "music_feature_hist.csv"
MUSIC_URL = "https://raw.githubusercontent.com/younver/spotify-top-200-dataset/main/spotify-top-200-dataset.csv"
MUSIC_FEATURES = [
    "danceability", "energy", "speechiness", "acousticness", "instrumentalness",
    "liveness", "valence", "tempo", "duration_s",
]
MUSIC_SPLIT_DATE = "2020-03-11"  # WHO declared COVID-19 a pandemic
MUSIC_WINDOW = ("2018-12-07", "2020-12-25")  # 108 consecutive weekly charts

NYT_US_URL = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us.csv"
NYT_STATES_URL = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv"
REGIONS_URL = (
    "https://raw.githubusercontent.com/cphalpert/census-regions/master/"
    "us%20census%20bureau%20regions%20and%20divisions.csv"
)
HHS_URL = "https://healthdata.gov/api/views/g62h-syeh/rows.csv?accessType=DOWNLOAD"

AGE_BANDS = ["18-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+", "unknown"]
REGION_ORDER = ["Northeast", "Midwest", "South", "West", "Other"]

# Two-letter code -> full name for the 50 states, DC and territories.
STATE_CODES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "PR": "Puerto Rico", "GU": "Guam", "VI": "Virgin Islands",
    "MP": "Northern Mariana Islands", "AS": "American Samoa",
}
NAME_TO_CODE = {name: code for code, name in STATE_CODES.items()}
