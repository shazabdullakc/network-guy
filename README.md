<p align="center">
  <h1 align="center">Network Guy</h1>
  <p align="center">
    AI-Powered Network Troubleshooting Assistant for Telecom Test Labs
  </p>
  <p align="center">
    <a href="#features">Features</a> &middot;
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#usage">Usage</a> &middot;
    <a href="#architecture">Architecture</a> &middot;
    <a href="#benchmark">Benchmark</a>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/LLM-Gemini%20%7C%20DeepSeek%20%7C%20Claude-green" alt="LLM Support">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/status-hackathon--ready-brightgreen" alt="Status">
</p>

---

When a network goes down, engineers waste hours SSH-ing into devices, grepping through logs, and cross-referencing metrics across disconnected systems. **Network Guy** fixes this.

Type a question in plain English. Get an evidence-backed root cause analysis in under 60 seconds.

```
❯ ROUTER-LAB-01 is dropping packets and BGP is flapping. What's the root cause?

┌─ Root Cause Analysis ────────────────────────────────────────────┐
│                                                                   │
│  Root Cause: Memory exhaustion triggered CPU spike (92%) which   │
│  caused BGP hold timer expiry and session drop with peer 10.0.0.3│
│  Confidence: 95%                                                  │
│                                                                   │
│  Evidence:                                                        │
│  - CPU spiked to 92% at 08:15 (snmp_metrics.csv row 14)         │
│  - BGP peer dropped at 08:15:03 (router_syslog.log line 9)      │
│  - Packet drops: 4,523 pps (snmp_metrics.csv row 16)            │
│                                                                   │
│  Fix:                                                             │
│  1. router bgp 65001 → bgp graceful-restart                     │
│  2. memory free low-watermark processor 20                       │
│                                                                   │
│  Historical Match: INC-2024-0228-003 (91% similar)               │
│  Blast Radius: 6 devices affected                                 │
│  Security: LEGITIMATE FAILURE (not an attack)                     │
└───────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-Agent Analysis** — 5 specialized agents run simultaneously: log analysis, metrics correlation, topology mapping, incident history, and security assessment
- **Evidence-Backed RCA** — every claim cites a specific log line, metric timestamp, or topology fact. No hallucinations.
- **Attack Detection** — distinguishes between legitimate failures and 7 types of network attacks (DDoS, brute force, BGP hijack, ARP spoofing, port scanning, unauthorized access, rogue devices)
- **Blast Radius Mapping** — calculates which downstream devices are impacted when a node fails
- **Historical Correlation** — searches past incidents for similar symptoms and proven resolutions
- **Interactive CLI** — Claude Code-style REPL with `/slash` commands and autocomplete
- **Multi-LLM Support** — works with Gemini, DeepSeek, OpenRouter, Groq, Grok, or Anthropic Claude

## Quick Start

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- An LLM API key (any one of: Gemini, DeepSeek, OpenRouter, Groq, or Anthropic)

### Install

```bash
# Clone the repo
git clone https://github.com/shazabdullakc/network-guy.git
cd network-guy

# Install dependencies
poetry install

# Set your LLM API key (pick one)
export GEMINI_API_KEY="your-key-here"          # Free 1M tokens/day
# export DEEPSEEK_API_KEY="your-key-here"      # Free 50M tokens
# export OPENROUTER_API_KEY="your-key-here"    # Free models available
# export GROQ_API_KEY="your-key-here"          # Free fast inference
# export ANTHROPIC_API_KEY="your-key-here"     # Paid, best quality
```

### Run

```bash
# Launch interactive session (recommended)
poetry run network-guy

# Or one-off query
poetry run network-guy query "Why did BGP drop on ROUTER-LAB-01?"
```

### Global Install (optional)

```bash
# Install globally so `network-guy` works from any directory
pipx install .
network-guy
```

## Usage

### Interactive Mode

Just type `network-guy` to launch the interactive REPL:

```
── Network Guy v0.1.0 ──
╭────────────────────────────────────────╮╭────────────────────────────────────────╮
│ Welcome to Network Guy!                ││ Tips for getting started               │
│                                        ││ Ask a question like:                   │
│  ┌─┐                                   ││ "Why did BGP drop on ROUTER-LAB-01?"   │
│  │N│ Network Guy                       ││                                        │
│  │G│ AI Troubleshooting Assistant      ││ Quick commands                         │
│  └─┘                                   ││ /devices  /incidents  /security-scan   │
│                                        ││                                        │
│ gemini (gemini-2.5-flash)              ││ Network status                         │
╰────────────────────────────────────────╯│ 15 devices (4 unhealthy)               │
                                          │ 3 open incidents                       │
                                          ╰────────────────────────────────────────╯
❯ _
```

Type questions in plain English or use slash commands. Press `/` to see autocomplete suggestions.

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/devices` | List all network devices with status |
| `/topology` | Display network topology map |
| `/incidents` | List all open incidents with timelines |
| `/security-scan` | Run full security audit |
| `/metrics <device>` | Show metrics + anomalies for a device |
| `/blast <device>` | Calculate blast radius for a device |
| `/history` | Show conversation history |
| `/export` | Export session to markdown file |
| `/clear` | Clear screen |
| `/exit` | End session |

### One-Off Commands

```bash
network-guy query "What happened to ROUTER-LAB-01 between 08:10 and 08:20?"
network-guy devices
network-guy security-scan
network-guy benchmark
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              CLI / Interactive REPL                       │
│   Type a question → get evidence-backed RCA              │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│             LangGraph Supervisor Agent                    │
│  Parse query → Route to agents → Synthesize via LLM     │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┘
   │          │          │          │          │
┌──▼───┐  ┌──▼───┐  ┌───▼──┐  ┌───▼────┐  ┌──▼────────┐
│ Log  │  │Metric│  │ Topo │  │Incident│  │ Security  │
│Agent │  │Agent │  │Agent │  │ Agent  │  │  Agent    │
└──┬───┘  └──┬───┘  └───┬──┘  └───┬────┘  └──┬────────┘
   │         │          │         │           │
┌──▼─────────▼──────────▼─────────▼───────────▼──────────┐
│                    Data Layer                            │
│  ChromaDB (semantic search)  │  SQLite (metrics/flows)  │
│  NetworkX (topology graph)   │  7 data files ingested   │
└─────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | What It Does | Data Source | Query Method |
|-------|-------------|-------------|-------------|
| **Log Analyst** | Finds error patterns, builds event timelines | Syslog events | ChromaDB semantic search |
| **Metrics Agent** | Detects anomalies, threshold breaches, trends | SNMP metrics | SQLite SQL queries |
| **Topology Agent** | Maps blast radius, finds downstream impact | Network topology | NetworkX graph BFS |
| **Incident Agent** | Finds similar past incidents, proven fixes | Incident tickets | ChromaDB semantic search |
| **Security Agent** | Detects 7 attack types, builds attack chains | Security logs + flows | Signature matching + anomaly detection |

### Why RAG + SQL (Not Just One)

| Data Type | Why RAG (ChromaDB) | Why SQL (SQLite) |
|-----------|-------------------|-----------------|
| **Logs** | "BGP dropped" and "routing session timeout" mean the same thing — semantic search finds both | Can't do meaning-based search with `WHERE` |
| **Metrics** | Can't precisely filter "CPU > 80% between 08:10 and 08:15" with vectors | Exact numeric filtering with SQL |
| **Topology** | Graph traversal (BFS) for blast radius — neither RAG nor SQL can do this | NetworkX handles graph algorithms |

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM | Gemini / DeepSeek / Claude | Multi-provider, auto-detects available key |
| Vector DB | ChromaDB | Local, zero-infra, semantic search |
| Metrics Store | SQLite | Fast numeric queries, no server |
| Graph | NetworkX | Python-native graph algorithms |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Free, local, 384-dim vectors |
| CLI | Typer + Rich + prompt_toolkit | Beautiful output, autocomplete |
| Models | Pydantic v2 | Type-safe data validation |

## Data Sources

The system ingests 7 data files:

| File | Format | Contains |
|------|--------|----------|
| `router_syslog.log` | Text | 23 router events (INFO/WARN/ERROR/CRIT) |
| `device_inventory.csv` | CSV | 15 devices across 4 lab networks |
| `network_topology.json` | JSON | 7 nodes, 7 links, routing protocols, VLANs |
| `snmp_metrics.csv` | CSV | Time-series: CPU, memory, packet drops, BGP sessions |
| `incident_tickets.json` | JSON | 3 open incidents with timelines and history |
| `security_events.log` | Text | 34 security events (brute force, DDoS, scans) |
| `traffic_flows.csv` | CSV | 22 NetFlow records (normal + attack traffic) |

## Benchmark

18 benchmark queries covering RCA accuracy, evidence grounding, and security detection:

```bash
network-guy benchmark
```

### Sample Queries

| # | Query | Tests |
|---|-------|-------|
| 1 | "What happened to ROUTER-LAB-01 between 08:10 and 08:20?" | Timeline + RCA |
| 2 | "Why did BGP session with 10.0.0.3 drop?" | Specific root cause |
| 3 | "Which devices are in CRITICAL state?" | Status filtering |
| 4 | "If SW-LAB-02 is down, what's affected?" | Blast radius |
| 5 | "Has CPU spike + BGP drop happened before?" | Historical correlation |
| 6 | "Is someone attacking the network?" | Attack detection |
| 7 | "Show me the full attack timeline" | Security chain |

### Evaluation Criteria (Hackathon)

| Criterion | Weight | How We Score |
|-----------|--------|-------------|
| Root Cause Accuracy | 30% | 5 agents cross-reference 7 data sources |
| Evidence Grounding | 20% | Every claim cites source (log line, metric, topology) |
| Remediation Quality | 20% | Device-specific CLI commands from incident history |
| System Design | 15% | Modular agents, adapter pattern, multi-LLM |
| Innovation & UX | 15% | Attack detection + interactive CLI + autocomplete |

## Project Structure

```
network_guy/
├── src/network_guy/
│   ├── cli.py                 # Typer CLI entry point
│   ├── repl.py                # Interactive REPL with autocomplete
│   ├── supervisor.py          # Orchestrator (parse → agents → LLM)
│   ├── llm.py                 # Multi-provider LLM abstraction
│   ├── models.py              # 20+ Pydantic data models
│   ├── agents/
│   │   ├── log_analyst.py     # Syslog analysis + pattern detection
│   │   ├── metrics.py         # SNMP anomaly detection + trends
│   │   ├── topology.py        # Blast radius (NetworkX BFS)
│   │   ├── incident.py        # Historical correlation
│   │   └── security/
│   │       ├── security_agent.py  # Main security pipeline
│   │       ├── signatures.py      # 7 attack signature patterns
│   │       ├── anomaly.py         # Statistical anomaly detection
│   │       └── correlator.py      # Attack chain builder
│   ├── data/
│   │   ├── loader.py          # Parse all 7 file types
│   │   └── embedder.py        # Chunk + embed into stores
│   ├── stores/
│   │   ├── vector.py          # ChromaDB wrapper
│   │   ├── metrics_db.py      # SQLite wrapper
│   │   └── graph.py           # NetworkX wrapper
│   └── prompts/
│       └── system.py          # LLM system prompts
├── data/                      # Sample input files (7 files)
├── tests/                     # Test suite
├── pyproject.toml             # Dependencies (Poetry)
└── README.md                  # You are here
```

## LLM Providers

Network Guy auto-detects which API key is available:

| Provider | Env Variable | Model | Free Tier |
|----------|-------------|-------|-----------|
| Gemini | `GEMINI_API_KEY` | gemini-2.5-flash | 1M tokens/day |
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat | 50M tokens on signup |
| Groq | `GROQ_API_KEY` | llama-3.3-70b | Fast inference |
| OpenRouter | `OPENROUTER_API_KEY` | varies (free models) | Model-dependent |
| Grok | `GROK_API_KEY` | grok-3-mini | Free tier |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4 | Paid |

Priority order: DeepSeek > Gemini > Groq > OpenRouter > Grok > Anthropic

## Contributing

```bash
# Clone and install
git clone https://github.com/shazabdullakc/network-guy.git
cd network-guy
poetry install

# Run tests
poetry run pytest

# Run linter
poetry run ruff check src/
```

## License

MIT

---

<p align="center">
  Built for the AI-Powered Network Troubleshooting Hackathon.<br>
  <sub>Reducing MTTR from hours to seconds.</sub>
</p>
