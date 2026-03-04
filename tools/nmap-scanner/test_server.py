"""Tests for nmap-scanner MCP server."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_nm():
    """Create a mock nmap.PortScanner result."""
    nm = MagicMock()
    nm.all_hosts.return_value = ["10.0.1.5"]
    nm.__contains__ = lambda self, x: x == "10.0.1.5"
    nm.__getitem__ = lambda self, x: nm._host_data if x == "10.0.1.5" else {}

    host_data = MagicMock()
    host_data.__getitem__ = lambda self, x: {
        "osmatch": [{"name": "Linux 2.6.x"}],
        "tcp": {
            22: {"state": "open", "name": "ssh", "product": "OpenSSH", "version": "7.4", "extrainfo": ""},
            80: {"state": "open", "name": "http", "product": "Apache", "version": "2.4.6", "extrainfo": ""},
            443: {"state": "closed", "name": "https", "product": "", "version": "", "extrainfo": ""},
        },
    }.get(x, {})
    host_data.all_protocols.return_value = ["tcp"]
    nm._host_data = host_data
    nm.get_nmap_last_output.return_value = "<nmap raw output>"
    return nm


async def test_nmap_scan_returns_valid_facts(mock_nm):
    """nmap_scan should return structured facts JSON."""
    from server import nmap_scan

    with patch("server._run_nmap", return_value=mock_nm):
        result_str = await nmap_scan("10.0.1.5")

    data = json.loads(result_str)
    assert "facts" in data
    assert "raw_output" in data

    traits = [f["trait"] for f in data["facts"]]
    assert "service.open_port" in traits
    assert "network.host.ip" in traits
    assert "host.os" in traits


async def test_nmap_scan_parses_services(mock_nm):
    """nmap_scan should parse open ports into service.open_port facts."""
    from server import nmap_scan

    with patch("server._run_nmap", return_value=mock_nm):
        result_str = await nmap_scan("10.0.1.5")

    data = json.loads(result_str)
    port_facts = [f for f in data["facts"] if f["trait"] == "service.open_port"]
    # Only open ports (22, 80), not closed (443)
    assert len(port_facts) == 2
    assert any("22/tcp/ssh" in f["value"] for f in port_facts)
    assert any("80/tcp/http" in f["value"] for f in port_facts)


async def test_nmap_scan_os_detection(mock_nm):
    """nmap_scan should include OS guess as host.os fact."""
    from server import nmap_scan

    with patch("server._run_nmap", return_value=mock_nm):
        result_str = await nmap_scan("10.0.1.5")

    data = json.loads(result_str)
    os_facts = [f for f in data["facts"] if f["trait"] == "host.os"]
    assert len(os_facts) == 1
    assert os_facts[0]["value"] == "Linux_2.6.x"


async def test_nmap_scan_no_hosts():
    """nmap_scan should handle no-host-found gracefully."""
    from server import nmap_scan

    nm = MagicMock()
    nm.all_hosts.return_value = []
    nm.get_nmap_last_output.return_value = ""

    with patch("server._run_nmap", return_value=nm):
        result_str = await nmap_scan("192.168.1.1")

    data = json.loads(result_str)
    assert len(data["facts"]) == 1  # Only network.host.ip
    assert data["facts"][0]["trait"] == "network.host.ip"


async def test_nmap_scan_custom_ports(mock_nm):
    """nmap_scan should accept custom port list."""
    from server import nmap_scan

    with patch("server._run_nmap", return_value=mock_nm) as mock_run:
        await nmap_scan("10.0.1.5", ports="22,80")
        mock_run.assert_called_once()
