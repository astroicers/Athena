# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""SPEC-034: Standardized Tool Onboarding Pipeline — static validation tests.

Validates that every MCP tool directory under ``tools/`` conforms to the
onboarding contract:

* Required files exist (``server.py``, ``Dockerfile``, ``pyproject.toml``,
  ``tool.yaml``).
* ``tool.yaml`` has the expected structure and required fields.
* ``tool.yaml`` ``tool_id`` matches the directory name.
* ``mcp_servers.json`` contains an entry for every non-template tool.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/tests -> project root
TOOLS_DIR = PROJECT_ROOT / "tools"
MCP_SERVERS_FILE = PROJECT_ROOT / "mcp_servers.json"

# Directories to skip when enumerating production tools.
_SKIP_DIRS = {"_template", "__pycache__"}

# Required top-level keys in every tool.yaml.
TOOL_YAML_REQUIRED_KEYS = {
    "tool_id",
    "name",
    "description",
    "category",
    "risk_level",
    "mitre_techniques",
    "output_traits",
    "mcp",
    "docker",
}

# Required keys inside the ``mcp`` section of tool.yaml.
MCP_SECTION_REQUIRED_KEYS = {
    "transport",
    "command",
    "args",
    "http_url",
    "tool_prefix",
}

# Allowed values for enum-like fields.
VALID_CATEGORIES = {
    "reconnaissance",
    "credential_access",
    "execution",
    "lateral_movement",
    "collection",
}

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tool_dirs() -> list[Path]:
    """Return a sorted list of production tool directories (excludes _template)."""
    if not TOOLS_DIR.is_dir():
        return []
    return sorted(
        p
        for p in TOOLS_DIR.iterdir()
        if p.is_dir() and p.name not in _SKIP_DIRS
    )


def _tool_names() -> list[str]:
    """Return tool directory names for parametrization."""
    return [p.name for p in _tool_dirs()]


def _load_mcp_servers() -> dict:
    """Load and return the parsed ``mcp_servers.json``."""
    return json.loads(MCP_SERVERS_FILE.read_text())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tool_dirs() -> list[Path]:
    return _tool_dirs()


@pytest.fixture(scope="module")
def mcp_servers() -> dict:
    return _load_mcp_servers()


# ---------------------------------------------------------------------------
# Tests — file existence
# ---------------------------------------------------------------------------


class TestToolRequiredFiles:
    """Every production tool must ship server.py, Dockerfile, pyproject.toml."""

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_server_py_exists(self, tool_name: str) -> None:
        path = TOOLS_DIR / tool_name / "server.py"
        assert path.is_file(), f"tools/{tool_name}/server.py is missing"

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_dockerfile_exists(self, tool_name: str) -> None:
        path = TOOLS_DIR / tool_name / "Dockerfile"
        assert path.is_file(), f"tools/{tool_name}/Dockerfile is missing"

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_pyproject_toml_exists(self, tool_name: str) -> None:
        path = TOOLS_DIR / tool_name / "pyproject.toml"
        assert path.is_file(), f"tools/{tool_name}/pyproject.toml is missing"

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_exists(self, tool_name: str) -> None:
        path = TOOLS_DIR / tool_name / "tool.yaml"
        assert path.is_file(), f"tools/{tool_name}/tool.yaml is missing"


# ---------------------------------------------------------------------------
# Tests — tool.yaml structure
# ---------------------------------------------------------------------------


class TestToolYamlStructure:
    """Validate the schema / structure of each tool.yaml."""

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_is_valid_yaml(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        assert isinstance(data, dict), "tool.yaml must be a YAML mapping"

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_has_required_keys(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        missing = TOOL_YAML_REQUIRED_KEYS - set(data.keys())
        assert not missing, (
            f"tools/{tool_name}/tool.yaml is missing keys: {sorted(missing)}"
        )

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_mcp_section_has_required_keys(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        mcp_section = data.get("mcp")
        if mcp_section is None:
            pytest.skip("mcp section missing (caught by other test)")
        missing = MCP_SECTION_REQUIRED_KEYS - set(mcp_section.keys())
        assert not missing, (
            f"tools/{tool_name}/tool.yaml mcp section missing keys: {sorted(missing)}"
        )

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_category_is_valid(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        category = data.get("category")
        if category is None:
            pytest.skip("category missing (caught by other test)")
        assert category in VALID_CATEGORIES, (
            f"tools/{tool_name}/tool.yaml category '{category}' "
            f"not in {sorted(VALID_CATEGORIES)}"
        )

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_risk_level_is_valid(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        risk_level = data.get("risk_level")
        if risk_level is None:
            pytest.skip("risk_level missing (caught by other test)")
        assert risk_level in VALID_RISK_LEVELS, (
            f"tools/{tool_name}/tool.yaml risk_level '{risk_level}' "
            f"not in {sorted(VALID_RISK_LEVELS)}"
        )

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_mitre_techniques_is_list(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        mitre = data.get("mitre_techniques")
        if mitre is None:
            pytest.skip("mitre_techniques missing (caught by other test)")
        assert isinstance(mitre, list), (
            f"tools/{tool_name}/tool.yaml mitre_techniques must be a list"
        )

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_yaml_output_traits_is_list(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        traits = data.get("output_traits")
        if traits is None:
            pytest.skip("output_traits missing (caught by other test)")
        assert isinstance(traits, list), (
            f"tools/{tool_name}/tool.yaml output_traits must be a list"
        )


# ---------------------------------------------------------------------------
# Tests — tool_id matches directory name
# ---------------------------------------------------------------------------


class TestToolYamlNameConsistency:
    """tool_id in tool.yaml must match the directory name."""

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_tool_id_matches_directory(self, tool_name: str) -> None:
        yaml_path = TOOLS_DIR / tool_name / "tool.yaml"
        if not yaml_path.is_file():
            pytest.skip(f"tools/{tool_name}/tool.yaml does not exist")
        data = yaml.safe_load(yaml_path.read_text())
        tool_id = data.get("tool_id")
        assert tool_id == tool_name, (
            f"tools/{tool_name}/tool.yaml tool_id is '{tool_id}', "
            f"expected '{tool_name}'"
        )


# ---------------------------------------------------------------------------
# Tests — mcp_servers.json consistency
# ---------------------------------------------------------------------------


class TestMcpServersJson:
    """mcp_servers.json must be valid JSON and reference all tools."""

    def test_mcp_servers_json_exists(self) -> None:
        assert MCP_SERVERS_FILE.is_file(), "mcp_servers.json not found at project root"

    def test_mcp_servers_json_is_valid_json(self) -> None:
        data = json.loads(MCP_SERVERS_FILE.read_text())
        assert isinstance(data, dict), "mcp_servers.json must be a JSON object"
        assert "servers" in data, "mcp_servers.json must have a 'servers' key"

    def test_mcp_servers_contains_all_tools(self) -> None:
        """Every tool directory (except _template) should have an entry."""
        data = json.loads(MCP_SERVERS_FILE.read_text())
        server_names = set(data.get("servers", {}).keys())
        tool_names = set(_tool_names())

        missing = tool_names - server_names
        assert not missing, (
            f"mcp_servers.json is missing entries for tools: {sorted(missing)}"
        )

    def test_mcp_servers_entries_have_required_fields(self) -> None:
        """Each server entry must have transport, command, args, and http_url."""
        required = {"transport", "command", "args", "http_url", "enabled"}
        data = json.loads(MCP_SERVERS_FILE.read_text())
        for name, entry in data.get("servers", {}).items():
            missing = required - set(entry.keys())
            assert not missing, (
                f"mcp_servers.json entry '{name}' is missing fields: {sorted(missing)}"
            )

    @pytest.mark.parametrize("tool_name", _tool_names())
    def test_mcp_server_description_not_empty(self, tool_name: str) -> None:
        """Each server entry should have a non-empty description."""
        data = json.loads(MCP_SERVERS_FILE.read_text())
        entry = data.get("servers", {}).get(tool_name)
        if entry is None:
            pytest.skip(f"'{tool_name}' not in mcp_servers.json")
        desc = entry.get("description", "")
        assert desc and desc.strip(), (
            f"mcp_servers.json entry '{tool_name}' has empty description"
        )


# ---------------------------------------------------------------------------
# Tests — template directory
# ---------------------------------------------------------------------------


class TestTemplateDirectory:
    """The _template directory must exist with expected scaffold files."""

    def test_template_dir_exists(self) -> None:
        assert (TOOLS_DIR / "_template").is_dir(), "tools/_template/ is missing"

    def test_template_server_py_exists(self) -> None:
        assert (TOOLS_DIR / "_template" / "server.py").is_file()

    def test_template_dockerfile_exists(self) -> None:
        assert (TOOLS_DIR / "_template" / "Dockerfile").is_file()

    def test_template_pyproject_toml_exists(self) -> None:
        assert (TOOLS_DIR / "_template" / "pyproject.toml").is_file()

    def test_template_tool_yaml_exists(self) -> None:
        assert (TOOLS_DIR / "_template" / "tool.yaml").is_file()

    def test_template_tool_yaml_has_placeholder(self) -> None:
        """Template tool.yaml must contain the {{TOOL_NAME}} placeholder."""
        content = (TOOLS_DIR / "_template" / "tool.yaml").read_text()
        assert "{{TOOL_NAME}}" in content, (
            "tools/_template/tool.yaml must contain {{TOOL_NAME}} placeholder"
        )
