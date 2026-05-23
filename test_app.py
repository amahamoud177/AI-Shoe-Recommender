import pytest
from unittest.mock import MagicMock
# Import the functions directly from your app script
from app import analyze_outfit_image, get_final_chat_response

@pytest.fixture
def mock_client():
    """Fixture to provide a clean, mocked Gemini client for each test."""
    return MagicMock()

def test_chain1_valid_outfit_analysis(mock_client):
    """Test Chain 1: Verify the agent correctly extracts style attributes from an image."""
    # Simulate a successful stylistic summary from Gemini 2.5 Flash
    mock_response = MagicMock()
    mock_response.text = "A casual summer outfit featuring a white t-shirt and blue denim jeans. Keywords: casual street, summer style."
    mock_client.models.generate_content.return_value = mock_response

    fake_image = MagicMock()
    result = analyze_outfit_image(mock_client, fake_image)

    assert "casual street" in result
    assert "INVALID" not in result

def test_chain1_invalid_image_filter(mock_client):
    """Test Chain 1 Safety Layer: Verify the agent catches non-clothing uploads."""
    mock_response = MagicMock()
    mock_response.text = "INVALID: No outfit detected."
    mock_client.models.generate_content.return_value = mock_response

    fake_image = MagicMock()
    result = analyze_outfit_image(mock_client, fake_image)

    assert result == "INVALID: No outfit detected."

def test_chain2_initial_recommendation_prompt(mock_client):
    """Test Chain 2 Case 1: Verify the initial greeting welcome prompt logic."""
    mock_response = MagicMock()
    mock_response.text = "Welcome! Those Classic White Sneakers are perfect for your casual street outfit."
    mock_client.models.generate_content.return_value = mock_response

    result = get_final_chat_response(
        client=mock_client,
        outfit_description="casual street look",
        matched_shoe="Classic White Sneakers",
        user_message="" # Empty because it's the initial phase
    )

    mock_client.models.generate_content.assert_called_once()
    assert "Welcome" in result

def test_chain2_followup_chat_isolation(mock_client):
    """Test Chain 2 Case 2: Verify follow-up questions switch prompt lanes and bypass greetings."""
    mock_response = MagicMock()
    mock_response.text = "For a clean low-top profile, I highly recommend checking out the Adidas Stan Smith."
    mock_client.models.generate_content.return_value = mock_response

    result = get_final_chat_response(
        client=mock_client,
        outfit_description="casual street look",
        matched_shoe="Classic White Sneakers",
        user_message="What brand do you recommend?"
    )

    assert "Adidas" in result
    # Verify it strictly isolated the response and didn't regurgitate the generic greeting
    assert "Welcome" not in result