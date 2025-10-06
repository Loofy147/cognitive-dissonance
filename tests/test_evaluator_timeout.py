import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock

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
    if duration == 2.0:
        raise StopTest()
    await original_asyncio_sleep(duration)

@pytest.mark.asyncio
async def test_evaluation_loop_configurable_timeout(caplog):
    """
    Test that the evaluation_loop times out correctly with a configured value.
    """
    test_timeout = 0.1

    async def mock_run_once_slow():
        # Sleep just a bit longer than the test timeout
        await asyncio.sleep(test_timeout + 0.1)

    # Patch the config value, the metric counter, and the two functions
    with patch('services.evaluator.main.config.EVALUATOR_LOOP_TIMEOUT_SECONDS', test_timeout), \
         patch('services.evaluator.main.EVALUATION_LOOP_TIMEOUTS_TOTAL') as mock_timeout_counter, \
         patch('services.evaluator.main.run_once', side_effect=mock_run_once_slow), \
         patch('asyncio.sleep', side_effect=selective_sleep_mock):

        mock_inc = MagicMock()
        mock_timeout_counter.labels.return_value = MagicMock(inc=mock_inc)

        try:
            await evaluation_loop()
        except StopTest:
            pass

    # 1. Check that the dynamic timeout warning was logged correctly
    expected_log_message = f"run_once call timed out after {test_timeout} seconds."
    assert any(
        expected_log_message in record.message for record in caplog.records
    ), f"The expected timeout warning '{expected_log_message}' was not found in the logs."

    # 2. Check that the timeout metric was incremented
    mock_timeout_counter.labels.assert_called_once_with(service='evaluator')
    mock_inc.assert_called_once()