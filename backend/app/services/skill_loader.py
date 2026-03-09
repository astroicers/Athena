"""Security Skills Library — load and inject attack knowledge into Orient prompt."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SKILLS_DIR = Path(__file__).parent.parent / "data" / "skills"
_MAX_SKILLS_PER_CALL = 2
_MAX_CHARS_PER_SKILL = 3200  # ~800 tokens

# technique_id -> skill file names
_SKILL_TECHNIQUE_MAP: dict[str, list[str]] = {
    "T1190": ["sql_injection", "xss"],
    "T1059.007": ["sql_injection", "xss"],
    "T1003": ["credential_dumping"],
    "T1003.001": ["credential_dumping"],
    "T1003.002": ["credential_dumping"],
    "T1003.003": ["credential_dumping"],
    "T1068": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "T1548": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "T1548.001": ["privilege_escalation_linux"],
    "T1548.002": ["privilege_escalation_windows"],
    "T1021": ["lateral_movement"],
    "T1021.001": ["lateral_movement"],
    "T1021.004": ["lateral_movement"],
    "T1595": ["network_recon", "web_scanning"],
    "T1046": ["network_recon"],
}

_TACTIC_SKILL_FALLBACK: dict[str, list[str]] = {
    "TA0001": ["sql_injection", "xss"],
    "TA0004": ["privilege_escalation_linux", "privilege_escalation_windows"],
    "TA0006": ["credential_dumping"],
    "TA0008": ["lateral_movement"],
    "TA0043": ["network_recon", "web_scanning"],
}


def load_skills(technique_id: str, tactic_id: str | None = None) -> str:
    """Load skill content relevant to a technique/tactic.

    Returns formatted Markdown string suitable for injection into Orient prompt.
    Returns at most _MAX_SKILLS_PER_CALL skills.
    """
    skill_names = _resolve_skill_names(technique_id, tactic_id)
    if not skill_names:
        return ""

    sections: list[str] = []
    for name in skill_names[:_MAX_SKILLS_PER_CALL]:
        content = _read_skill_file(name)
        if content:
            sections.append(content)

    if not sections:
        return ""

    return "## 8.5. RELEVANT SECURITY KNOWLEDGE\n\n" + "\n---\n".join(sections)


def _resolve_skill_names(technique_id: str, tactic_id: str | None) -> list[str]:
    """Resolve technique/tactic to skill file names with fallback logic."""
    # 1. Exact match
    if technique_id in _SKILL_TECHNIQUE_MAP:
        return _SKILL_TECHNIQUE_MAP[technique_id]

    # 2. Parent match (T1003.001 -> T1003)
    parent = technique_id.split(".")[0] if "." in technique_id else None
    if parent and parent in _SKILL_TECHNIQUE_MAP:
        return _SKILL_TECHNIQUE_MAP[parent]

    # 3. Tactic fallback
    if tactic_id and tactic_id in _TACTIC_SKILL_FALLBACK:
        return _TACTIC_SKILL_FALLBACK[tactic_id]

    return []


def _read_skill_file(name: str) -> str | None:
    """Read a skill Markdown file, stripping YAML front matter."""
    path = _SKILLS_DIR / f"{name}.md"
    if not path.exists():
        logger.debug("Skill file not found: %s", path)
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        # Strip YAML front matter
        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                raw = raw[end + 3:].strip()
        return raw[:_MAX_CHARS_PER_SKILL]
    except Exception:
        logger.warning("Failed to read skill file: %s", path, exc_info=True)
        return None
