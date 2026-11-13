import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import req_check

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

@pytest.fixture
def mock_api_response(mocker):
    mock_post = mocker.patch("req_check.requests.post")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE
    mock_post.return_value = mock_response
    return mock_post

def test_check_availability_weekday(mock_api_response):
    test_date = datetime(2026, 11, 4) # Wednesday
    dummy_headers = {}
    
    # NEW: Unpack the tuple into the message and the boolean flag
    result_msg, has_availability = req_check.check_availability_for_date(test_date, dummy_headers)
    
    # NEW: Assert the boolean flag is True
    assert has_availability is True
    
    # Assertions on the message string
    assert "📅 Wednesday, 2026-11-04" in result_msg
    assert "🏟️ Court 1" in result_msg
    assert "✅ 6:00 AM" in result_msg
    assert "⭐ 6:00 PM" in result_msg
    assert "5:00 PM" not in result_msg

def test_check_availability_weekend(mock_api_response):
    test_date = datetime(2026, 11, 7) # Saturday
    dummy_headers = {}
    
    # NEW: Unpack the tuple
    result_msg, has_availability = req_check.check_availability_for_date(test_date, dummy_headers)
    
    # NEW: Assert the boolean flag is True
    assert has_availability is True
    
    # Assertions on the message string
    assert "📅 Saturday, 2026-11-07" in result_msg
    assert "✅ 6:00 PM" in result_msg
    assert "⭐" not in result_msg

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
    
    # NEW: Unpack the tuple
    result_msg, has_availability = req_check.check_availability_for_date(test_date, {})
    
    # NEW: Assert the boolean flag is False
    assert has_availability is False
    
    # Assertions on the message string
    assert "• *No courts available*" in result_msg
    assert "🏟️ Court 1" not in result_msg