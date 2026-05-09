import pytest
from unittest.mock import patch, MagicMock
from geo.geocoder import Geocoder


def test_geocode_success():
    geocoder = Geocoder(api_key="test_key")
    mock_response = {
        "status": "1",
        "geocodes": [{"location": "120.123,30.456"}]
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: mock_response)
        coords = geocoder.geocode("西湖区")
        assert coords == (120.123, 30.456)


def test_geocode_not_found():
    geocoder = Geocoder(api_key="test_key")
    mock_response = {"status": "0", "info": "NOT_FOUND"}
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: mock_response)
        coords = geocoder.geocode("不存在的地址")
        assert coords is None
