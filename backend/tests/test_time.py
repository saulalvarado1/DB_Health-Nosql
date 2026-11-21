from datetime import UTC, datetime

from app.core.time import PERU_TZ, format_peru_time, to_peru_time


def test_to_peru_time_conversion() -> None:
    # 22:44:56 UTC should be 17:44:56 PET (UTC-5)
    utc_dt = datetime(2026, 11, 20, 22, 44, 56, tzinfo=UTC)
    peru_dt = to_peru_time(utc_dt)

    assert peru_dt.year == 2026
    assert peru_dt.month == 11
    assert peru_dt.day == 20
    assert peru_dt.hour == 17
    assert peru_dt.minute == 44
    assert peru_dt.second == 56
    assert peru_dt.tzinfo == PERU_TZ


def test_format_peru_time_with_label() -> None:
    utc_dt = datetime(2026, 11, 20, 22, 44, 56, tzinfo=UTC)
    formatted = format_peru_time(utc_dt, include_tz_label=True)
    assert formatted == "2026-11-20 17:44:56 (Hora Perú, UTC-5)"


def test_format_peru_time_without_label() -> None:
    utc_dt = datetime(2026, 11, 20, 22, 44, 56, tzinfo=UTC)
    formatted = format_peru_time(utc_dt, include_tz_label=False)
    assert formatted == "2026-11-20 17:44:56"


def test_format_peru_time_naive_assumed_utc() -> None:
    naive_dt = datetime(2026, 11, 20, 22, 44, 56)
    formatted = format_peru_time(naive_dt, include_tz_label=False)
    assert formatted == "2026-11-20 17:44:56"
