"""Tests for Metasploit shell exponential backoff and session health check."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.metasploit_client import MetasploitRPCEngine


@pytest.fixture
def engine():
    return MetasploitRPCEngine()


class TestReadShellOutput:
    """Tests for _read_shell_output()."""

    @pytest.mark.asyncio
    async def test_normal_output(self, engine):
        """Shell returns output after a few empty reads."""
        shell = MagicMock()
        call_count = 0
        def mock_read():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return ""
            return "uid=0(root) gid=0(root)\n"
        shell.read = mock_read
        result = await engine._read_shell_output(shell, timeout=5.0)
        assert "uid=0(root)" in result

    @pytest.mark.asyncio
    async def test_prompt_detection(self, engine):
        """Shell output ending with prompt triggers early stop."""
        shell = MagicMock()
        shell.read = MagicMock(side_effect=["root@target# "])
        result = await engine._read_shell_output(shell, timeout=5.0)
        assert "root@target#" in result

    @pytest.mark.asyncio
    async def test_timeout_empty(self, engine):
        """Shell always empty -> timeout returns empty string."""
        shell = MagicMock()
        shell.read = MagicMock(return_value="")
        result = await engine._read_shell_output(shell, timeout=1.0)
        assert result == ""

    @pytest.mark.asyncio
    async def test_consecutive_empty_after_output(self, engine):
        """2 consecutive empty reads after output -> done."""
        shell = MagicMock()
        shell.read = MagicMock(side_effect=["data chunk", "", ""])
        result = await engine._read_shell_output(shell, timeout=5.0)
        assert result == "data chunk"

    @pytest.mark.asyncio
    async def test_multi_chunk(self, engine):
        """Multiple data chunks are accumulated."""
        shell = MagicMock()
        shell.read = MagicMock(side_effect=["chunk1 ", "chunk2 ", "", ""])
        result = await engine._read_shell_output(shell, timeout=5.0)
        assert result == "chunk1 chunk2 "


class TestCheckSessionHealth:
    """Tests for _check_session_health()."""

    @pytest.mark.asyncio
    async def test_healthy_shell(self, engine):
        """Existing session with type=shell returns True."""
        client = MagicMock()
        client.sessions.list = {"1": {"type": "shell"}}
        result = await engine._check_session_health(client, "1")
        assert result is True

    @pytest.mark.asyncio
    async def test_healthy_meterpreter(self, engine):
        """Existing session with type=meterpreter returns True."""
        client = MagicMock()
        client.sessions.list = {"2": {"type": "meterpreter"}}
        result = await engine._check_session_health(client, "2")
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_session(self, engine):
        """Non-existent session returns False."""
        client = MagicMock()
        client.sessions.list = {}
        result = await engine._check_session_health(client, "99")
        assert result is False

    @pytest.mark.asyncio
    async def test_wrong_type(self, engine):
        """Session with unexpected type returns False."""
        client = MagicMock()
        client.sessions.list = {"3": {"type": "unknown"}}
        result = await engine._check_session_health(client, "3")
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_handling(self, engine):
        """Exception when querying sessions returns False."""
        client = MagicMock()
        type(client.sessions).list = property(lambda self: (_ for _ in ()).throw(Exception("RPC error")))
        result = await engine._check_session_health(client, "1")
        assert result is False


class TestReadShellOutputExpanded:
    """Additional tests for _read_shell_output() — SPEC-041 acceptance criteria."""

    @pytest.mark.asyncio
    async def test_read_shell_output_3_empty_then_success(self, engine):
        """3 empty reads then successful output -> correct accumulation.

        Verifies that the backoff loop keeps polling through empty reads
        and correctly accumulates when data finally arrives, then terminates
        after 2 consecutive empty reads following the output.
        """
        shell = MagicMock()
        call_count = 0

        def mock_read():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return ""
            if call_count == 4:
                return "uid=0(root) gid=0(root)"
            return ""  # consecutive empties after output -> done

        shell.read = mock_read

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await engine._read_shell_output(
                shell, start_interval=0.1, timeout=10.0
            )

        assert result == "uid=0(root) gid=0(root)"
        # At least 6 reads: 3 empty + 1 data + 2 empty (consecutive stop)
        assert call_count >= 6

    @pytest.mark.asyncio
    async def test_read_shell_output_prompt_detection_early_termination(self, engine):
        """Prompt characters ($, #, >) cause early termination.

        Tests each prompt character to ensure the loop breaks immediately
        upon detecting a shell prompt at the end of accumulated output.
        """
        for prompt_char in ('$', '#', '>'):
            shell = MagicMock()
            output_with_prompt = f"user@host{prompt_char} "
            shell.read = MagicMock(side_effect=[output_with_prompt])

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await engine._read_shell_output(
                    shell, start_interval=0.1, timeout=10.0
                )

            assert output_with_prompt.rstrip() in result.rstrip(), (
                f"Expected prompt '{prompt_char}' to trigger early termination"
            )
            # Should have called read only once (prompt detected on first data)
            assert shell.read.call_count == 1

    @pytest.mark.asyncio
    async def test_read_shell_output_persistent_empty_timeout(self, engine):
        """All empty reads -> 15s timeout (mocked asyncio.sleep to speed up).

        Verifies that when shell.read() never returns data, the method
        respects the timeout and returns an empty string.
        """
        shell = MagicMock()
        shell.read = MagicMock(return_value="")

        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("asyncio.sleep", side_effect=mock_sleep), \
             patch("time.monotonic") as mock_time:
            # Simulate time progression: starts at 0, each call advances by 1s,
            # exceeds 15s timeout after enough iterations
            time_values = [float(i) for i in range(0, 100)]
            mock_time.side_effect = time_values

            result = await engine._read_shell_output(
                shell, start_interval=0.3, timeout=15.0
            )

        assert result == ""
        # Verify exponential backoff was applied (intervals should increase)
        assert len(sleep_calls) > 0
        # First sleep should be start_interval
        assert sleep_calls[0] == pytest.approx(0.3)
