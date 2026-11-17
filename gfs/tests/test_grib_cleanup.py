from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import xarray as xr

from gfs import fetch


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [(None, None), ("decode", ValueError), ("select", KeyError)],
)
def test_grib_files_are_removed(tmp_path, monkeypatch, failure, expected_error):
    monkeypatch.setattr(fetch.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(fetch.requests, "get", lambda url: SimpleNamespace(content=b"GRIB"))
    monkeypatch.setattr(fetch, "get_col_map", lambda source: {"gust": "gust_speed_ms"})
    monkeypatch.setattr(fetch, "get_col_order", lambda: ["gust_speed_ms"])
    closed_datasets = []

    def open_datasets(path, *, backend_kwargs):
        grib_path = Path(path)
        assert grib_path.read_bytes() == b"GRIB"
        assert backend_kwargs == {"indexpath": ""}
        if failure == "decode":
            raise ValueError("invalid GRIB")

        dataset = xr.Dataset(
            {"gust": (("latitude", "longitude"), [[7.5]])},
            coords={"latitude": [48.0 if failure == "select" else 50.0], "longitude": [14.0]},
        )

        def close():
            assert grib_path.exists()
            closed_datasets.append(dataset)

        dataset.set_close(close)
        return [dataset]

    monkeypatch.setattr(fetch.cfgrib, "open_datasets", open_datasets)

    with pytest.raises(expected_error) if expected_error else nullcontext():
        data = fetch.get_gfs_data(datetime(2026, 11, 17), 0, 9, [50.0], [14.0], source="grib")
        assert data.loc[(50.0, 14.0), "gust_speed_ms"] == 7.5

    assert len(closed_datasets) == (0 if failure == "decode" else 1)
    assert list(tmp_path.iterdir()) == []
