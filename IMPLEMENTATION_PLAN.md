# Implementation Plan: AI-Powered Network Troubleshooting Assistant

## Executive Summary

**Goal**: Build a hackathon-ready AI agent that ingests network data (syslogs, metrics, topology, incidents) and provides evidence-backed root cause analysis (RCA) + remediation steps in <60 seconds.

**Timeline**: 2 weeks (hackathon sprint)
**Team Size**: 1-3 engineers
**Deliverables**: Working CLI prototype, architecture doc, demo video, source code, evaluation report

---

## Architecture Overview

### High-Level Data Flow

```
┌─────────────────────────────────────┐
│  Engineer CLI Input (Typer + Rich)  │
│  "BGP is down, CPU spiked"          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   LangGraph Supervisor Agent         │
│   ┌──────────────────────────────┐   │
│   │ Route query → Choose tools   │   │
│   │ Manage conversation state    │   │
│   │ Format response with evidence│   │
│   └──────────────────────────────┘   │
└──┬────────┬──────────┬──────────┬────┘
   │        │          │          │
   │   ┌────▼──┐  ┌────▼──┐  ┌───▼──┐
   │   │Log    │  │Metrics│  │Topo  │
   │   │Agent  │  │Agent  │  │Agent │
   │   └────┬──┘  └────┬──┘  └───┬──┘
   │        │          │          │
┌──▼────────▼──────────▼──────────▼──────────────┐
│           Data Retrieval Layer                 │
├──────────────────────────────────────────────┐ │
│ ChromaDB (Vector DB)                         │ │
│ • Embedded syslog chunks                     │ │
│ • Embedded device descriptions               │ │
│ • Embedded topology facts                    │ │
│ • Embedded incident resolutions              │ │
├──────────────────────────────────────────────┤ │
│ SQLite (Metrics Time-Series)                 │ │
│ • CPU, memory, packet drops over time        │ │
│ • Thresholds and status                      │ │
├──────────────────────────────────────────────┤ │
│ NetworkX Graph (Topology)                    │ │
│ • Device nodes, link connections             │ │
│ • Blast radius traversal (BFS/DFS)           │ │
└──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. **Data Ingestion Layer** (`src/network_guy/data/`)

#### 1.1 Data Loader (`loader.py`)
- **Purpose**: Parse all 4 input file types and prepare for storage
- **Inputs**:
  - `router_syslog.log` → parse timestamp, severity, device, event, metrics
  - `device_inventory.csv` → load device metadata (vendor, model, version, status)
  - `network_topology.json` → load device connections, link types, BGP peers
  - `snmp_metrics.csv` → load time-series data (CPU%, memory%, packet drops)
  - `incident_tickets.json` → load past incidents, resolutions
- **Output**: Structured Python dicts ready for embedding/storage
- **Key logic**:
  ```python
  parse_syslog(file_path) → List[LogEvent]
  load_inventory(file_path) → Dict[device_id, DeviceMetadata]
  load_topology(file_path) → Dict[link_id, TopologyLink]
  load_metrics(file_path) → List[MetricReading]
  load_incidents(file_path) → List[IncidentTicket]
  ```

#### 1.2 Chunker & Embedder (`embedder.py`)
- **Purpose**: Convert structured data into text chunks, embed, store in ChromaDB
- **Logic**:
  - Syslog: Group by 5-min time windows → chunk = "At 08:15, router CPU hit 92%, BGP dropped, interface went down"
  - Inventory: Convert row to sentence = "ROUTER-LAB-01 is Cisco ASR 9000 running IOS-XE 17.6.1, currently DEGRADED"
  - Topology: Convert link to sentence = "ROUTER-LAB-01 connects to ROUTER-LAB-02 via 10G BGP peering link"
  - Incidents: Keep as-is, embed title + symptom + resolution
- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2` (free, local, 384-dim)
- **Output**: Stored in ChromaDB with metadata (timestamp, device_id, severity, source_file)

---

### 2. **Data Storage Layer** (`src/network_guy/stores/`)

#### 2.1 Vector Store (`vector.py`)
- **Purpose**: Semantic search over logs, topology, incidents
- **Technology**: ChromaDB (local, embeddable)
- **Collections**:
  - `syslog_chunks` — log events grouped by time window
  - `device_metadata` — inventory descriptions
  - `topology_facts` — network connections and links
  - `incident_resolutions` — past incidents with solutions
- **Query pattern**:
  ```python
  results = vector_db.search(
    query="CPU spike causes BGP to drop",
    collection="syslog_chunks",
    top_k=5
  )
  # Returns: [chunk_text, metadata, relevance_score]
  ```

#### 2.2 Metrics DB (`metrics_db.py`)
- **Purpose**: Structured queries over SNMP time-series
- **Technology**: SQLite with raw SQL
- **Schema**:
  ```sql
  CREATE TABLE metrics (
    timestamp TEXT,
    device_id TEXT,
    metric_name TEXT,        -- 'cpu_utilization', 'packet_drops_per_sec', etc
    value REAL,
    unit TEXT,
    status TEXT,             -- 'OK', 'WARNING', 'CRITICAL'
    PRIMARY KEY(timestamp, device_id, metric_name)
  );
  CREATE INDEX idx_device_time ON metrics(device_id, timestamp);
  ```
- **Query patterns**:
  ```python
  # Get CPU for ROUTER-LAB-01 between 08:10-08:20
  SELECT * FROM metrics
  WHERE device_id='ROUTER-LAB-01'
    AND metric_name='cpu_utilization'
    AND timestamp BETWEEN '08:10' AND '08:20'
  ORDER BY timestamp;

  # Find all devices in CRITICAL state
  SELECT DISTINCT device_id FROM metrics
  WHERE status='CRITICAL' AND timestamp > NOW() - INTERVAL '1 hour';
  ```

#### 2.3 Topology Graph (`graph.py`)
- **Purpose**: Map device connections, calculate blast radius
- **Technology**: NetworkX (Python graph library)
- **Data structure**:
  ```python
  G = nx.DiGraph()  # Directed graph
  G.add_node('ROUTER-LAB-01', type='router', vendor='Cisco')
  G.add_edge('ROUTER-LAB-01', 'ROUTER-LAB-02',
    link_type='BGP_PEERING', bandwidth='10G')
  ```
- **Query patterns**:
  ```python
  # Get blast radius: if node A fails, which downstream nodes break?
  downstream = nx.descendants(G, 'ROUTER-LAB-01')  # BFS from node

  # Find all paths between two devices
  paths = nx.all_simple_paths(G, 'ROUTER-LAB-01', 'ROUTER-LAB-02')

  # Find critical nodes (high in-degree/out-degree)
  criticality = dict(G.in_degree())
  ```

---

### 3. **Agent Layer** (`src/network_guy/agents/`)

Each agent is a **tool function** called by the supervisor. Not autonomous — deterministic.

#### 3.1 Log Analyst Agent (`log_analyst.py`)
- **Purpose**: Extract relevant log events, identify error patterns
- **Input**: Engineer query + time range + affected device(s)
- **Process**:
  1. Semantic search ChromaDB for relevant syslog chunks
  2. Parse timestamps, severity, event type
  3. Group by device and event category (CPU, BGP, interface, process crash)
  4. Return ranked list: severity × recency × relevance
- **Output**:
  ```python
  {
    "log_events": [
      {
        "timestamp": "2024-03-15T08:15:03Z",
        "device": "ROUTER-LAB-01",
        "severity": "ERROR",
        "event": "BGP peer 10.0.0.3 session dropped",
        "reason": "Hold timer expired",
        "evidence_chunk": "log line 342: ..."
      }
    ],
    "error_patterns": ["CPU spike → BGP timeout"],
    "confidence": 0.92
  }
  ```

#### 3.2 Metrics Agent (`metrics.py`)
- **Purpose**: Query time-series data, detect anomalies
- **Input**: Device(s), time range, metric names
- **Process**:
  1. Query SQLite for CPU, memory, packet drops in time window
  2. Check against thresholds (WARN, CRIT)
  3. Detect trends: is metric rising/falling? How fast?
  4. Correlate spike timestamps with log events
- **Output**:
  ```python
  {
    "metrics": [
      {
        "device": "ROUTER-LAB-01",
        "metric": "cpu_utilization",
        "values": [(timestamp, value), ...],
        "peak": 92,
        "peak_time": "2024-03-15T08:15:00Z",
        "status": "CRITICAL",
        "trend": "spike then recovery"
      }
    ],
    "anomalies": ["CPU jumped from 40% to 92% in 5 min"],
    "confidence": 0.88
  }
  ```

#### 3.3 Topology Agent (`topology.py`)
- **Purpose**: Map network connections, find blast radius
- **Input**: Device(s) that failed
- **Process**:
  1. Load topology graph from JSON
  2. Find downstream devices (BFS from failed node)
  3. Identify critical links/paths affected
  4. Estimate impact scope (how many test cases blocked?)
- **Output**:
  ```python
  {
    "failed_device": "ROUTER-LAB-01",
    "downstream_devices": ["ROUTER-LAB-02", "SW-LAB-01", "5G-AMF-01"],
    "affected_links": 3,
    "critical_paths_lost": 12,
    "impact_summary": "Redundancy lost for 5G test automation",
    "blast_radius_diagram": "ASCII diagram"
  }
  ```

#### 3.4 Incident Memory Agent (`incident.py`)
- **Purpose**: Find historical correlations
- **Input**: Current symptoms (log patterns, metrics anomalies)
- **Process**:
  1. Semantic search ChromaDB for incident descriptions
  2. Match current symptoms to past incidents
  3. Return ranked matches with resolution steps
- **Output**:
  ```python
  {
    "historical_matches": [
      {
        "incident_id": "INC-2024-0228-003",
        "similarity_score": 0.91,
        "symptoms": "CPU spike + BGP hold timer expiry",
        "root_cause": "Memory exhaustion from traffic burst",
        "resolution": "Applied BGP graceful-restart config + memory guards",
        "commands": ["router bgp 65001", "bgp graceful-restart", ...]
      }
    ]
  }
  ```

---

### 4. **Orchestration Layer** (`src/network_guy/supervisor.py`)

#### LangGraph Supervisor
- **Purpose**: Route queries, call agents in sequence/parallel, synthesize results
- **State machine**:
  ```
  START
    ↓
  Parse Query (what device? what symptom?)
    ↓
  [PARALLEL] Call agents: Log + Metrics + Topology + Incident
    ↓
  Synthesize findings into RCA
    ↓
  Generate remediation steps (device-specific CLI commands)
    ↓
  Format response with evidence citations
    ↓
  Store in conversation memory
    ↓
  END
  ```
- **Prompt engineering**: System prompt instructs Claude to:
  - Always cite evidence (log line number, metric timestamp)
  - Rank root causes by confidence (0-1)
  - Suggest step-by-step remediation
  - Explain in plain English
  - Note any version mismatches or known issues

---

### 5. **CLI Interface** (`src/network_guy/cli.py`)

- **Framework**: Typer (async, simple)
- **Commands**:
  ```bash
  network-guy init                    # Load data files, build stores
  network-guy query "BGP is down"     # Single query
  network-guy chat                    # Interactive multi-turn session
  network-guy list-devices            # Show inventory
  network-guy show-topology           # Print ASCII topology
  network-guy search-incidents        # Search historical incidents
  network-guy benchmark               # Run 10 test queries
  ```
- **Output formatting**: Rich library for tables, panels, syntax highlighting

---

### 6. **Prompt Engineering** (`src/network_guy/prompts/system.py`)

Critical for RCA quality. Template:

```
You are a network troubleshooting expert. Analyze the provided context and answer the engineer's question.

INSTRUCTIONS:
1. Root Cause Analysis
   - Identify most likely root cause
   - Provide confidence score (0-1)
   - CITE EVIDENCE: reference specific log lines, metric timestamps, topology facts

2. Remediation Steps
   - Provide step-by-step fix instructions
   - Include device-specific CLI commands if applicable
   - Note any risks or prerequisites

3. Evidence Grounding
   - Every claim must cite source
   - Format: "Based on log line 342 (CPU 92%), metric spike at 08:15, and BGP drop at 08:15:03..."

4. Historical Context
   - If similar incident found, note it and reference resolution

5. Severity & Impact
   - Which devices impacted?
   - How many test cases blocked?
   - Is this P1 or P2?

CONTEXT:
- Device inventory: {inventory}
- Network topology: {topology}
- Available log events: {log_results}
- Current metrics: {metrics_results}
- Related incidents: {incident_results}

QUESTION: {user_query}
```

---

## Technology Stack

| Layer | Tool | Purpose | Why |
|-------|------|---------|-----|
| **LLM** | Claude API (Anthropic) | Generate RCA + remediation | Best at structured reasoning + citations |
| **Orchestration** | LangGraph | Multi-agent workflow | Explicit state graph, easy to debug |
| **Vector DB** | ChromaDB | Semantic search (logs, incidents) | Local, no server, embeddable |
| **Time-Series** | SQLite | Query metrics (CPU, memory) | Fast, structured, no external deps |
| **Graph** | NetworkX | Topology + blast radius | Pure Python, BFS/DFS algorithms |
| **Embeddings** | sentence-transformers | Local embeddings | Free, no API key, 384-dim vectors |
| **CLI** | Typer + Rich | User interface | Fast to build, beautiful output |
| **Language** | Python 3.11+ | Implementation | Type hints, async/await, poetry |

---

## Data Files (Provided in Hackathon)

| File | Format | Purpose | Example |
|------|--------|---------|---------|
| `router_syslog.log` | Text | Log events | `2024-03-15T08:15:00Z [ERROR] ROUTER-LAB-01 BGP drop` |
| `device_inventory.csv` | CSV | Device metadata | Device ID, type, vendor, model, version, status |
| `network_topology.json` | JSON | Device connections | Nodes, links, BGP peers, VLANs |
| `snmp_metrics.csv` | CSV | Time-series metrics | Timestamp, device, CPU%, memory%, packet drops |
| `incident_tickets.json` | JSON | Past incidents | ID, severity, symptoms, resolution, commands |

---

## Project Structure

```
network_guy/
├── pyproject.toml                    # Poetry config + dependencies
├── README.md                         # Setup instructions
├── IMPLEMENTATION_PLAN.md            # This file
├── ANALYSIS.md                       # Architecture deep-dive
│
├── src/network_guy/
│   ├── __init__.py
│   ├── cli.py                        # Typer CLI entry point
│   ├── supervisor.py                 # LangGraph orchestrator
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── log_analyst.py            # Parse logs, find patterns
│   │   ├── metrics.py                # Query metrics, detect anomalies
│   │   ├── topology.py               # Map blast radius
│   │   └── incident.py               # Historical correlation
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py                 # Parse all 4 file types
│   │   └── embedder.py               # Chunk + embed into ChromaDB
│   │
│   ├── stores/
│   │   ├── __init__.py
│   │   ├── vector.py                 # ChromaDB wrapper
│   │   ├── metrics_db.py             # SQLite wrapper
│   │   └── graph.py                  # NetworkX topology
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── system.py                 # RCA system prompt
│   │
│   └── models.py                     # Pydantic models (LogEvent, etc)
│
├── data/                             # Sample input files (provided)
│   ├── router_syslog.log
│   ├── device_inventory.csv
│   ├── network_topology.json
│   ├── snmp_metrics.csv
│   └── incident_tickets.json
│
├── tests/
│   ├── test_loader.py                # Unit test data ingestion
│   ├── test_stores.py                # Unit test storage queries
│   ├── test_agents.py                # Unit test individual agents
│   └── test_integration.py           # End-to-end query tests
│
├── notebooks/                        # (Optional) Dev exploration
│   └── explore_data.ipynb
│
└── .github/workflows/
    └── ci.yml                        # GitHub Actions (optional)
```

---

## Implementation Phases

### Phase 0: Setup (Day 1)
- [ ] Initialize Poetry project + dependencies
- [ ] Create folder structure
- [ ] Write data models (Pydantic)
- [ ] Set up ChromaDB, SQLite, NetworkX

### Phase 1: Data Ingestion (Days 1-2)
- [ ] Implement `loader.py` — parse all 4 file types
- [ ] Implement `embedder.py` — chunk + embed
- [ ] Test with sample data files
- [ ] Build `vector.py`, `metrics_db.py`, `graph.py` wrappers

### Phase 2: Agents (Days 2-3)
- [ ] Log analyst agent
- [ ] Metrics agent
- [ ] Topology agent
- [ ] Incident agent
- [ ] Unit test each agent in isolation

### Phase 3: Orchestration (Days 3-4)
- [ ] Build LangGraph supervisor
- [ ] Implement query router logic
- [ ] Implement evidence citation logic
- [ ] Prompt engineering for RCA quality

### Phase 4: CLI + Testing (Days 4-5)
- [ ] Implement Typer CLI
- [ ] Build interactive chat mode
- [ ] Run 10 benchmark queries
- [ ] Document accuracy/latency/limitations

### Phase 5: Polish (Days 5-6)
- [ ] Write README with setup + example queries
- [ ] Create demo script (for video)
- [ ] Finalize architecture doc
- [ ] Prepare evaluation report

---

## Dependencies (Poetry)

```toml
[tool.poetry.dependencies]
python = "^3.11"
anthropic = "^0.25"           # Claude API
langgraph = "^0.1"            # Orchestration
langchain-core = "^0.1"       # Utilities
chroma-db = "^0.4"            # Vector DB
sentence-transformers = "^3"  # Embeddings
networkx = "^3"               # Graph
pandas = "^2"                 # Data processing (optional)
typer = "^0.9"                # CLI
rich = "^13"                  # Formatted output
pydantic = "^2"               # Data validation

[tool.poetry.dev-dependencies]
pytest = "^7"
black = "^24"
ruff = "^0.1"
```

---

## Evaluation Against Hackathon Criteria

### ✅ Root Cause Accuracy (30%)
- Evidence citations from log/metric/topology data
- Ranked root causes with confidence scores
- Test against 10 benchmark queries

### ✅ Evidence Grounding (20%)
- Every RCA claim cites source (log line, metric timestamp, topology fact)
- Prompt engineering ensures grounding
- Traceability from claim → data

### ✅ Remediation Quality (20%)
- Device-specific CLI commands (Cisco IOS-XE, etc.)
- Step-by-step instructions
- Cross-referenced with incident memory

### ✅ System Design (15%)
- Modular agents (swappable for live network later)
- Adapter pattern for data sources
- Scalable: easy to add more devices/logs/metrics

### ✅ Innovation & UX (15%)
- Interactive multi-turn conversation
- Beautiful CLI output (Rich formatting)
- Blast radius visualization (ASCII diagram)
- Incident correlation (novel approach)

---

## Success Metrics

By end of hackathon:

| Metric | Target | Stretch |
|--------|--------|---------|
| **Query latency** | <60 sec | <30 sec |
| **RCA accuracy** | 8/10 benchmark queries correct | 9/10 |
| **Evidence citation** | 100% of claims cited | 100% with <50ms lookup |
| **CLI usability** | 3 commands (init, query, chat) | 8+ commands |
| **Code quality** | Type hints + tests | 80%+ coverage |
| **Documentation** | README + architecture doc | Video + blog post |

---

## Next Steps

1. **Approve this plan** — any changes?
2. **Set up Poetry project** — dependencies + folder structure
3. **Start Phase 0-1** — data loading + storage
4. **Iterate** — build agent by agent, test end-to-end

Ready to start building?
