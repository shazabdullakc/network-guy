# 🚀 Network Troubleshooting Assistant — Implementation Brief

## What We're Building

An AI agent that answers network troubleshooting questions in plain English and provides evidence-backed root cause analysis (RCA) + remediation steps.

**Example interaction:**
```
Engineer: "ROUTER-LAB-01 is dropping packets and BGP sessions are flapping. What's the issue?"

System:
  Root Cause (Confidence: 92%): CPU exhaustion triggered BGP hold-timer expiry

  Evidence:
    • CPU spiked to 92% at 08:15:00 (syslog line 342)
    • BGP session dropped at 08:15:03 (syslog line 345)
    • Packet drops hit 4,523 pps (metric peak at 08:15)

  Fix Steps:
    1. Restart BGP daemon: router bgp 65001 → no shutdown
    2. Apply graceful-restart: bgp graceful-restart timers restart 120
    3. Monitor CPU recovery

  Historical Context:
    Similar incident INC-2024-0228-003 had identical symptoms.
    Resolution: memory guards + BGP timer tuning
```

---

## Each Component & Its Job

### 1. **Data Ingestion** — Loads all your network data
- Reads: syslog, device inventory, network topology, SNMP metrics, incident history
- Outputs: Structured data ready for analysis
- Tools: Python file parsing, Pandas

### 2. **Data Storage** — Stores data for fast searching
| What | Where | Why |
|------|-------|-----|
| Log chunks + topology facts | ChromaDB (vector DB) | Semantic search: "find logs related to BGP timeout" |
| CPU%, memory%, packet drops | SQLite | Time-series queries: "get CPU for ROUTER-LAB-01 from 08:10-08:20" |
| Network topology | NetworkX graph | Blast radius: "if this router dies, what breaks downstream?" |

### 3. **Agents** — Specialized workers that answer specific questions
| Agent | Question | Answer |
|-------|----------|--------|
| **Log Analyst** | "What happened in the logs?" | List of errors, patterns, event timeline |
| **Metrics Agent** | "What were the CPU/memory readings?" | Thresholds exceeded, trends, anomalies |
| **Topology Agent** | "What devices are affected?" | Blast radius, downstream impact, critical paths |
| **Incident Agent** | "Has this happened before?" | Historical matches + proven resolutions |

### 4. **Supervisor** — Orchestrator that ties everything together
- Gets engineer query: "BGP is down"
- Decides which agents to call (all 4 in parallel)
- Synthesizes their results into coherent RCA
- Generates step-by-step remediation commands
- Cites evidence for every claim
- Tools: LangGraph (multi-agent orchestration), Claude API (LLM)

### 5. **CLI** — User interface (command line)
- Simple commands:
  ```bash
  network-guy init              # Load data
  network-guy query "BGP down"  # Single query
  network-guy chat              # Multi-turn conversation
  ```
- Tools: Typer (CLI framework), Rich (pretty output)

---

## Complete Tool & Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    TECHNOLOGY STACK                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🧠 LLM: Claude API (Anthropic)                                │
│     └─ Generates RCA, remediation, explanations               │
│                                                                 │
│  🤖 Orchestration: LangGraph                                   │
│     └─ Routes queries, calls agents, manages state             │
│                                                                 │
│  📄 Vector DB: ChromaDB                                        │
│     └─ Stores embedded logs, incidents, topology              │
│     └─ Semantic search: "find logs about BGP timeouts"        │
│                                                                 │
│  📊 Metrics Store: SQLite                                      │
│     └─ Time-series data: CPU%, memory%, packet drops          │
│     └─ SQL queries: "get CPU for device X from 08:10-08:20"  │
│                                                                 │
│  🌐 Topology Graph: NetworkX                                   │
│     └─ Device connections, link types                         │
│     └─ Blast radius: "if node A dies, which B,C,D break?"     │
│                                                                 │
│  🏷️  Embeddings: sentence-transformers                         │
│     └─ Local, free, fast                                       │
│     └─ Converts text → 384-dimensional vectors                │
│                                                                 │
│  💻 Programming: Python 3.11+                                  │
│     └─ Type hints, async/await                                │
│     └─ Dependency mgmt: Poetry                                 │
│                                                                 │
│  🎨 CLI: Typer + Rich                                          │
│     └─ Beautiful command-line interface                       │
│     └─ Tables, syntax highlighting, progress bars             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## How Each Tool Works

### Claude API
- **What**: Anthropic's LLM (language model)
- **Why**: Best at structured reasoning + citing evidence
- **Where**: Generates RCA text, remediation commands, explanations
- **Cost**: ~$0.003 per query (hackathon free tier available)

### LangGraph
- **What**: Graph-based multi-agent orchestration framework
- **Why**: Explicit state machine (easier to debug than CrewAI)
- **Where**: Routes queries → calls 4 agents → synthesizes results
- **Example**:
  ```python
  graph = StateGraph(QueryState)
  graph.add_node("log_analyst", log_analyst_func)
  graph.add_node("metrics", metrics_func)
  graph.add_node("supervisor", supervisor_func)
  graph.add_edge("START", "log_analyst")
  graph.add_edge("START", "metrics")  # Parallel
  graph.add_edge(["log_analyst", "metrics"], "supervisor")
  ```

### ChromaDB
- **What**: Vector database (stores embeddings)
- **Why**: Semantic search without external API
- **Where**: Stores log chunks + incident descriptions
- **Example**:
  ```python
  vector_db.add(
    collection="syslog_chunks",
    documents=["At 08:15, CPU hit 92%"],
    metadatas=[{"timestamp": "08:15", "device": "ROUTER-LAB-01"}]
  )
  results = vector_db.query(
    query_texts=["CPU spike causes BGP drop"],
    n_results=5
  )
  ```

### SQLite
- **What**: Lightweight SQL database
- **Why**: Perfect for time-series metrics (no server needed)
- **Where**: Stores SNMP readings with timestamps
- **Example**:
  ```sql
  SELECT * FROM metrics
  WHERE device_id='ROUTER-LAB-01'
    AND metric_name='cpu_utilization'
    AND timestamp BETWEEN '08:10' AND '08:20'
  ORDER BY timestamp;
  ```

### NetworkX
- **What**: Python graph library
- **Why**: Calculate blast radius (which devices break if A fails?)
- **Where**: Loads topology, does BFS/DFS traversal
- **Example**:
  ```python
  G = nx.DiGraph()
  G.add_edge('ROUTER-LAB-01', 'ROUTER-LAB-02')
  G.add_edge('ROUTER-LAB-02', 'SW-LAB-01')

  # If ROUTER-LAB-01 dies, what's affected?
  downstream = nx.descendants(G, 'ROUTER-LAB-01')
  # Result: {'ROUTER-LAB-02', 'SW-LAB-01'}
  ```

### sentence-transformers
- **What**: Free embedding model
- **Why**: Converts text → vectors for semantic search
- **Where**: Embeds syslog chunks, incident descriptions
- **Speed**: ~100ms to embed 1000 chunks (local)

### Typer + Rich
- **What**: CLI framework + pretty output
- **Why**: Fast to build, beautiful formatted output
- **Where**: User interface
- **Example**:
  ```bash
  $ network-guy query "BGP is down"

  ╭─ Root Cause ─────────────────────╮
  │ CPU exhaustion (Confidence: 92%) │
  ╰───────────────────────────────────╯

  Evidence:
  • CPU spiked to 92% at 08:15:00
  • BGP dropped at 08:15:03

  Fix:
  1. router bgp 65001
  2. no shutdown
  ```

---

## Alignment with Hackathon Requirements

| Requirement | How We Meet It |
|-------------|----------------|
| **F1: Natural Language Query** | Typer CLI accepts English questions → LangGraph routes to Claude |
| **F2: Multi-Source Ingestion** | Loader.py parses syslog, inventory, topology, metrics, incidents |
| **F3: Root Cause Analysis** | Claude + agent findings → ranked RCA with confidence scores |
| **F4: Remediation Steps** | Claude generates device-specific CLI commands |
| **F5: Historical Correlation** | Incident agent searches ChromaDB for past incidents |
| **F6: Conversation Memory** | LangGraph has built-in conversation checkpointing |
| **F7: Evidence Citation** | Every claim includes source (log line, metric timestamp, topology fact) |
| **F8: Severity & Impact** | Topology agent calculates blast radius, impact scope |
| **Evaluation 1: RCA Accuracy (30%)** | Test against 10 benchmark queries, measure correctness |
| **Evaluation 2: Evidence Grounding (20%)** | Every claim cites source data |
| **Evaluation 3: Remediation Quality (20%)** | Device-specific commands, step-by-step |
| **Evaluation 4: System Design (15%)** | Modular agents, adapter pattern for live network later |
| **Evaluation 5: UX (15%)** | Rich CLI output, multi-turn conversation |

---

## Timeline (2 weeks)

| Phase | Days | What | Deliverable |
|-------|------|------|-------------|
| **Setup** | 1 | Poetry config, folder structure | pyproject.toml |
| **Data Loading** | 1-2 | Parse all 4 file types | loader.py + tests |
| **Storage** | 2 | Build ChromaDB, SQLite, NetworkX wrappers | stores/ module |
| **Agents** | 2-3 | Implement 4 agents (log, metrics, topo, incident) | agents/ module |
| **Orchestration** | 3-4 | LangGraph supervisor + prompt engineering | supervisor.py |
| **CLI + Testing** | 4-5 | Typer interface + run 10 benchmark queries | cli.py + test results |
| **Polish** | 5-6 | README, demo script, architecture doc | GitHub repo ready |

---

## How to Start

1. **Review this plan** — Any questions or changes?
2. **Next: Set up Poetry** — Create pyproject.toml with all dependencies
3. **Next: Implement Phase 0-1** — Data loading + storage
4. **Iterate** — Build agent by agent, test continuously

Ready? Let me know if anything needs clarification.
