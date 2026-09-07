from __future__ import annotations

import numpy as np
import pandas as pd

from glideator_ml.xc.benchmark import XCFeatureContract
from glideator_ml.xc.preprocessing import DATE_FEATURES, TARGET_NAMES
from glideator_ml.xc.tabpfn import (
    build_tabular_features,
    ordinal_classes_from_targets,
    tabular_feature_columns,
    threshold_probabilities_from_classes,
)


def _target_frame(classes: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            name: [int(target_index < ordinal_class) for ordinal_class in classes]
            for target_index, name in enumerate(TARGET_NAMES)
        }
    )


def test_tabpfn_ordinal_class_is_equivalent_to_nested_xc_targets() -> None:
    classes = [0, 1, 5, 11]
    frame = _target_frame(classes)

    encoded = ordinal_classes_from_targets(frame)

    np.testing.assert_array_equal(encoded, np.asarray(classes))


def test_tabpfn_ordinal_encoding_rejects_non_nested_targets() -> None:
    frame = _target_frame([3])
    frame.loc[0, "XC0"] = 0

    try:
        ordinal_classes_from_targets(frame)
    except ValueError as exc:
        assert "nested" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected non-nested XC targets to be rejected")


def test_tabpfn_class_probabilities_recover_monotonic_threshold_outputs() -> None:
    classes = np.asarray([0, 1, 11])
    class_probabilities = np.asarray([[0.2, 0.3, 0.5], [0.7, 0.2, 0.1]])

    probabilities = threshold_probabilities_from_classes(classes, class_probabilities)

    assert probabilities.shape == (2, len(TARGET_NAMES))
    np.testing.assert_allclose(probabilities[:, 0], [0.8, 0.3])
    np.testing.assert_allclose(probabilities[:, 1:], [[0.5] * 10, [0.1] * 10])
    assert np.all(probabilities[:, 1:] <= probabilities[:, :-1])


def test_tabpfn_features_flatten_existing_contract_and_keep_site_id_categorical() -> None:
    features = XCFeatureContract(
        weather_features=("weather_a", "weather_b"),
        site_features=("latitude", "longitude", "altitude"),
    )
    frame = pd.DataFrame(
        {
            "site_id": [1, 2],
            "latitude": [50.0, 49.0],
            "longitude": [14.0, 15.0],
            "altitude": [300.0, 500.0],
            "weekend": [0, 1],
            "year": [2022, 2022],
            "day_of_year_sin": [0.1, 0.2],
            "day_of_year_cos": [0.9, 0.8],
            "weather_a_9": [1.0, 2.0],
            "weather_b_9": [3.0, 4.0],
            "weather_a_12": [5.0, 6.0],
            "weather_b_12": [7.0, 8.0],
            "weather_a_15": [9.0, 10.0],
            "weather_b_15": [11.0, 12.0],
        }
    )

    columns = tabular_feature_columns(features)
    result = build_tabular_features(frame, features)

    assert columns == (
        "site_id",
        "latitude",
        "longitude",
        "altitude",
        *DATE_FEATURES,
        "weather_a_9",
        "weather_b_9",
        "weather_a_12",
        "weather_b_12",
        "weather_a_15",
        "weather_b_15",
    )
    assert tuple(result.columns) == columns
    assert isinstance(result["site_id"].dtype, pd.CategoricalDtype)
    assert result["site_id"].astype(str).tolist() == ["1", "2"]
