import pytest
import asyncio
import sys
import os
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.evaluator.main import evaluation_loop

# Save the original asyncio.sleep before it's patched
original_asyncio_sleep = asyncio.sleep

class StopTest(Exception):
    """Custom exception to gracefully stop the test loop."""
    pass

async def selective_sleep_mock(duration):
    """
    A mock for asyncio.sleep that only stops the evaluation_loop's own sleep.
    """
    # The evaluation_loop waits for 2.0 seconds at the end of each iteration.
    # We raise an exception here to break the loop and finish the test.
    if duration == 2.0:
        raise StopTest()

    # For any other sleep duration (like the one in our mock_run_once),
    # we call the original asyncio.sleep to allow the timeout to actually occur.
    await original_asyncio_sleep(duration)

@pytest.mark.asyncio
async def test_evaluation_loop_timeout(caplog):
    """
    Test that the evaluation_loop times out correctly and logs a warning.
    """
    # Mock run_once to simulate a long-running task
    async def mock_run_once_slow():
        # This sleep will be handled by our selective_sleep_mock, which will
        # call the original asyncio.sleep, allowing the timeout to trigger.
        await asyncio.sleep(35) # Sleep longer than the 30s timeout

    with patch('services.evaluator.main.run_once', side_effect=mock_run_once_slow), \
         patch('asyncio.sleep', side_effect=selective_sleep_mock):
        try:
            await evaluation_loop()
        except StopTest:
            # This is the expected way to exit the normally infinite loop.
            pass

    # Check that the timeout warning was logged correctly
    assert any(
        "run_once call timed out after 30 seconds." in record.message
        for record in caplog.records
    ), "The expected timeout warning was not found in the logs."