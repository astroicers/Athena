from enum import Enum


class OODAPhase(str, Enum):
    OBSERVE = "observe"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"


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
    CALDERA = "caldera"
    SHANNON = "shannon"


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
    SERVICE = "service"
    VULNERABILITY = "vulnerability"
    FILE = "file"


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
