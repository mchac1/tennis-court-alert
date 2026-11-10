import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import req_check  # Assuming your script is named req_check.py

# A sample API response to mock
MOCK_API_RESPONSE = {
    "body": {
        "availability": {
            "time_slots": ["06:00:00", "17:00:00", "18:00:00"],
            "resources": [
                {
                    "resource_name": "Court 1",
                    "time_slot_details": [
                        {"status": 0}, # 6 AM - Available
                        {"status": 1}, # 5 PM - Unavailable
                        {"status": 0}  # 6 PM - Available
                    ]
                }
            ]
        }
    }
}

# Mocking the API call using patch
@pytest.fixture
def mock_api_response(mocker):
    # We mock requests.post inside req_check.py
    mock_post = mocker.patch("req_check.requests.post")
    
    # Configure the mock to return our fake JSON response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE
    mock_post.return_value = mock_response
    
    return mock_post

def test_check_availability_weekday(mock_api_response):
    # Test a weekday (e.g., Wednesday)
    test_date = datetime(2026, 11, 4) # November 4, 2026 is a Wednesday
    dummy_headers = {}
    
    result = req_check.check_availability_for_date(test_date, dummy_headers)
    
    # Assertions
    assert "📅 Wednesday, 2026-11-04" in result
    assert "🏟️ Court 1" in result
    assert "✅ 6:00 AM" in result     # Should have checkmark
    assert "⭐ 6:00 PM" in result     # Should have star (weekday >= 5 PM)
    assert "5:00 PM" not in result    # Should not be listed (status 1 = unavailable)

def test_check_availability_weekend(mock_api_response):
    # Test a weekend (e.g., Saturday)
    test_date = datetime(2026, 11, 7) # November 7, 2026 is a Saturday
    dummy_headers = {}
    
    result = req_check.check_availability_for_date(test_date, dummy_headers)
    
    # Assertions
    assert "📅 Saturday, 2026-11-07" in result
    assert "✅ 6:00 PM" in result     # Should have checkmark (weekend)
    assert "⭐" not in result         # No stars on weekends

def test_no_courts_available(mocker):
    # Mock an API response where ALL courts are unavailable
    empty_response = {
        "body": {
            "availability": {
                "time_slots": ["06:00:00"],
                "resources": [
                    {"resource_name": "Court 1", "time_slot_details": [{"status": 1}]}
                ]
            }
        }
    }
    
    mock_post = mocker.patch("req_check.requests.post")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = empty_response
    mock_post.return_value = mock_response
    
    test_date = datetime(2026, 11, 4)
    result = req_check.check_availability_for_date(test_date, {})
    
    # Should economize output and not list the court name
    assert "• *No courts available*" in result
    assert "🏟️ Court 1" not in result