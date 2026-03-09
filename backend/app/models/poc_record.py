"""PoC Record dataclass for auto-generated attack reproduction steps."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json


@dataclass
class PoCRecord:
    """結構化 PoC 記錄，用於自動產出可重現的攻擊步驟。"""

    technique_id: str
    target_ip: str
    commands_executed: list[str]
    input_params: dict
    output_snippet: str
    environment: dict
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reproducible: bool = True

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "PoCRecord":
        return cls(**json.loads(raw))
