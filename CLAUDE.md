# CLAUDE.md - Athena Project v3

> **Project Context Document for AI Assistants**
> 
> This document provides comprehensive context about the Athena project for AI assistants (Claude, ChatGPT, etc.) to understand the project's architecture, philosophy, and technical decisions.
>
> **Status**: POC Phase - Individual deployment, military consultant focused  
> **Core Stack**: PentestGPT (Intelligence) + Caldera (Execution)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Core Philosophy](#core-philosophy)
3. [Architecture](#architecture)
4. [Component Roles](#component-roles)
5. [License Strategy](#license-strategy)
6. [Technical Stack](#technical-stack)
7. [Integration Strategy](#integration-strategy)
8. [Development Roadmap](#development-roadmap)
9. [Key Concepts](#key-concepts)
10. [POC Phase Constraints](#poc-phase-constraints)
11. [For AI Assistants](#for-ai-assistants)

---

## Project Overview

### What is Athena?

**Athena** is an AI-driven C5ISR (Command, Control, Communications, Computers, Cyber, Intelligence, Surveillance, Reconnaissance) command platform for cyber operations. It is **NOT** another penetration testing tool—it's a **military-grade command and decision platform** that orchestrates execution engines with AI-assisted tactical planning.

### Positioning
```
Traditional Tools          Athena
─────────────────         ────────────────────
"How to exploit"    →     "How to command"
Operator's console  →     Commander's dashboard
Technical execution →     Strategic decision-making
Static scripts      →     Dynamic OODA loop
Tool-centric        →     Framework-centric
```

### Key Differentiators

- **Not a tool, but a command platform**: Elevates penetration testing from tactical operations to strategic command
- **C5ISR framework**: Applies military operational framework to cyber warfare
- **MITRE ATT&CK native**: Built on MITRE Caldera with deep integration
- **AI-assisted decision**: Integrates PentestGPT for tactical intelligence (Orient phase)
- **OODA-driven**: Dynamic adjustment through Observe-Orient-Decide-Act cycles
- **Multi-engine capable**: Commands Caldera (standard) and optionally Shannon (AI-powered)

---

## Core Philosophy

### The Military Analogy
```
Athena is to penetration testing what an Air Force Command Center is to fighter jets.

PentestGPT = Military Intelligence Officer (analyzes, recommends)
Caldera    = F-16 Squadron (proven, standardized, reliable)
Shannon    = F-35 (advanced, AI-capable, adaptive) - Optional
Athena     = Command Center (decides strategy and which assets to deploy)
```

### Design Principles

1. **Commander's Perspective**: Users think in terms of strategic intent, not technical commands
2. **Framework over Tools**: C5ISR provides structure, tools provide capability
3. **Decision over Execution**: Focus on "what to do" rather than "how to do"
4. **Human-AI Collaboration**: AI assists (PentestGPT), humans decide (Commander), engines execute (Caldera/Shannon)
5. **Dynamic Adaptation**: OODA loop enables real-time tactical adjustment

### Three Layers of Intelligence
```
┌─────────────────────────────────────────────────┐
│  Strategic Intelligence (战略智能)              │
│  └─ PentestGPT: "Why this tactic?"              │
│     Role: Think, Analyze, Recommend             │
│     Output: Tactical options with reasoning     │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Decision Intelligence (决策智能)               │
│  └─ Athena Engine: "Which engine to use?"      │
│     Role: Route, Orchestrate, Prioritize       │
│     Output: Execution plan                      │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Execution Intelligence (执行智能)              │
│  ├─ Caldera: Standard MITRE techniques          │
│  └─ Shannon: AI-adaptive execution (optional)   │
│     Role: Do, Execute, Report                   │
│     Output: Attack results                      │
└─────────────────────────────────────────────────┘
```

---

## Architecture

### High-Level Architecture (POC Configuration)
```
┌─────────────────────────────────────────────────────┐
│              Pencil.dev UI Layer                    │
│  (Commander Interface - Visual Command Dashboard)   │
│                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐     │
│  │ C5ISR  │ │ MITRE  │ │ Mission│ │ Battle  │     │
│  │ Board  │ │Navigator│ │Planner │ │Monitor  │     │
│  └────────┘ └────────┘ └────────┘ └─────────┘     │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│         Athena Command & Intelligence Layer         │
│         (Core Innovation - Your IP)                 │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Strategic Decision Engine                   │  │
│  │  ├─ C5ISR Framework Mapper                   │  │
│  │  ├─ MITRE ATT&CK Orchestrator                │  │
│  │  ├─ OODA Loop Controller                     │  │
│  │  └─ Mission Priority Manager                 │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  ⭐ PentestGPT Intelligence Layer (CORE)     │  │
│  │  ════════════════════════════════════════    │  │
│  │  Role: OODA Orient Phase                     │  │
│  │  License: MIT (Safe Integration)             │  │
│  │                                               │  │
│  │  ├─ Situation Analysis                       │  │
│  │  ├─ MITRE Technique Recommendation           │  │
│  │  ├─ Tactical Reasoning                       │  │
│  │  ├─ Risk Assessment                          │  │
│  │  └─ Multi-Option Generation                  │  │
│  │                                               │  │
│  │  LLM Backend:                                 │  │
│  │  ├─ Primary: Claude (Anthropic) - Reasoning  │  │
│  │  └─ Fallback: GPT-4 (OpenAI)                 │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Execution Engine Abstraction Layer          │  │
│  │  ├─ Task Routing Logic                       │  │
│  │  ├─ Caldera Client (API-based) ✅ Core       │  │
│  │  ├─ Shannon Client (API-based) ⚠️ Optional   │  │
│  │  └─ Results Aggregation & Normalization      │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────┘
                        │
                  API Boundary
                  (License Isolation)
                        │
          ┌─────────────┴──────────────┐
          ↓                            ↓
┌──────────────────┐         ┌──────────────────┐
│ ✅ Caldera       │         │ ⚠️ Shannon       │
│  (POC Core)      │         │  (Optional)      │
│                  │         │                  │
│  Apache 2.0      │         │  AGPL-3.0        │
│  (MITRE Official)│         │  (Independent)   │
│                  │         │                  │
│  - MITRE Native  │         │  - AI Reasoning  │
│  - Standardized  │         │  - Autonomous    │
│  - Reliable      │         │  - Adaptive      │
│  - POC-Ready     │         │  - Advanced Demo │
└──────────────────┘         └──────────────────┘
```

### Data Flow (OODA Loop with PentestGPT)
```
┌─────────────────────────────────────────┐
│         Observe (观察)                   │
│  ├─ User inputs strategic intent        │
│  ├─ Caldera Agents report results       │
│  ├─ Facts database updates              │
│  └─ Environmental state changes         │
└──────────────┬──────────────────────────┘
               ↓
┌──────────────▼──────────────────────────┐
│         Orient (导向) ⭐ PentestGPT      │
│  ════════════════════════════════════   │
│  This is where PentestGPT shines:       │
│                                          │
│  1. Analyze current situation            │
│  2. Consider completed techniques        │
│  3. Evaluate failures and obstacles      │
│  4. Generate 3 tactical options          │
│  5. Explain reasoning for each           │
│  6. Recommend best path                  │
│                                          │
│  Example Output:                         │
│  ┌────────────────────────────────────┐ │
│  │ "Current: Initial access achieved  │ │
│  │                                    │ │
│  │ Option 1: T1003.001 (LSASS)       │ │
│  │   Reasoning: Admin access present │ │
│  │   Risk: Medium (EDR may detect)   │ │
│  │   Engine: Caldera (standard)      │ │
│  │                                    │ │
│  │ Option 2: T1134 (Token Manip)     │ │
│  │   Reasoning: Stealthier approach  │ │
│  │   Risk: Low                        │ │
│  │   Engine: Shannon (adaptive)      │ │
│  │                                    │ │
│  │ Recommended: Option 1"            │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               ↓
┌──────────────▼──────────────────────────┐
│         Decide (决策)                    │
│  ├─ Athena evaluates PentestGPT advice  │
│  ├─ Considers operational constraints   │
│  ├─ Selects technique                   │
│  ├─ Routes to execution engine:         │
│  │   ├─ Caldera (standard techniques)   │
│  │   └─ Shannon (complex scenarios)     │
│  └─ Updates operation plan              │
└──────────────┬──────────────────────────┘
               ↓
┌──────────────▼──────────────────────────┐
│         Act (行动)                       │
│  ├─ Caldera/Shannon executes via API    │
│  ├─ Agents perform attack operations    │
│  ├─ Results collected in Facts DB       │
│  └─ Feedback loops to Observe ──────────┘
```

---

## Component Roles

### Critical: Understanding PentestGPT vs Shannon vs Caldera
```
┌──────────────────────────────────────────────────────────┐
│  Component Comparison Matrix                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  PentestGPT (Intelligence Layer)                         │
│  ═══════════════════════════════════                     │
│  What it does:    Thinks, analyzes, recommends           │
│  What it outputs: Text recommendations & reasoning       │
│  Role in C5ISR:   Intelligence                           │
│  Role in OODA:    Orient (THE critical phase)            │
│  Executes attacks: ❌ No (pure advisory)                 │
│  License:         MIT ✅ Safe to integrate               │
│  Resources:       Minimal (LLM API calls only)           │
│  POC Status:      ✅ REQUIRED - Core differentiator      │
│                                                           │
│  Example interaction:                                    │
│  Input:  "Failed to escalate privileges via T1068"      │
│  Output: "EDR likely present. Recommend:                │
│           1. T1548.002 (UAC Bypass) - Lower noise       │
│           2. T1134 (Token Manip) - Requires SeDebug     │
│           Suggest: Try #1 first via Caldera"            │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Caldera (Standard Execution Engine)                     │
│  ════════════════════════════════════                    │
│  What it does:    Executes MITRE techniques              │
│  What it outputs: Attack results, collected facts        │
│  Role in C5ISR:   Cyber (Execution)                      │
│  Role in OODA:    Act                                    │
│  Executes attacks: ✅ Yes (predefined abilities)         │
│  License:         Apache 2.0 ✅ MITRE official           │
│  Resources:       ~2GB RAM, 2 CPU cores                  │
│  POC Status:      ✅ REQUIRED - Primary executor         │
│                                                           │
│  Example interaction:                                    │
│  Input:  Execute T1003.001 (LSASS Memory)               │
│  Output: SUCCESS - Retrieved 15 credentials              │
│          Facts: domain\admin, domain\user1...            │
│                                                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Shannon (AI-Powered Execution Engine)                   │
│  ══════════════════════════════════════                 │
│  What it does:    AI-driven adaptive execution           │
│  What it outputs: Attack results with AI reasoning       │
│  Role in C5ISR:   Cyber (Advanced Execution)             │
│  Role in OODA:    Act (with internal Orient)             │
│  Executes attacks: ✅ Yes (autonomous + adaptive)        │
│  License:         AGPL-3.0 ⚠️ API-only integration       │
│  Resources:       ~2GB RAM, 2 CPU cores                  │
│  POC Status:      ⚠️ OPTIONAL - Advanced feature         │
│                                                           │
│  Example interaction:                                    │
│  Input:  Execute privilege escalation (method TBD)      │
│  Output: SUCCESS - Used T1548.002 with obfuscation       │
│          AI Note: "Detected AV, switched to LOLBAS"      │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### When to Use Each
```
Scenario-Based Selection Guide:

┌─────────────────────────────────────────────────────────┐
│  Scenario 1: Planning Attack Strategy                  │
├─────────────────────────────────────────────────────────┤
│  Use: PentestGPT                                        │
│  Why: Need tactical analysis and recommendations       │
│                                                          │
│  User: "How do I get domain admin?"                    │
│  PentestGPT: "Analyze current position...              │
│               Recommend TA0006 → TA0004 → TA0008       │
│               Start with T1003.001 because..."         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Scenario 2: Standard MITRE Technique Execution        │
├─────────────────────────────────────────────────────────┤
│  Use: Caldera                                           │
│  Why: Known environment, standard technique             │
│                                                          │
│  Athena: Execute T1003.001 on 192.168.1.10             │
│  Caldera: [Runs standard LSASS dump ability]           │
│           Returns: 10 credentials extracted             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Scenario 3: Adaptive Execution (Unknown Defense)      │
├─────────────────────────────────────────────────────────┤
│  Use: Shannon (if available)                            │
│  Why: Need AI to adapt to unknown defenses             │
│                                                          │
│  Athena: Escalate privileges (environment unknown)     │
│  Shannon: [AI analyzes] → Detects EDR                  │
│           [Adapts] → Uses LOLBAS technique             │
│           Returns: Success via alternate method         │
└─────────────────────────────────────────────────────────┘
```

### Key Insight: PentestGPT Cannot Be Replaced
```
❌ Wrong Mental Model:
"Shannon is AI, so it can replace PentestGPT"

✅ Correct Understanding:
PentestGPT = Strategic advisor (explains WHY)
Shannon    = Smart soldier (figures out HOW)

Both use AI, but at different levels:
├─ PentestGPT: Meta-level tactical reasoning
│   "Given these facts, what's the best approach?"
│   Can be questioned: "Why recommend this?"
│   Provides multiple options for human choice
│
└─ Shannon: Execution-level adaptation
    "This defense blocked me, try another way"
    Black-box operation
    Makes own decisions autonomously

Analogy:
├─ PentestGPT = General's Chief of Staff (strategic advice)
└─ Shannon = Special Forces Unit (tactical execution)

You need both layers for Athena's value proposition!
```

---

## License Strategy

### Critical: License Isolation Architecture

**Problem**: Shannon uses AGPL-3.0 license, which has "viral" characteristics that could force Athena to also be AGPL-3.0 if improperly integrated.

**Solution**: Strict API-based integration with clear license boundaries.

### License Boundaries
```
┌─────────────────────────────────────────┐
│  Athena Core Platform                   │
│  License: Apache 2.0                    │
│                                          │
│  ✅ Commercial-friendly                 │
│  ✅ Patent protection                   │
│  ✅ Enterprise acceptable               │
│                                          │
│  Includes:                               │
│  ├─ All decision engine logic           │
│  ├─ C5ISR framework implementation      │
│  ├─ MITRE orchestration                 │
│  ├─ OODA loop controller                │
│  ├─ PentestGPT integration (MIT)        │
│  └─ UI/UX layer                         │
└──────────────┬──────────────────────────┘
               │
          API Boundary
        (License Firewall)
               │
      ┌────────┴────────┐
      ↓                 ↓
┌──────────┐      ┌──────────┐
│ Caldera  │      │ Shannon  │
│          │      │ (Optional)│
│ Apache   │      │ AGPL-3.0 │
│ 2.0      │      │          │
└──────────┘      └──────────┘
```

### Third-Party Components & Licenses
```
Component       License      Integration    Required   Source
─────────────  ──────────   ─────────────  ────────  ────────────────────
Athena Core    Apache 2.0   -              ✅ Yes    This project
PentestGPT     MIT          Library import ✅ Yes    github.com/GreyDGL/PentestGPT
Caldera        Apache 2.0   API            ✅ Yes    github.com/mitre/caldera
Shannon        AGPL-3.0     API (isolated) ⚠️ No     github.com/KeygraphHQ/shannon
```

### Safe Integration Practices

#### ✅ ALLOWED (License-Safe)
```python
# ✅ PentestGPT - MIT License (safe to import directly)
from pentestgpt import PentestGPTClient

class AthenaIntelligence:
    def __init__(self):
        # Direct import is safe - MIT license
        self.gpt_client = PentestGPTClient(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-opus-4-20250514"
        )

# ✅ Caldera - Apache 2.0 (API integration)
class CalderaClient:
    def execute_ability(self, ability_id: str):
        # HTTP API calls - license-safe
        response = requests.post(
            f"{self.caldera_url}/api/v2/abilities/{ability_id}",
            json={...}
        )

# ✅ Shannon - AGPL-3.0 (API-only, isolated)
class ShannonClient:
    def execute_task(self, task: dict):
        # HTTP API calls only - no code import
        response = requests.post(
            f"{self.shannon_url}/execute",
            json=task
        )
```

#### ❌ FORBIDDEN (License Contamination Risk)
```python
# ❌ DO NOT DO THIS - Shannon code import
from shannon import ShannonEngine  # AGPL contamination!

# ❌ DO NOT DO THIS - Copying Shannon source
# Copying Shannon modules into Athena repository

# ❌ DO NOT DO THIS - Static linking
# Including Shannon binaries in Athena
```

---

## Technical Stack

### Core Technologies
```
Frontend (UI Layer):
├─ Pencil.dev (Visual design & prototyping)
├─ React/Next.js (Framework)
└─ Tailwind CSS (Styling)

Backend (Decision Engine):
├─ Python 3.11+ (Core language)
├─ FastAPI (API framework)
├─ SQLite (POC phase - simple, file-based)
└─ Pydantic (Data validation)

AI/ML Components:
├─ ⭐ PentestGPT (MIT License) - CORE COMPONENT
│   ├─ GitHub: https://github.com/GreyDGL/PentestGPT
│   ├─ Integration: Direct library import (MIT-safe)
│   └─ Purpose: OODA Orient phase intelligence
│
├─ LLM APIs:
│   ├─ Primary: Claude (Anthropic)
│   │   └─ Model: claude-opus-4-20250514
│   │   └─ Why: Superior reasoning for tactical analysis
│   │   └─ Context: 200K tokens (entire operation)
│   │
│   └─ Fallback: GPT-4 Turbo (OpenAI)
│       └─ Model: gpt-4-turbo-preview
│       └─ Cost: ~50% cheaper than Claude
│
└─ LangChain (Optional - for advanced prompting)

Execution Engines:
├─ ✅ Caldera (MITRE official - POC Core)
│   └─ Apache 2.0 License
│   └─ Role: Primary execution engine
│
└─ ⚠️ Shannon (AI agent - Optional)
    └─ AGPL-3.0 License (API-isolated)
    └─ Role: Advanced AI-adaptive execution

Infrastructure (POC):
├─ Docker & Docker Compose (local deployment)
├─ SQLite (file-based database)
└─ Simple .env configuration
```

### LLM Integration Strategy
```python
# Flexible LLM configuration with PentestGPT

class LLMConfig:
    """
    LLM configuration for Athena's intelligence layer
    Powered by PentestGPT
    """
    
    # Primary LLM (recommended for Athena)
    PRIMARY_PROVIDER = "claude"
    CLAUDE_MODEL = "claude-opus-4-20250514"
    
    # Reasons for Claude as primary:
    # 1. Superior reasoning for complex tactical analysis
    # 2. 200K context window (can hold entire operation history)
    # 3. Better at structured thinking (MITRE mapping)
    # 4. More conservative/aligned outputs (safer for military use)
    # 5. Excellent at explaining reasoning (Orient phase key)
    
    # Fallback LLM
    FALLBACK_PROVIDER = "openai"
    OPENAI_MODEL = "gpt-4-turbo-preview"
    
    # API Keys (loaded from .env)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Generation parameters
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7  # Balance creativity and consistency

# PentestGPT Integration Example
from pentestgpt import PentestGPTClient

class AthenaOrientPhase:
    """
    Wraps PentestGPT for Athena's Orient phase
    This is the CORE intelligence component
    """
    def __init__(self):
        self.gpt = PentestGPTClient(
            api_key=LLMConfig.ANTHROPIC_API_KEY,
            model=LLMConfig.CLAUDE_MODEL
        )
    
    async def analyze_situation(
        self, 
        strategic_intent: str,
        facts: dict,
        failures: list
    ) -> TacticalRecommendation:
        """
        OODA Orient: Analyze and recommend tactics
        
        This is where Athena's AI intelligence shines
        """
        prompt = self._build_c5isr_prompt(
            strategic_intent, facts, failures
        )
        
        # Use PentestGPT's reasoning capabilities
        analysis = await self.gpt.reasoning_chain(
            query=prompt,
            context=facts
        )
        
        return self._parse_recommendations(analysis)
```

---

## Integration Strategy

### PentestGPT: The Intelligence Core

**PentestGPT** is the cornerstone of Athena's intelligence layer. It powers the OODA Orient phase, providing AI-assisted tactical reasoning.
```
Why PentestGPT is Essential:

1. Strategic Analysis
   └─ Analyzes complex operational contexts
   └─ Considers multiple factors (environment, failures, goals)
   └─ Generates multi-option recommendations

2. MITRE ATT&CK Native
   └─ Understands MITRE tactics and techniques
   └─ Maps situations to appropriate techniques
   └─ Explains technique selection reasoning

3. Human-Centric
   └─ Designed for human-AI collaboration
   └─ Provides explanations, not just answers
   └─ Presents options for human decision

4. License-Friendly
   └─ MIT License - safe to integrate directly
   └─ No viral licensing concerns
   └─ Can be modified if needed

5. Cost-Effective
   └─ Uses LLM APIs (no local compute needed)
   └─ POC testing: ~$5-15 for 20-30 operations
   └─ Pay-per-use model
```

### PentestGPT in OODA Orient Phase
```python
class AthenaOODAController:
    """
    Implements OODA loop with PentestGPT at its core
    """
    
    async def execute_ooda_cycle(self, operation: Operation):
        """
        Complete OODA cycle for one iteration
        """
        
        # ────────────────────────────────────────
        # OBSERVE: Collect current state
        # ────────────────────────────────────────
        facts = await self.facts_db.get_all(operation.id)
        agent_status = await self.caldera.get_agent_status()
        
        observation = {
            "completed_techniques": operation.completed,
            "failures": operation.failures,
            "facts": facts,
            "agent_status": agent_status
        }
        
        # ────────────────────────────────────────
        # ORIENT: ⭐ PentestGPT Analyzes
        # ────────────────────────────────────────
        # This is THE critical phase
        tactical_options = await self.pentestgpt.analyze_situation(
            strategic_intent=operation.strategic_intent,
            current_state=observation,
            environment=operation.environment_profile
        )
        
        # PentestGPT returns structured recommendations:
        # {
        #   "situation_assessment": "Current position: initial access...",
        #   "options": [
        #     {
        #       "technique_id": "T1003.001",
        #       "reasoning": "Admin access present, EDR risk medium",
        #       "prerequisites": ["SeDebugPrivilege"],
        #       "risk_level": "MEDIUM",
        #       "recommended_engine": "caldera"
        #     },
        #     ...
        #   ],
        #   "recommended": "T1003.001"
        # }
        
        # ────────────────────────────────────────
        # DECIDE: Athena evaluates and chooses
        # ────────────────────────────────────────
        decision = self.decision_engine.evaluate(
            recommendations=tactical_options,
            constraints=operation.constraints,
            commander_preferences=operation.preferences
        )
        
        # Choose execution engine
        engine = self.router.select_engine(
            technique=decision.selected_technique,
            context=operation.context,
            gpt_recommendation=decision.recommended_engine
        )
        
        # ────────────────────────────────────────
        # ACT: Execute via chosen engine
        # ────────────────────────────────────────
        if engine == "caldera":
            result = await self.caldera.execute_ability(
                technique=decision.selected_technique,
                target=operation.target
            )
        elif engine == "shannon":
            result = await self.shannon.execute_task(
                technique=decision.selected_technique,
                target=operation.target,
                adaptive=True
            )
        
        # Update facts and loop back to OBSERVE
        await self.facts_db.add(result.facts)
        operation.iterations += 1
```

### Execution Engine Selection
```python
class EngineRouter:
    """
    Routes tasks to appropriate execution engine
    
    Decision logic:
    1. PentestGPT recommendation (if confident)
    2. Technique standardization (MITRE native → Caldera)
    3. Environment complexity (unknown → Shannon)
    4. Stealth requirements (high → Shannon)
    5. Default: Caldera (proven, reliable)
    """
    
    def select_engine(
        self,
        technique: str,
        context: dict,
        gpt_recommendation: str = None
    ) -> str:
        """
        Returns: "caldera" or "shannon"
        """
        
        # Priority 1: Trust PentestGPT if high confidence
        if gpt_recommendation and self._is_high_confidence(gpt_recommendation):
            logger.info(f"Using GPT recommendation: {gpt_recommendation}")
            return gpt_recommendation
        
        # Priority 2: Standard MITRE → Caldera
        if self.caldera.has_ability(technique):
            logger.info(f"{technique} is standard MITRE → Caldera")
            return "caldera"
        
        # Priority 3: Unknown environment → Shannon (if available)
        if context.get("environment") == "unknown" and self.shannon.available():
            logger.info("Unknown environment → Shannon for adaptation")
            return "shannon"
        
        # Priority 4: High stealth → Shannon
        if context.get("stealth_level") == "maximum" and self.shannon.available():
            logger.info("High stealth required → Shannon")
            return "shannon"
        
        # Default: Caldera (most reliable)
        logger.info(f"Default routing → Caldera")
        return "caldera"
```

---

## Development Roadmap

### POC Phase - Simplified Path (6-8 weeks)

**Core Configuration: PentestGPT + Caldera**
```
Phase 1: Foundation (2 weeks)
┌────────────────────────────────────────┐
│  Week 1: Core Setup                    │
│  ├─ Project structure                  │
│  ├─ Docker Compose (3 containers)      │
│  │   ├─ athena-ui                      │
│  │   ├─ athena-backend                 │
│  │   └─ caldera                        │
│  ├─ Basic SQLite models                │
│  └─ Caldera API client                 │
│                                         │
│  Week 2: Intelligence Integration      │
│  ├─ PentestGPT library integration     │
│  ├─ Claude API configuration           │
│  ├─ Basic Orient phase implementation  │
│  └─ Simple prompting strategies        │
└────────────────────────────────────────┘

Deliverable: PentestGPT can analyze scenarios

Phase 2: OODA Loop (2 weeks)
┌────────────────────────────────────────┐
│  Week 3: Decision & Execution          │
│  ├─ Decision engine implementation     │
│  ├─ Caldera integration                │
│  ├─ Facts database                     │
│  └─ Basic routing logic                │
│                                         │
│  Week 4: OODA Integration              │
│  ├─ Complete OODA loop                 │
│  ├─ Observe → Orient → Decide → Act   │
│  ├─ Feedback mechanism                 │
│  └─ Iteration tracking                 │
└────────────────────────────────────────┘

Deliverable: One complete OODA iteration works

Phase 3: UI & Demo (2 weeks)
┌────────────────────────────────────────┐
│  Week 5: User Interface                │
│  ├─ Pencil.dev mockups                 │
│  ├─ React components                   │
│  ├─ C5ISR dashboard                    │
│  └─ MITRE ATT&CK navigator             │
│                                         │
│  Week 6: Demo Scenario                 │
│  ├─ "Obtain Domain Admin" scenario     │
│  ├─ PentestGPT recommendations visible │
│  ├─ OODA iterations displayed          │
│  └─ Presentation materials             │
└────────────────────────────────────────┘

Deliverable: Demo-ready POC

Phase 4: Optional - Shannon Integration (2 weeks)
┌────────────────────────────────────────┐
│  If time permits:                      │
│  ├─ Shannon API client                 │
│  ├─ Dual-engine routing                │
│  ├─ Comparison demo                    │
│  └─ "Standard vs AI" showcase          │
└────────────────────────────────────────┘

Deliverable: Advanced capability demo
```

### POC Success Criteria
```
✅ Must Have (POC Core):
├─ PentestGPT provides tactical recommendations
├─ Caldera executes MITRE techniques
├─ One complete OODA loop iteration
├─ C5ISR framework visible in UI
├─ Demo scenario runs smoothly
└─ Presentation-ready documentation

⚠️ Nice to Have (If time):
├─ Shannon integration
├─ Multiple OODA iterations
├─ Advanced UI features
└─ Metrics dashboard

❌ Out of Scope (POC):
├─ Production deployment
├─ Multi-user support
├─ Advanced security
├─ Compliance features
└─ Extensive testing
```

---

## POC Phase Constraints

### Resource Requirements
```
Minimal Configuration (PentestGPT + Caldera):
──────────────────────────────────────────────

Container         CPU    Memory   Required
────────────────  ─────  ───────  ────────
athena-ui         0.5    512 MB   ✅ Yes
athena-backend    1.0    1 GB     ✅ Yes
caldera           2.0    2 GB     ✅ Yes
────────────────  ─────  ───────  ────────
Total             3.5    3.5 GB

Host Requirements:
├─ CPU: 4 cores minimum
├─ RAM: 8 GB (16 GB recommended)
├─ Storage: 20 GB
└─ Network: Stable internet (for LLM APIs)

Full Configuration (+ Shannon):
──────────────────────────────────────────────

shannon (optional) 2.0   2 GB     ⚠️ No
────────────────  ─────  ───────  ────────
Total with Shannon 5.5   5.5 GB

Recommendation: Start without Shannon
```

### Cost Estimation (POC Phase)
```
One-time Setup:
└─ $0 (all open-source components)

Ongoing Costs (LLM APIs):
├─ Claude Opus: ~$15 per 1M input tokens
├─ Per OODA iteration: ~2,000-4,000 tokens
├─ Per operation: 10-20 iterations
├─ Per operation cost: ~$0.10 - $0.50
└─ POC testing (20-30 ops): $5 - $15

Total POC Budget: < $20
```

### Security Posture (POC)
```
Acceptable for POC:
✅ .env files for API keys (.gitignored)
✅ Local-only deployment
✅ Self-signed certificates OK
✅ Minimal authentication
✅ Basic logging

Not Acceptable:
❌ Committing secrets to Git
❌ Exposing to public internet
❌ Storing credentials in code
❌ Running as root

Principle: "Secure enough to not shoot yourself,
           but don't over-engineer for POC"
```

---

## Key Concepts

### For AI Assistants to Understand

#### 1. Three Layers of Intelligence
```
Every AI assistant helping with Athena must understand:

PentestGPT (Think) ≠ Shannon (Do)

PentestGPT:
├─ Role: Military intelligence analyst
├─ Function: Analyze, reason, recommend
├─ Output: "I suggest X because of Y and Z"
├─ Interacts with: Humans (commander)
├─ Can be questioned: "Why X and not Y?"
└─ POC Status: REQUIRED

Shannon:
├─ Role: Special operations soldier
├─ Function: Execute, adapt, report
├─ Output: "I did X, here's the result"
├─ Interacts with: Target systems
├─ Black box operation (less explainable)
└─ POC Status: OPTIONAL

Both use AI, but:
└─ PentestGPT = Meta-cognitive AI (thinking about tactics)
└─ Shannon = Autonomous AI (executing tactics)

You need PentestGPT to make Athena intelligent.
Shannon is just a more capable executor.
```

#### 2. PentestGPT Powers the Orient Phase
```
OODA Loop Breakdown:

Observe: Data collection
  └─ This is straightforward

Orient: ⭐ CRITICAL - PentestGPT's domain
  └─ This is where Athena adds value
  └─ "Given facts, what should we do?"
  └─ PentestGPT analyzes and recommends
  └─ Without this, Athena is just automation

Decide: Human + AI collaboration
  └─ Commander considers PentestGPT's advice
  └─ Athena engine helps structure decision

Act: Execution (Caldera/Shannon)
  └─ This is commodity capability
  └─ Anyone can execute techniques
```

#### 3. Target User Implications
```
User: 10+ years red team experience, military consultant

This means:
✅ Assume MITRE ATT&CK knowledge
✅ Use military terminology naturally
✅ Don't explain basic pentesting concepts
✅ Focus on strategic value, not execution details
❌ Don't patronize with over-simplified explanations
❌ Don't focus on "automation" - they can automate
✅ Focus on "decision support" - this is the value

When PentestGPT recommends:
└─ Don't explain what T1003.001 is
└─ DO explain why it's the best choice NOW
```

#### 4. POC Scope Management
```
When user asks for a feature:

Always ask:
1. "Is this for POC or future production?"
2. "Does this help prove the core concept?"
3. "Does this showcase Athena's unique value?"

Core value = PentestGPT + C5ISR + OODA
Not core = anything else

Example:
User: "Can we add multi-user support?"
Bad: "Sure, let's add role-based access control..."
Good: "That's a production feature. For POC, let's
      focus on proving the decision engine works.
      We can note multi-user as future enhancement."
```

---

## For AI Assistants

### Critical Understanding Checklist

Before helping with Athena development, AI assistants must understand:

- [ ] PentestGPT (Think) vs Shannon (Do) distinction
- [ ] PentestGPT is REQUIRED, Shannon is OPTIONAL for POC
- [ ] Orient phase is THE critical innovation
- [ ] Target user is senior military consultant
- [ ] C5ISR framework is organizing principle
- [ ] MITRE ATT&CK is common language
- [ ] POC scope is limited intentionally
- [ ] License boundaries (PentestGPT MIT, Shannon AGPL)

### Code Style Guidelines
```python
# ✅ Good: Clear layer separation + PentestGPT integration

class AthenaOrientPhase:
    """
    Intelligence layer - uses PentestGPT for analysis.
    This is the CORE of Athena's value.
    """
    def __init__(self):
        from pentestgpt import PentestGPTClient
        self.gpt = PentestGPTClient(...)
    
    async def analyze(self, facts: Facts) -> Recommendations:
        # PentestGPT reasoning logic
        pass

class CalderaExecutor:
    """
    Execution layer - just sends API calls.
    No decision logic here.
    """
    def execute_ability(self, ability_id: str):
        # Pure API call
        pass

# ❌ Bad: Mixed responsibilities

class AthenaEngine:
    def exploit_smb(self, target):  # NO! This is execution
        # Exploitation code doesn't belong in Athena core
```

### When Suggesting Features
```
Decision Tree:

Does it involve PentestGPT or Orient phase?
├─ Yes → Likely core to POC
└─ No  → Is it Command/Control layer?
         ├─ Yes → Likely valuable
         └─ No  → Probably defer to production

Is it execution capability?
├─ Yes → Belongs in Caldera/Shannon, not Athena
└─ No  → Continue evaluation

Does Shannon need to be involved?
├─ User explicitly mentions AI-adaptive execution → Maybe
├─ Standard MITRE technique → No, use Caldera
└─ Unknown → Ask for clarification

Is it POC scope?
├─ Proves core concept → Yes, include
├─ Production feature → No, defer
└─ Nice-to-have → Note for future
```

---

## Common Questions

### "Why do we need PentestGPT if we have Shannon?"
```
Answer: They serve different purposes at different layers.

PentestGPT = Strategic thinking
"Given the current situation, what tactics make sense?"
"Why is T1003.001 better than T1110 right now?"

Shannon = Tactical execution
"Execute this attack and adapt if defenses block you"

Analogy:
├─ PentestGPT = Military strategist (plans battles)
└─ Shannon = Special forces operator (wins firefights)

You need both. PentestGPT tells you WHAT to do.
Shannon helps DO it in complex environments.
```

### "Can Shannon replace PentestGPT?"
```
Answer: No. Different roles, different layers.

Shannon is:
├─ Black box (hard to explain its reasoning)
├─ Execution-focused (not strategic)
├─ Autonomous (doesn't collaborate with humans)

PentestGPT is:
├─ Explainable (can justify recommendations)
├─ Strategy-focused (meta-level reasoning)
├─ Collaborative (designed for human interaction)

Athena's value = Command layer with AI advice.
Shannon can't provide that - it's an executor.
```

### "Do we need Shannon for POC?"
```
Answer: No. PentestGPT + Caldera is sufficient.

POC Goal: Prove Athena's command platform concept

Required for this:
✅ AI-assisted tactical planning (PentestGPT)
✅ MITRE technique execution (Caldera)
✅ OODA loop (PentestGPT + Caldera)
✅ C5ISR framework visualization

Shannon adds:
⚠️ Dual-engine orchestration demo
⚠️ AI-adaptive execution showcase
⚠️ But increases complexity and risk

Recommendation: Start without Shannon.
Add it later if POC succeeds and you want
to showcase advanced orchestration.
```

### "Why Claude over GPT-4 for PentestGPT?"
```
Answer: Superior reasoning for tactical analysis.

Claude Advantages:
✅ Better at complex reasoning chains
✅ 200K context (entire operation history)
✅ More conservative/aligned (safer for military)
✅ Excellent at explaining reasoning (key for Orient)

GPT-4 Advantages:
✅ Cheaper (~50% less)
✅ Faster API responses
✅ PentestGPT originally designed for it

Recommendation: Use Claude as primary, GPT-4 as fallback.
Cost difference is minimal for POC (~$10-15 total).
```

---

## Environment Setup

### Required API Keys
```bash
# .env file (NEVER commit to Git)

# ════════════════════════════════════════════════
# LLM APIs (at least one required)
# ════════════════════════════════════════════════
ANTHROPIC_API_KEY=sk-ant-...    # Recommended (Claude)
OPENAI_API_KEY=sk-...           # Fallback (GPT-4)

# ════════════════════════════════════════════════
# Execution Engines
# ════════════════════════════════════════════════
CALDERA_URL=http://caldera:8888
CALDERA_API_KEY=...             # If Caldera requires auth

# Shannon (optional - comment out if not using)
# SHANNON_API_URL=http://shannon:8000

# ════════════════════════════════════════════════
# Database
# ════════════════════════════════════════════════
DATABASE_URL=sqlite:///./data/athena.db

# ════════════════════════════════════════════════
# Logging
# ════════════════════════════════════════════════
LOG_LEVEL=INFO
```

### Quick Start Commands
```bash
# ════════════════════════════════════════════════
# POC Setup (PentestGPT + Caldera)
# ════════════════════════════════════════════════

# 1. Clone repository
git clone https://github.com/[your-org]/athena
cd athena

# 2. Setup environment
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

# 3. Start core services (no Shannon)
docker-compose up -d athena-ui athena-backend caldera

# 4. Verify services
docker-compose ps
docker-compose logs -f athena-backend

# 5. Access Athena
# - Athena UI: http://localhost:3000
# - Athena API: http://localhost:8000/docs
# - Caldera: http://localhost:8888

# ════════════════════════════════════════════════
# Optional: Add Shannon later
# ════════════════════════════════════════════════

# Uncomment shannon in docker-compose.yml
# Then:
docker-compose up -d shannon
```

---

## Project Goals

### Immediate (POC - 2 months)
- [ ] Working PentestGPT + Caldera integration
- [ ] AI-powered tactical recommendations (Orient phase)
- [ ] Complete OODA loop (at least 1 iteration)
- [ ] C5ISR framework visualization
- [ ] Demo scenario: "Obtain Domain Admin"
- [ ] Presentation-ready materials

### Future (If Continuing)
- [ ] Shannon integration (dual-engine orchestration)
- [ ] Enhanced AI reasoning (multi-turn planning)
- [ ] Full MITRE ATT&CK coverage
- [ ] Production deployment considerations
- [ ] Potential commercialization path

---

## Critical Reminders for AI Assistants

1. **PentestGPT is CORE** - Not optional, not replaceable by Shannon
2. **Shannon is OPTIONAL** - POC works without it
3. **Orient phase is key** - This is where Athena adds value
4. **POC scope discipline** - Don't over-engineer
5. **License awareness** - PentestGPT MIT (safe), Shannon AGPL (careful)
6. **Target user level** - Senior military consultant, assume expertise
7. **C5ISR framework** - All features must map to it
8. **MITRE ATT&CK** - Common language for tactics

---

*Last Updated: 2024-02-22*  
*Version: 0.3.0-poc*  
*Phase: Early Development - POC (PentestGPT + Caldera)*

---

## Appendix: Quick Reference

### Component Checklist
- [ ] PentestGPT (Intelligence) ✅ Required
- [ ] Caldera (Execution) ✅ Required
- [ ] Shannon (Advanced Execution) ⚠️ Optional
- [ ] Athena UI ✅ Required
- [ ] Athena Backend ✅ Required

### OODA Checklist
- [ ] Observe: Fact collection ✅
- [ ] Orient: PentestGPT analysis ✅ **CORE**
- [ ] Decide: Athena decision engine ✅
- [ ] Act: Caldera/Shannon execution ✅

### License Compliance
- [ ] Athena Core: Apache 2.0 ✅
- [ ] PentestGPT: MIT (safe import) ✅
- [ ] Caldera: Apache 2.0 (API) ✅
- [ ] Shannon: AGPL-3.0 (API-only) ⚠️
- [ ] No license contamination ✅

### POC Success Metrics
- [ ] PentestGPT provides recommendations
- [ ] Recommendations are actionable
- [ ] Caldera executes techniques
- [ ] One complete OODA iteration
- [ ] Demo scenario works
- [ ] Presentation ready

---

**End of CLAUDE.md v3**