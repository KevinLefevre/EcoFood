import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from ecofood_backend.agent.clients.gemini import generate_text_async, retry_with_backoff
from ecofood_backend.agent.cache import profile_cache

# Mock env vars for testing
os.environ["GEMINI_COMPLEX_TASK_MODEL"] = "gemini-2.5-pro"
os.environ["GEMINI_FAST_TASK_MODEL"] = "gemini-2.0-flash-exp"
os.environ["GEMINI_API_KEY"] = "fake-key"

@pytest.mark.asyncio
async def test_retry_logic():
    mock_func = AsyncMock(side_effect=[ValueError("Fail 1"), ValueError("Fail 2"), "Success"])
    
    @retry_with_backoff(max_retries=3, base_delay=0.01)
    async def decorated_func():
        return await mock_func()
        
    result = await decorated_func()
    assert result == "Success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_retry_failure():
    mock_func = AsyncMock(side_effect=ValueError("Always Fail"))
    
    @retry_with_backoff(max_retries=3, base_delay=0.01)
    async def decorated_func():
        return await mock_func()
        
    with pytest.raises(ValueError, match="Always Fail"):
        await decorated_func()
    assert mock_func.call_count == 3

def test_profile_cache():
    members = [{"name": "Alice"}, {"name": "Bob"}]
    profile = {"diet": "vegan"}
    
    # Ensure clean state
    profile_cache._cache.clear()
    
    # Miss
    assert profile_cache.get(members) is None
    
    # Set
    profile_cache.set(members, profile)
    
    # Hit
    assert profile_cache.get(members) == profile
    
    # Order independence
    members_reversed = [{"name": "Bob"}, {"name": "Alice"}]
    assert profile_cache.get(members_reversed) == profile

@pytest.mark.asyncio
async def test_gemini_hybrid_model_selection():
    with patch("ecofood_backend.agent.clients.gemini.genai") as mock_genai:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Mock response"
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Test complex task
        await generate_text_async("prompt", task_type="meal_planning")
        # Check if GenerativeModel was called with correct model name
        # We need to check the calls to GenerativeModel
        calls = mock_genai.GenerativeModel.call_args_list
        # The last call should be for meal_planning
        assert calls[-1][0][0] == "gemini-2.5-pro"
        
        # Test fast task
        await generate_text_async("prompt", task_type="default")
        calls = mock_genai.GenerativeModel.call_args_list
        assert calls[-1][0][0] == "gemini-2.0-flash-exp"
