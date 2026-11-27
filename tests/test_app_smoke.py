"""Smoke-test every page against the committed data files."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ENTRY = str(Path(__file__).resolve().parents[1] / "dashboard.py")

PAGES = [
    "app_pages/overview.py",
    "app_pages/trends.py",
    "app_pages/regions.py",
    "app_pages/map.py",
    "app_pages/hospitals.py",
    "app_pages/music.py",
    "app_pages/about.py",
]


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(ENTRY, default_timeout=60).run()
    assert not at.exception
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(app, page):
    at = app.switch_page(page).run()
    assert not at.exception, [e.value for e in at.exception]


def test_overview_has_four_kpis(app):
    at = app.switch_page("app_pages/overview.py").run()
    assert len(at.metric) == 4


def test_partial_date_range_does_not_crash(app):
    import datetime as dt

    at = app.switch_page("app_pages/trends.py").run()
    at.sidebar.date_input[0].set_value((dt.date(2021, 1, 1),)).run()
    assert not at.exception


def test_music_lag_slider_changes_correlation_without_error(app):
    at = app.switch_page("app_pages/music.py").run()
    assert not at.exception
    before = [m.value for m in at.metric]
    at.slider[0].set_value(4).run()
    assert not at.exception, [e.value for e in at.exception]
    assert [m.value for m in at.metric] != before
