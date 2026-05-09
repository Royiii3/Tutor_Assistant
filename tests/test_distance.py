import pytest
from unittest.mock import patch, MagicMock
from geo.distance import DistanceCalculator


def test_calculate_distance_success():
    calc = DistanceCalculator(api_key="test_key")
    mock_response = {
        "status": "1",
        "route": {
            "paths": [{
                "duration": "1500",
                "distance": "5000"
            }]
        }
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: mock_response)
        result = calc.calculate((120.1, 30.2), (120.2, 30.3))
        assert result["duration"] == 25
        assert result["distance"] == 5.0


def test_calculate_distance_invalid_coords():
    calc = DistanceCalculator(api_key="test_key")
    result = calc.calculate(None, (120.2, 30.3))
    assert result is None
