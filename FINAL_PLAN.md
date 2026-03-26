# FINAL IMPLEMENTATION PLAN
# AI-Powered Network Troubleshooting Assistant

> One document. Everything we discussed. The definitive build plan.

---

## What We're Building

A **CLI-based AI assistant** that telecom lab engineers can query in plain English to get:
- Root cause analysis (RCA) with evidence citations
- Remediation steps with device-specific CLI commands
- Historical incident correlation
- **Attack detection** — distinguish between legitimate failures and network attacks

```
Engineer: "ROUTER-LAB-01 is dropping packets and BGP is flapping. What's wrong?"

System (in <60 seconds):
  ┌─ Root Cause (Confidence: 92%) ──────────────────────────────┐
  │ Memory exhaustion triggered CPU spike → BGP hold timer      │
  │ expiry → process crash → packet loss cascade                │
  ├─ Evidence ──────────────────────────────────────────────────┤
  │ • CPU hit 92% at 08:15:00 (snmp_metrics.csv row 14)       │
  │ • BGP dropped at 08:15:03 (router_syslog.log line 9)      │
  │ • Packet drops: 4,523 pps (snmp_metrics.csv row 16)       │
  │ • bgpd crashed at 08:17:00 (router_syslog.log line 14)    │
  ├─ Security Assessment ───────────────────────────────────────┤
  │ Verdict: LEGITIMATE FAILURE (not an attack)                 │
  │ Reason: No suspicious source IPs, no scan/flood signatures │
  ├─ Fix ───────────────────────────────────────────────────────┤
  │ 1. router bgp 65001 → bgp graceful-restart                │
  │ 2. memory free low-watermark processor 20                  │
  │ 3. Monitor CPU recovery                                     │
  ├─ Historical Match ──────────────────────────────────────────┤
  │ INC-2024-0228-003 had identical symptoms.                   │
  │ Resolution: memory guards + BGP timer tuning                │
  └─────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              CLI Interface (Typer + Rich)                │
│   Commands: init | query | chat | security-scan         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│             LangGraph Supervisor Agent                   │
│                                                         │
│  1. Parse query → identify devices, symptoms, intent    │
│  2. Route to relevant agents (parallel where possible)  │
│  3. Synthesize findings into RCA                        │
│  4. Generate remediation + evidence citations           │
│  5. Store in conversation memory                        │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┘
   │          │          │          │          │
┌──▼───┐  ┌──▼───┐  ┌───▼──┐  ┌───▼────┐  ┌──▼────────┐
│ Log  │  │Metric│  │ Topo │  │Incident│  │ Security  │
│Analyst│  │Agent │  │Agent │  │ Agent  │  │  Agent    │
└──┬───┘  └──┬───┘  └───┬──┘  └───┬────┘  └──┬────────┘
   │         │          │         │           │
   │  Semantic│   SQL    │  Graph  │  Semantic │  Signature
   │  Search  │  Query   │  BFS    │  Search   │  + Anomaly
   │         │          │         │           │
┌──▼─────────▼──────────▼─────────▼───────────▼──────────┐
│                    Data Layer                            │
│                                                         │
│  ChromaDB          SQLite           NetworkX            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │ Syslog   │    │ SNMP     │    │ Topology │         │
│  │ chunks   │    │ metrics  │    │ graph    │         │
│  │          │    │ (time-   │    │ (nodes + │         │
│  │ Device   │    │  series) │    │  links)  │         │
│  │ metadata │    │          │    │          │         │
│  │          │    │ Traffic  │    │ Blast    │         │
│  │ Topology │    │ flows    │    │ radius   │         │
│  │ facts    │    │          │    │ calc     │         │
│  │          │    └──────────┘    └──────────┘         │
│  │ Incidents│                                          │
│  │          │                                          │
│  │ Security │                                          │
│  │ events   │                                          │
│  └──────────┘                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Tool | What It Does | Why This Choice |
|-------|------|-------------|-----------------|
| **Language** | Python 3.11+ | Everything | Type hints, async, ecosystem |
| **Dependency Mgmt** | Poetry | Package management | Clean, reproducible builds |
| **LLM** | Claude API (Anthropic) | RCA generation, reasoning | Best at structured reasoning + citations |
| **Orchestration** | LangGraph | Multi-agent workflow | Explicit state graph, debuggable, parallel execution |
| **Vector DB** | ChromaDB | Semantic search over logs/incidents | Local, zero-infra, embeddable |
| **Metrics Store** | SQLite | Time-series queries (CPU, memory) | Fast structured queries, no server |
| **Graph** | NetworkX | Topology mapping, blast radius | Pure Python, BFS/DFS algorithms |
| **Embeddings** | sentence-transformers | Convert text → vectors | Free, local, no API key needed |
| **CLI** | Typer + Rich | User interface | Fast to build, beautiful formatted output |
| **Data Validation** | Pydantic | Type-safe data models | Catches errors early, self-documenting |

---

## Data Sources (7 Files)

### Provided by Hackathon (5 files)

| File | Format | Size | Contains |
|------|--------|------|----------|
| `router_syslog.log` | Text | 2.3 KB | 23 log events from ROUTER-LAB-01 (08:00-08:30) |
| `device_inventory.csv` | CSV | 1.9 KB | 15 devices across 4 lab networks |
| `network_topology.json` | JSON | 2.8 KB | 7 nodes, 7 links, routing protocols, VLANs |
| `snmp_metrics.csv` | CSV | 3.0 KB | Time-series metrics (5-min intervals) for multiple devices |
| `incident_tickets.json` | JSON | 4.5 KB | 3 open incidents with timelines and history |

### Created by Us (2 files — for attack detection)

| File | Format | Size | Contains |
|------|--------|------|----------|
| `security_events.log` | Text | ~3 KB | Auth failures, port scans, flood alerts, config changes, rogue devices |
| `traffic_flows.csv` | CSV | ~2 KB | NetFlow data — source/dest IPs, ports, protocols, bytes, flags |

---

## 5 Agents — What Each One Does

### Agent 1: Log Analyst
```
Input:  "What happened to ROUTER-LAB-01 between 08:10 and 08:20?"
Source: ChromaDB (syslog chunks)
Logic:  Semantic search for relevant log events → extract timestamps,
        severity, event type → group by failure category
Output: Ranked list of events with severity, timeline, and patterns
        e.g., "CPU spike at 08:10 → BGP drop at 08:15 → crash at 08:17"
```

### Agent 2: Metrics Agent
```
Input:  "What were the CPU/memory readings during the incident?"
Source: SQLite (SNMP metrics)
Logic:  SQL query for device metrics in time range → check against
        thresholds → detect trends (rising/falling/spike)
Output: Metric values with status (OK/WARN/CRIT), peak values, trends
        e.g., "CPU peaked at 92% (CRIT) at 08:15, recovered to 48% by 08:30"
```

### Agent 3: Topology Agent
```
Input:  "If ROUTER-LAB-01 fails, what's affected?"
Source: NetworkX graph (topology)
Logic:  BFS/DFS from failed node → find all downstream devices →
        count affected links/paths → assess impact scope
Output: Blast radius diagram, affected devices, lost redundancy
        e.g., "5 downstream devices affected, 12 MPLS paths lost"
```

### Agent 4: Incident Agent
```
Input:  "Has this happened before?"
Source: ChromaDB (incident embeddings)
Logic:  Semantic search for similar symptoms → match current findings
        to past incidents → extract proven resolutions
Output: Historical matches with similarity score, past root cause, fix
        e.g., "INC-2024-0228-003 (91% match) — fixed with BGP graceful-restart"
```

### Agent 5: Security Agent (NEW)
```
Input:  "Is this an attack or a legitimate failure?"
Source: ChromaDB (security events) + SQLite (traffic flows) + all other sources
Logic:  Three-stage pipeline:
        1. Signature scan — match known attack patterns (brute force, DDoS, etc.)
        2. Anomaly detection — flag statistical outliers in metrics
        3. Correlation — cross-reference all findings, build attack chain
Output: Verdict (ATTACK / LEGITIMATE / INCONCLUSIVE), confidence score,
        attack chain timeline, containment steps
        e.g., "ATTACK DETECTED: DDoS from 10.99.0.0/16 (87% confidence)"
```

---

## 7 Attack Types Detected

| # | Attack | Detection Method | Confidence |
|---|--------|-----------------|-----------|
| 1 | Brute Force (SSH) | Failed login count > 10/min from same IP | 95% |
| 2 | Port Scanning | 20+ ports probed from single IP in 30 sec | 90% |
| 3 | DDoS / SYN Flood | Bandwidth spike + SYN rate + CPU correlation | 85% |
| 4 | BGP Hijack | Unknown AS in BGP updates | 92% |
| 5 | ARP Spoofing | MAC conflict + gratuitous ARP from unknown MAC | 88% |
| 6 | Unauthorized Config Change | Config modified from unknown user/IP | 75% |
| 7 | Rogue Device | New MAC not in inventory + DHCP violation | 90% |

---

## Project Structure

```
network_guy/
├── pyproject.toml                          # Poetry dependencies
├── README.md                               # Setup + usage guide
├── FINAL_PLAN.md                           # This file
│
├── src/network_guy/
│   ├── __init__.py
│   ├── cli.py                              # Typer CLI (init, query, chat, security-scan)
│   ├── supervisor.py                       # LangGraph orchestrator
│   ├── models.py                           # Pydantic data models
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── log_analyst.py                  # Parse logs, find error patterns
│   │   ├── metrics.py                      # Query SNMP data, detect anomalies
│   │   ├── topology.py                     # Map blast radius (NetworkX BFS)
│   │   ├── incident.py                     # Historical incident correlation
│   │   └── security/
│   │       ├── __init__.py
│   │       ├── security_agent.py           # Main security analysis agent
│   │       ├── parser.py                   # Parse security event logs
│   │       ├── signatures.py              # Attack pattern matching (7 types)
│   │       ├── anomaly.py                  # Statistical anomaly detection
│   │       └── correlator.py              # Cross-reference + attack chain builder
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py                       # Parse all 7 input file types
│   │   └── embedder.py                     # Chunk text + embed into ChromaDB
│   │
│   ├── stores/
│   │   ├── __init__.py
│   │   ├── vector.py                       # ChromaDB wrapper
│   │   ├── metrics_db.py                   # SQLite wrapper
│   │   └── graph.py                        # NetworkX topology wrapper
│   │
│   └── prompts/
│       ├── __init__.py
│       └── system.py                       # RCA + security system prompts
│
├── data/                                    # Input files
│   ├── router_syslog.log                   # Provided — router events
│   ├── device_inventory.csv                # Provided — device metadata
│   ├── network_topology.json               # Provided — network map
│   ├── snmp_metrics.csv                    # Provided — performance metrics
│   ├── incident_tickets.json               # Provided — past incidents
│   ├── security_events.log                 # NEW — security log events
│   └── traffic_flows.csv                   # NEW — NetFlow traffic data
│
└── tests/
    ├── test_loader.py                      # Data parsing tests
    ├── test_stores.py                      # Storage query tests
    ├── test_agents.py                      # Individual agent tests
    ├── test_security.py                    # Attack detection tests
    └── test_benchmark.py                   # 10 hackathon benchmark queries
```

**Total files to write: ~25 Python files**

---

## Implementation Timeline

### Phase 0: Project Setup (Day 1, ~2 hours)

| Task | What | Output |
|------|------|--------|
| 0.1 | Initialize Poetry project with all dependencies | `pyproject.toml` |
| 0.2 | Create folder structure (all directories + `__init__.py`) | Project skeleton |
| 0.3 | Define Pydantic data models | `models.py` |
| 0.4 | Create synthetic security data files | `security_events.log`, `traffic_flows.csv` |

```toml
# Key dependencies
[tool.poetry.dependencies]
python = "^3.11"
anthropic = "^0.25"
langgraph = "^0.1"
langchain-core = "^0.2"
chromadb = "^0.4"
sentence-transformers = "^3.0"
networkx = "^3.0"
typer = "^0.9"
rich = "^13.0"
pydantic = "^2.0"
```

---

### Phase 1: Data Layer (Days 1-2, ~6 hours)

**Goal**: Parse all 7 files, store in 3 databases.

| Task | What | Input → Output |
|------|------|----------------|
| 1.1 | Syslog parser | `.log` → `List[LogEvent]` |
| 1.2 | Inventory loader | `.csv` → `Dict[device_id, Device]` |
| 1.3 | Topology loader | `.json` → `NetworkX DiGraph` |
| 1.4 | Metrics loader | `.csv` → SQLite `metrics` table |
| 1.5 | Incident loader | `.json` → `List[Incident]` |
| 1.6 | Security event parser | `.log` → `List[SecurityEvent]` |
| 1.7 | Traffic flow loader | `.csv` → SQLite `flows` table |
| 1.8 | Text chunker + embedder | All text → ChromaDB collections |

**Data flow:**
```
router_syslog.log ──→ parse ──→ chunk by 5-min windows ──→ ChromaDB (syslog_chunks)
device_inventory.csv ──→ parse ──→ row to sentence ──→ ChromaDB (device_metadata)
network_topology.json ──→ parse ──→ NetworkX graph + sentences ──→ ChromaDB (topology_facts)
snmp_metrics.csv ──→ parse ──→ SQLite (metrics table)
incident_tickets.json ──→ parse ──→ ticket to document ──→ ChromaDB (incidents)
security_events.log ──→ parse ──→ chunk by event type ──→ ChromaDB (security_events)
traffic_flows.csv ──→ parse ──→ SQLite (flows table)
```

**ChromaDB collections:**
```
syslog_chunks      — log events grouped by time window
device_metadata    — device descriptions from inventory
topology_facts     — link/connection descriptions
incidents          — past incident reports + resolutions
security_events    — security log events
```

**SQLite tables:**
```sql
CREATE TABLE metrics (
    timestamp TEXT, device_id TEXT, device_name TEXT,
    metric_name TEXT, metric_value REAL, unit TEXT,
    threshold_warn REAL, threshold_crit REAL, status TEXT
);

CREATE TABLE flows (
    timestamp TEXT, src_ip TEXT, dst_ip TEXT,
    src_port INTEGER, dst_port TEXT, protocol TEXT,
    bytes INTEGER, packets INTEGER, flags TEXT, duration_sec INTEGER
);
```

---

### Phase 2: Agents (Days 2-4, ~10 hours)

**Goal**: Build 5 agent tool functions.

| Task | Agent | Hours | Key Logic |
|------|-------|-------|-----------|
| 2.1 | Log Analyst | 2h | ChromaDB semantic search → filter by time/device → rank by severity |
| 2.2 | Metrics Agent | 2h | SQLite queries → threshold checks → trend detection |
| 2.3 | Topology Agent | 1.5h | NetworkX BFS from failed node → count downstream → impact summary |
| 2.4 | Incident Agent | 1.5h | ChromaDB semantic search → similarity scoring → extract resolutions |
| 2.5 | Security Agent | 3h | Signature scan + anomaly detection + correlation → verdict |

**Each agent follows the same pattern:**
```python
def agent_function(query: str, context: AgentContext) -> AgentResult:
    """
    1. Extract parameters from query (device, time range, symptoms)
    2. Query relevant data store (ChromaDB / SQLite / NetworkX)
    3. Analyze results (pattern matching, threshold checks, graph traversal)
    4. Return structured findings with evidence citations
    """
    pass
```

---

### Phase 3: Orchestrator (Days 4-5, ~6 hours)

**Goal**: Wire agents together with LangGraph, add Claude reasoning.

| Task | What | Hours |
|------|------|-------|
| 3.1 | Define LangGraph state schema | 1h |
| 3.2 | Build supervisor node (query parser + agent router) | 2h |
| 3.3 | Build synthesizer node (combine agent results → RCA) | 1.5h |
| 3.4 | Prompt engineering (system prompt for Claude) | 1h |
| 3.5 | Add conversation memory (LangGraph MemorySaver) | 0.5h |

**LangGraph state machine:**
```
START
  │
  ▼
┌─────────────┐
│ Parse Query │ ← Extract: devices, symptoms, time range, intent
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Route to Agents  │ ← Decide which agents to call
└──┬───┬───┬───┬───┘
   │   │   │   │
   ▼   ▼   ▼   ▼     ← PARALLEL EXECUTION
  Log Metric Topo Incident
   │   │   │   │
   └───┴───┴───┘
       │
       ▼
┌──────────────────┐
│ Security Check   │ ← Always runs: is this an attack?
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Synthesize RCA   │ ← Claude combines all findings
└──────┬───────────┘   with evidence citations
       │
       ▼
┌──────────────────┐
│ Format Response  │ ← Rich tables, panels, syntax highlighting
└──────┬───────────┘
       │
       ▼
     END
```

**System prompt (core of RCA quality):**
```
You are an expert network troubleshooting assistant for a telecom test lab.

RULES:
1. ALWAYS cite evidence: log line numbers, metric timestamps, topology facts
2. Rank root causes by confidence (0.0 to 1.0)
3. Provide device-specific CLI commands for remediation
4. Note version mismatches between devices
5. Distinguish between attack-caused and legitimate failures
6. Reference historical incidents when symptoms match

FORMAT:
- Root Cause: [description] (Confidence: X%)
- Evidence: [bullet list with source:line citations]
- Security Assessment: ATTACK / LEGITIMATE / INCONCLUSIVE
- Fix Steps: [numbered, device-specific]
- Historical: [matching past incidents]
- Impact: [affected devices, blocked tests, severity]
```

---

### Phase 4: CLI + Polish (Days 5-6, ~4 hours)

**Goal**: User-facing interface and output formatting.

| Task | What | Hours |
|------|------|-------|
| 4.1 | `network-guy init` — load all data, build stores | 1h |
| 4.2 | `network-guy query "..."` — single question mode | 0.5h |
| 4.3 | `network-guy chat` — interactive multi-turn session | 1h |
| 4.4 | `network-guy security-scan` — full security audit | 0.5h |
| 4.5 | Rich output formatting (tables, panels, colors) | 1h |

**CLI commands:**
```bash
# Load data files and build databases
network-guy init --data-dir ./data

# Single query
network-guy query "Why did BGP drop on ROUTER-LAB-01?"

# Interactive chat (multi-turn, remembers context)
network-guy chat

# Security audit
network-guy security-scan

# Utility commands
network-guy devices              # List all devices + status
network-guy topology             # Print ASCII network map
network-guy incidents            # List open incidents
network-guy benchmark            # Run 10 test queries, report accuracy
```

---

### Phase 5: Testing + Deliverables (Days 6-7, ~4 hours)

**Goal**: Validate against benchmarks, prepare submission.

| Task | What | Hours |
|------|------|-------|
| 5.1 | Run 10 benchmark queries, document results | 1.5h |
| 5.2 | Run 8 security benchmark queries | 1h |
| 5.3 | Write README (setup, usage, examples) | 0.5h |
| 5.4 | Record 5-min demo video (3 scenarios) | 0.5h |
| 5.5 | Write evaluation report (accuracy, latency, limitations) | 0.5h |

---

## Benchmark Queries (18 Total)

### Core RCA Benchmarks (10 — from hackathon requirements)

| # | Query | Expected Answer | Data Sources |
|---|-------|-----------------|-------------|
| 1 | "What happened to ROUTER-LAB-01 between 08:10 and 08:20?" | CPU spike → memory pressure → BGP timeout → recovery | Logs + Metrics |
| 2 | "Why did BGP session with peer 10.0.0.3 drop?" | Hold timer expired due to CPU overload | Syslog line 9 |
| 3 | "Which devices in NET-LAB-ALPHA are WARNING or CRITICAL?" | ROUTER-LAB-01 (multiple CRITICAL metrics at 08:15) | Metrics |
| 4 | "If SW-LAB-02 is down, which devices are affected?" | LB-LAB-02, all NET-LAB-BETA dependent devices | Topology + Inventory |
| 5 | "Software version of ROUTER-LAB-01 vs ROUTER-LAB-02?" | 17.6.1 vs 17.9.3 — version mismatch, possible compatibility issue | Inventory |
| 6 | "Has CPU spike + BGP drop happened before?" | Yes — INC-2024-0228-003 (check resolution) | Incidents |
| 7 | "Remediation for Cisco BGP hold timer expiry?" | Enable graceful-restart, increase timers, reduce CPU load | Incidents + LLM |
| 8 | "Show all CRITICAL events from syslog in last hour" | 4 CRIT events: route flap, packet loss, bgpd crash, OOM | Syslog |
| 9 | "Blast radius of 5G-UPF-01 crash?" | All 5G data plane tests blocked, GTP tunnels down | Topology + Incidents |
| 10 | "Summary of all open P1 incidents" | INC-001 (CPU/BGP) + INC-003 (UPF crash) | Incidents |

### Security Benchmarks (8 — our addition)

| # | Query | Expected Answer |
|---|-------|-----------------|
| 11 | "Is someone attacking the network?" | Yes — DDoS from 10.99.0.0/16, recon from 10.99.1.15 |
| 12 | "Is the CPU spike an attack or legitimate?" | Depends on data — security agent differentiates |
| 13 | "Who is attacking us?" | Primary: 10.99.1.15 (recon), Botnet: 10.99.0.0/16 |
| 14 | "How do I stop the attack?" | Block source IPs at FIREWALL-01, enable rate-limiting |
| 15 | "Is the BGP drop attack-related?" | Yes/No based on correlation with security events |
| 16 | "Any rogue devices on the network?" | Unknown MAC on SW-LAB-01 port GE0/45 |
| 17 | "Has anyone changed config without authorization?" | Yes — unknown_user from 10.99.1.15 modified ACL |
| 18 | "Show me the full attack timeline" | Recon → scan → flood → impact → recovery |

---

## Hackathon Deliverables Checklist

| # | Deliverable | Format | Status |
|---|-------------|--------|--------|
| 1 | **Working Prototype** — CLI that ingests data and answers queries | Python CLI | To build |
| 2 | **Architecture Document** — System design with diagrams | This file (FINAL_PLAN.md) | Done |
| 3 | **Demo Video** (5 min) — 3 scenarios: log analysis, blast radius, historical correlation | MP4 | Phase 5 |
| 4 | **Source Code + README** — GitHub repo with setup instructions | GitHub | In progress |
| 5 | **Evaluation Report** — 18 benchmark queries, accuracy, latency, limitations | PDF/MD | Phase 5 |

---

## Hackathon Evaluation Alignment

| Criterion (Weight) | How We Score High |
|--------------------|--------------------|
| **Root Cause Accuracy (30%)** | 5 agents cross-reference 7 data sources. Claude synthesizes with structured prompts. Every RCA is evidence-backed, not guessed. |
| **Evidence Grounding (20%)** | Every claim cites source: log line number, metric timestamp, topology fact. Built into system prompt as hard requirement. |
| **Remediation Quality (20%)** | Device-specific CLI commands (Cisco IOS-XE). Historical incident resolutions. Step-by-step with risks/prerequisites noted. |
| **System Design (15%)** | Modular agent architecture. Adapter pattern (swap file-based for live network). Clean separation: data → agents → orchestrator → CLI. |
| **Innovation & UX (15%)** | Attack detection (unique differentiator). Attack-vs-legitimate classifier. Beautiful Rich CLI output. Multi-turn conversation memory. |

---

## What Makes This Stand Out

### vs. Basic RAG Chatbot
Most teams will build: "stuff all data into vector DB → query → LLM answers"

We build: **specialized agents with domain-specific logic** (SQL for metrics, graph BFS for topology, signature matching for security) + RAG for unstructured data. This means:
- Metrics queries are precise (SQL), not fuzzy (semantic search)
- Blast radius is deterministic (graph traversal), not hallucinated
- Attack detection is pattern-based (signatures), not guessed

### vs. Other Teams
Our **differentiator** is the Security Agent — no one else will have:
- Attack-vs-legitimate classification
- Attack chain timeline (recon → exploit → impact)
- Containment + hardening recommendations
- This directly adds to Innovation score (15% of evaluation)

---

## Summary: Build Order

```
Day 1:  Setup + Data Layer (parse all files, build stores)
Day 2:  Data Layer continued + Log Analyst + Metrics Agent
Day 3:  Topology Agent + Incident Agent
Day 4:  Security Agent (signatures + anomaly + correlation)
Day 5:  LangGraph Supervisor + Prompt Engineering
Day 6:  CLI Interface + Rich formatting
Day 7:  Testing (18 benchmarks) + Demo Video + Evaluation Report
```

**Total estimated effort: ~32 hours across 7 days**

---

## Dependencies Between Phases

```
Phase 0 (Setup)
    │
    ▼
Phase 1 (Data Layer) ← Everything depends on this
    │
    ├──→ Phase 2 (Agents) ← Can build agents in parallel once data layer works
    │       │
    │       ▼
    │    Phase 3 (Orchestrator) ← Needs agents to exist
    │       │
    │       ▼
    │    Phase 4 (CLI) ← Needs orchestrator to work
    │
    └──→ Phase 5 (Testing) ← Needs everything working
```

**Critical path**: Setup → Data → Agents → Orchestrator → CLI → Test

**Parallelizable**: Once Phase 1 is done, all 5 agents can be built independently.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LangGraph too complex | Fallback: simple function chaining (no framework needed) |
| ChromaDB embedding slow | Use `all-MiniLM-L6-v2` (smallest model, fastest) |
| Claude API rate limits | Cache responses, batch queries, use retry logic |
| Security data too synthetic | Focus on pattern detection logic, not data realism |
| Time crunch | Core RCA (Phases 0-3) is the MVP. Security (Phase 2.5) is bonus. |
| Accuracy on benchmarks | Test early, tune prompts iteratively |

**MVP (Minimum Viable Product)**: Phases 0-3 + basic CLI = working RCA tool without security agent. If time is tight, ship this.

**Full Product**: All 5 phases + security agent + 18 benchmarks = competition-winning submission.

---

## Ready to Build

This plan consolidates:
- Core RCA system (5 agents, 3 data stores, LangGraph orchestrator)
- Attack detection (7 attack types, signature + anomaly engine)
- Hackathon alignment (all 5 deliverables, all evaluation criteria)
- Realistic timeline (7 days, 32 hours)

**Next step**: Phase 0 — Initialize Poetry project and create the folder structure.

Say the word and I'll start writing code.
