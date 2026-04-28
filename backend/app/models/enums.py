# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

from enum import Enum


class OODAPhase(str, Enum):
    OBSERVE = "observe"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"
    FAILED = "failed"
    COMPLETE = "complete"


class OperationStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


class TechniqueStatus(str, Enum):
    UNTESTED = "untested"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class MissionStepStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentStatus(str, Enum):
    ALIVE = "alive"
    DEAD = "dead"
    PENDING = "pending"
    UNTRUSTED = "untrusted"


class ExecutionEngine(str, Enum):
    SSH = "ssh"
    PERSISTENT_SSH = "persistent_ssh"
    C2 = "c2"
    MOCK = "mock"
    METASPLOIT = "metasploit"
    WINRM = "winrm"
    MCP = "mcp"


class C5ISRDomain(str, Enum):
    COMMAND = "command"
    CONTROL = "control"
    COMMS = "comms"
    COMPUTERS = "computers"
    CYBER = "cyber"
    ISR = "isr"


class C5ISRDomainStatus(str, Enum):
    OPERATIONAL = "operational"
    ACTIVE = "active"
    NOMINAL = "nominal"
    ENGAGED = "engaged"
    SCANNING = "scanning"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    CRITICAL = "critical"


class FactCategory(str, Enum):
    CREDENTIAL = "credential"
    HOST = "host"
    NETWORK = "network"
    OSINT = "osint"
    SERVICE = "service"
    VULNERABILITY = "vulnerability"
    FILE = "file"
    POC = "poc"
    WEB = "web"
    DEFENSE = "defense"


class LogSeverity(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class KillChainStage(str, Enum):
    RECON = "recon"
    WEAPONIZE = "weaponize"
    DELIVER = "deliver"
    EXPLOIT = "exploit"
    INSTALL = "install"
    C2 = "c2"
    ACTION = "action"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutomationMode(str, Enum):
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    AUTO_FULL = "auto_full"


class ToolKind(str, Enum):
    TOOL = "tool"
    ENGINE = "engine"


class AccessStatus(str, Enum):
    ACTIVE = "active"
    LOST = "lost"
    UNKNOWN = "unknown"


class ToolCategory(str, Enum):
    RECONNAISSANCE = "reconnaissance"
    ENUMERATION = "enumeration"
    VULNERABILITY_SCANNING = "vulnerability_scanning"
    CREDENTIAL_ACCESS = "credential_access"
    EXPLOITATION = "exploitation"
    EXECUTION = "execution"


class MissionProfile(str, Enum):
    SR = "SR"  # Stealth Recon
    CO = "CO"  # Covert Operation
    SP = "SP"  # Standard Pentest
    FA = "FA"  # Full Assault


class NoiseLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OPSECSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class OPSECEventType(str, Enum):
    BURST = "burst"
    AUTH_FAILURE = "auth_failure"
    HIGH_NOISE = "high_noise"
    ARTIFACT = "artifact"
    DETECTION = "detection"


class ConstraintLevel(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


# Canonical noise point values per noise_level — single source of truth
NOISE_POINTS: dict[str, int] = {"low": 1, "medium": 3, "high": 8}
