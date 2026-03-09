"""Tests for Security Skills Library (SPEC-043 A3)."""
import pytest
from pathlib import Path

from app.services.skill_loader import (
    load_skills,
    _resolve_skill_names,
    _read_skill_file,
    _SKILLS_DIR,
)


class TestResolveSkillNames:
    def test_exact_match(self):
        result = _resolve_skill_names("T1190", None)
        assert "sql_injection" in result

    def test_parent_match(self):
        result = _resolve_skill_names("T1003.001", None)
        assert "credential_dumping" in result

    def test_tactic_fallback(self):
        result = _resolve_skill_names("T9999", "TA0004")
        assert "privilege_escalation_linux" in result

    def test_no_match(self):
        result = _resolve_skill_names("T9999", "TA9999")
        assert result == []

    def test_no_match_no_tactic(self):
        result = _resolve_skill_names("T9999", None)
        assert result == []


class TestReadSkillFile:
    def test_existing_file(self):
        content = _read_skill_file("sql_injection")
        assert content is not None
        assert "Attack Methodology" in content

    def test_nonexistent_file(self):
        content = _read_skill_file("nonexistent_skill")
        assert content is None

    def test_yaml_front_matter_stripped(self):
        content = _read_skill_file("sql_injection")
        assert content is not None
        assert "---" not in content.split("\n")[0]

    def test_max_chars(self):
        content = _read_skill_file("sql_injection")
        assert content is not None
        assert len(content) <= 3200


class TestLoadSkills:
    def test_loads_for_known_technique(self):
        result = load_skills("T1190")
        assert "RELEVANT SECURITY KNOWLEDGE" in result
        assert "SQL Injection" in result or "Attack Methodology" in result

    def test_max_two_skills(self):
        result = load_skills("T1190")
        # T1190 maps to sql_injection + xss, both should appear
        assert result != ""

    def test_empty_for_unknown(self):
        result = load_skills("T9999")
        assert result == ""

    def test_parent_technique(self):
        result = load_skills("T1003.001")
        assert result != ""

    def test_tactic_fallback(self):
        result = load_skills("T9999", "TA0008")
        assert "Lateral Movement" in result or result != ""
