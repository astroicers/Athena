# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


class ToolCategory(str, Enum):
    RECONNAISSANCE = "reconnaissance"
    ENUMERATION = "enumeration"
    VULNERABILITY_SCANNING = "vulnerability_scanning"
    CREDENTIAL_ACCESS = "credential_access"
    EXPLOITATION = "exploitation"
    EXECUTION = "execution"
