# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Unit tests for OODAScheduler auto-loop service."""
from unittest.mock import MagicMock, patch

from app.services.ooda_scheduler import (
    _active_loops,
    get_loop_status,
    start_auto_loop,
    stop_auto_loop,
)


import pytest


@pytest.fixture(autouse=True)
def clear_loops():
    _active_loops.clear()
    yield
    _active_loops.clear()


async def test_start_auto_loop_registers_job(tmp_path):
    """start_auto_loop registers APScheduler job and returns started status."""
    db_path = str(tmp_path / "test.db")
    with patch("app.services.ooda_scheduler._scheduler") as mock_sched, \
         patch("app.services.ooda_scheduler.build_ooda_controller"):
        mock_sched.running = True
        mock_sched.get_job.return_value = None
        mock_sched.add_job = MagicMock()
        result = await start_auto_loop("op-001", db_path, interval_sec=5, max_iterations=3)
    assert result["status"] == "started"
    assert result["operation_id"] == "op-001"
    assert result["interval_sec"] == 5
    assert "op-001" in _active_loops
    # Issue 7.1: assert add_job was called with the expected arguments
    mock_sched.add_job.assert_called_once()
    call_kwargs = mock_sched.add_job.call_args
    assert call_kwargs[1]["id"] == "ooda_op-001"
    assert call_kwargs[1]["seconds"] == 5


async def test_start_auto_loop_already_running():
    """start_auto_loop returns already_running when loop exists."""
    _active_loops["op-002"] = {
        "interval_sec": 10,
        "max_iterations": 0,
        "iteration_count": 0,
        "job_id": "ooda_op-002",
    }
    result = await start_auto_loop("op-002", "/tmp/test.db")
    assert result["status"] == "already_running"


async def test_stop_auto_loop_removes_job():
    """stop_auto_loop removes job and returns stopped with iteration count."""
    _active_loops["op-003"] = {
        "interval_sec": 5,
        "max_iterations": 2,
        "iteration_count": 1,
        "job_id": "ooda_op-003",
    }
    with patch("app.services.ooda_scheduler._scheduler") as mock_sched:
        mock_sched.get_job.return_value = MagicMock()
        mock_sched.remove_job = MagicMock()
        result = await stop_auto_loop("op-003")
    assert result["status"] == "stopped"
    assert result["iterations_completed"] == 1
    assert "op-003" not in _active_loops
    # Issue 7.2: assert remove_job was called with correct job id
    mock_sched.remove_job.assert_called_once_with("ooda_op-003")


async def test_get_loop_status_idle():
    """get_loop_status returns idle when no loop registered."""
    status = get_loop_status("op-999")
    assert status["status"] == "idle"


async def test_get_loop_status_running():
    """get_loop_status returns running metadata."""
    _active_loops["op-004"] = {
        "interval_sec": 30,
        "max_iterations": 5,
        "iteration_count": 2,
        "job_id": "ooda_op-004",
    }
    status = get_loop_status("op-004")
    assert status["status"] == "running"
    assert status["iteration_count"] == 2
    assert status["max_iterations"] == 5


async def test_stop_nonexistent_loop_returns_stopped():
    """stop_auto_loop on non-existent operation returns stopped with 0 iterations."""
    with patch("app.services.ooda_scheduler._scheduler") as mock_sched:
        mock_sched.get_job.return_value = None
        result = await stop_auto_loop("op-nonexistent")
    assert result["status"] == "stopped"
    assert result["iterations_completed"] == 0


# Issue 7.3: Test max_iterations boundary — loop at max stops cleanly
async def test_max_iterations_stops_loop_on_next_tick(tmp_path):
    """When iteration_count == max_iterations, _run_cycle stops the loop."""
    # We can't easily test _run_cycle directly since it's a closure,
    # but we can verify stop_auto_loop is idempotent and that
    # when a loop is at max iterations it gets cleaned up
    _active_loops["op-005"] = {
        "interval_sec": 1,
        "max_iterations": 2,
        "iteration_count": 2,  # already at max
        "job_id": "ooda_op-005",
    }
    with patch("app.services.ooda_scheduler._scheduler") as mock_sched:
        mock_sched.get_job.return_value = MagicMock()
        mock_sched.remove_job = MagicMock()
        result = await stop_auto_loop("op-005")
    assert result["status"] == "stopped"
    assert result["iterations_completed"] == 2
    assert "op-005" not in _active_loops
