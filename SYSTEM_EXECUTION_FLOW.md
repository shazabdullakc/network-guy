# System Execution Flow — From User Input to Answer

> What happens when engineer types a question. Step by step with diagrams.

---

## Step 1: User Runs CLI Command

```bash
$ network-guy query "ROUTER-LAB-01 is dropping packets and BGP is flapping. What's the root cause?"
```

This command:
1. Calls `cli.py` → `query_command()` function
2. Passes the query string to the **Supervisor Agent**
3. Starts the entire analysis pipeline

---

## Step 2: Supervisor Parses the Query

```python
# Inside supervisor.py

query = "ROUTER-LAB-01 is dropping packets and BGP is flapping. What's the root cause?"

# Supervisor extracts:
extracted = {
    "devices": ["ROUTER-LAB-01"],      # What device is affected?
    "symptoms": ["dropping packets", "BGP flapping"],  # What's broken?
    "time_range": "last 30 minutes",   # When did it happen?
    "intent": "root_cause_analysis"    # What does user want?
}
```

**This is important because:**
- Different queries need different agents
- "Why is CPU high?" → mostly metrics agent
- "Is someone attacking?" → security agent
- "What's the blast radius?" → topology agent

---

## Step 3: Route to Agents (The Magic)

The Supervisor decides: **Which agents should I call?**

```
User Query: "ROUTER-LAB-01 is dropping packets and BGP is flapping"

Supervisor thinks:
  "I need to understand:
   1. What HAPPENED (logs) → Call Log Analyst
   2. How BAD it was (metrics) → Call Metrics Agent
   3. What BROKE downstream (topology) → Call Topology Agent
   4. Is this NORMAL or ATTACK (history + security) → Call Incident + Security Agents"

Decision: Call ALL 5 agents (best approach for comprehensive RCA)
```

---

## Step 4: Agents Execute IN PARALLEL

This is the key optimization. All 5 agents run at the same time:

```
08:16:00.000 → Query submitted
           │
           ├──→ [PARALLEL] ─────────────────────────────────────────
           │                                                        │
           │    Agent 1: Log Analyst                              │
           │    ├─ Query: ChromaDB.search("ROUTER-LAB-01 errors") │
           │    ├─ Duration: ~200ms                               │
           │    └─ Output: Event timeline                         │
           │                                                        │
           │    Agent 2: Metrics Agent                            │
           │    ├─ Query: SQLite("SELECT * FROM metrics...")      │
           │    ├─ Duration: ~50ms                                │
           │    └─ Output: CPU/memory/bandwidth peaks             │
           │                                                        │
           │    Agent 3: Topology Agent                           │
           │    ├─ Query: NetworkX.BFS(ROUTER-LAB-01)            │
           │    ├─ Duration: ~30ms                                │
           │    └─ Output: Blast radius (5 devices affected)      │
           │                                                        │
           │    Agent 4: Incident Agent                           │
           │    ├─ Query: ChromaDB.semantic_search("symptoms")    │
           │    ├─ Duration: ~200ms                               │
           │    └─ Output: INC-2024-0228-003 (91% match)         │
           │                                                        │
           │    Agent 5: Security Agent                           │
           │    ├─ Query: Signature scan + anomaly check          │
           │    ├─ Duration: ~100ms                               │
           │    └─ Output: LEGITIMATE (not attack, 95% conf)      │
           │                                                        │
           └──→ [END PARALLEL] ──────────────────────────────────
                Total time: max(all) ≈ 200ms (not sum!)
```

**Why parallel?**
- Without parallelism: 200 + 50 + 30 + 200 + 100 = 580ms
- With parallelism: max(200, 50, 30, 200, 100) = 200ms
- **3x faster** just by running in parallel

---

## Step 5: Each Agent Does Its Job

Let me show what EACH agent actually does:

### Agent 1: Log Analyst

```
Input:  query="ROUTER-LAB-01", time_range="08:00-08:30"
        intent="find errors"

Process:
  1. ChromaDB search
     query_vector = embed("ROUTER-LAB-01 errors")
     results = chromadb.search(
         query=query_vector,
         collection="syslog_chunks",
         top_k=10,        # Get top 10 most relevant chunks
         where={"device": "ROUTER-LAB-01"}  # Filter by device
     )

  2. Parse results
     for chunk in results:
         extract: timestamp, severity, event_type, details
         sort by timestamp

  3. Identify patterns
     Pattern: High severity events clustered at 08:15
     Pattern: ERROR → ERROR → CRIT → CRIT → recovery
     Pattern: CPU warnings precede BGP drop

Output:
{
  "events": [
    {timestamp: "08:10:22", severity: "WARN", event: "CPU 78%", source: "syslog_line_6"},
    {timestamp: "08:15:00", severity: "ERROR", event: "GE0/2 DOWN", source: "syslog_line_8"},
    {timestamp: "08:15:03", severity: "ERROR", event: "BGP dropped", source: "syslog_line_9"},
    {timestamp: "08:17:00", severity: "CRIT", event: "bgpd crashed", source: "syslog_line_14"},
    ...
  ],
  "patterns": ["CPU spike precedes interface failure", "BGP timeout after memory pressure"],
  "timeline": "Escalation from WARN→ERROR→CRIT, then recovery"
}
```

### Agent 2: Metrics Agent

```
Input:  query="ROUTER-LAB-01", time_range="08:00-08:30"
        metrics=["cpu", "memory", "packet_drops", "bandwidth"]

Process:
  1. SQLite query
     SELECT timestamp, metric_name, metric_value, status
     FROM metrics
     WHERE device_id = 'D001'
       AND timestamp BETWEEN '08:00' AND '08:30'
       AND metric_name IN ('cpu_utilization', 'memory_utilization', ...)

  2. Analyze trends
     cpu_values = [45%, 58%, 78%, 92%, 82%, 65%, 48%]
     trend = "Sharp spike at 08:15, then gradual recovery"
     anomaly_score = (92 - baseline_mean) / baseline_stddev = 4.7σ
     ^ 4.7 standard deviations = HUGE anomaly (>99.9% confidence)

  3. Correlation check
     At 08:15:
       - CPU peaks 92% (CRITICAL)
       - Memory peaks 95% (CRITICAL)
       - Packet drops spike 4523 pps (CRITICAL)
     Correlation: all three spike SIMULTANEOUSLY
     ^ Indicates resource exhaustion (not independent failures)

Output:
{
  "metrics": {
    "cpu_utilization": {
      "baseline": 45%,
      "peak": 92%,
      "peak_time": "08:15",
      "threshold_crit": 90,
      "anomaly_zscore": 4.7,
      "status": "CRITICAL",
      "trend": "spike_then_recovery"
    },
    "memory_utilization": {
      "baseline": 60%,
      "peak": 95%,
      "peak_time": "08:15",
      "threshold_crit": 95,
      "anomaly_zscore": 3.2,
      "status": "CRITICAL"
    },
    "packet_drops_per_sec": {
      "baseline": 10,
      "peak": 4523,
      "peak_time": "08:15",
      "anomaly_zscore": 5.1,
      "status": "CRITICAL"
    }
  },
  "correlations": "All three metrics spike at same time → systemic issue",
  "impact": "Network is degraded, data loss occurring"
}
```

### Agent 3: Topology Agent

```
Input:  query="ROUTER-LAB-01"
        intent="find blast radius"

Process:
  1. Load topology graph
     G = load_topology_from_json()
     # G has 7 nodes, 7 edges

  2. Find downstream devices
     failed_node = "D001" (ROUTER-LAB-01)
     downstream = networkx.descendants(G, failed_node)
     # BFS: find all nodes reachable FROM failed node

  3. Calculate impact
     for device in downstream:
         is_critical = (in_degree > 1) or (out_degree > 1)
         # Device is critical if it's a hub (many connections)

Output:
{
  "failed_device": "ROUTER-LAB-01",
  "downstream_devices": ["ROUTER-LAB-02", "SW-LAB-01"],
  "cascade_level_2": ["FIREWALL-01", "LB-LAB-01", "PACKET-BROKER-01"],
  "all_affected": 5,
  "critical_links_affected": 3,
  "mpls_paths_lost": 12,
  "blast_radius": {
    "devices": ["D002", "D003", "D005", "D007", "D013"],
    "severity": "HIGH",
    "recovery_impact": "Feature validation blocked for Sprint-24"
  }
}
```

### Agent 4: Incident Agent

```
Input:  query_context={
          symptoms: ["CPU spike", "BGP drop", "packet loss"],
          affected_device: "ROUTER-LAB-01"
        }

Process:
  1. Semantic search for similar incidents
     symptom_vector = embed("CPU spike + BGP drop + memory pressure")
     similar_incidents = chromadb.search(
         query=symptom_vector,
         collection="incidents",
         top_k=5  # Get top 5 similar incidents
     )

  2. Score similarity
     for incident in similar_incidents:
         similarity_score = cosine_distance(query_vector, incident_vector)
         confidence = 1 - similarity_score

  3. Extract resolution
     best_match = similar_incidents[0]  # INC-2024-0228-003
     root_cause = best_match.root_cause
     resolution_steps = best_match.resolution

Output:
{
  "historical_matches": [
    {
      "incident_id": "INC-2024-0228-003",
      "similarity": 0.91,
      "symptoms": "High CPU (78%) → Memory pressure (88%) → BGP timeout",
      "root_cause": "Memory exhaustion from traffic burst",
      "resolution": [
        "Enable BGP graceful-restart",
        "Set memory low-watermark",
        "Configure OSPF hello interval adjustment"
      ],
      "mttr": "15 minutes",
      "success": true
    }
  ],
  "recommendation": "Apply resolution from INC-2024-0228-003"
}
```

### Agent 5: Security Agent

```
Input:  query_context={
          metrics: [CPU spike, packet loss],
          devices: ["ROUTER-LAB-01"],
          time_range: "08:00-08:30"
        }

Process:
  1. Signature scan
     security_events = parse_security_logs()
     for event in security_events:
         if event matches any of [brute_force, port_scan, ddos, ...]:
             add to findings

     Result: No malicious signatures found

  2. Anomaly detection
     Check if traffic patterns are suspicious:
       - Single IP scanning many ports? NO
       - Multiple IPs flooding from same subnet? NO
       - Unknown MAC addresses? NO
       - Config changes from unauthorized user? NO

     Result: No anomalies detected

  3. Verdict
     is_attack = (signature_hits > 0) OR (anomaly_score > threshold)
     verdict = is_attack ? "ATTACK" : "LEGITIMATE"

Output:
{
  "is_attack": false,
  "verdict": "LEGITIMATE FAILURE",
  "confidence": 0.95,
  "reason": "CPU/memory spike matches legitimate resource exhaustion pattern. No DDoS, scan, or compromise signatures detected.",
  "attack_type": null,
  "threat_level": "NONE"
}
```

---

## Step 6: Supervisor Collects All Agent Outputs

```python
# Inside supervisor.py

all_findings = {
    "log_analyst": log_agent_output,      # Event timeline
    "metrics": metrics_agent_output,      # Peaks + anomalies
    "topology": topology_agent_output,    # Blast radius
    "incident": incident_agent_output,    # Historical match
    "security": security_agent_output     # Attack verdict
}

# Now we have a 360° view of the problem
```

---

## Step 7: Claude Synthesizes RCA

The Supervisor sends ALL findings to Claude API with a system prompt:

```
System Prompt:
  "You are a network troubleshooting expert.
   Use the provided data to generate a root cause analysis.
   RULES:
   1. Always cite evidence (log line, metric, topology fact)
   2. Rank root causes by confidence
   3. Provide step-by-step remediation
   4. Distinguish legitimate failures from attacks
   5. Note version mismatches or known issues"

Agent Findings (context):
  Agent 1: "CPU went 45% → 92% at 08:15, memory went 60% → 95%"
  Agent 2: "Packet drops spiked 4523 pps at 08:15"
  Agent 3: "BGP dropped at 08:15:03 (hold timer expired)"
  Agent 4: "5 downstream devices affected"
  Agent 5: "This happened in INC-2024-0228-003, fixed with BGP graceful-restart"
  Agent 6: "Not an attack (95% confidence), legitimate failure"

Claude reasoning:
  "The timeline shows:
   1. CPU + memory spike at 08:15 (metrics)
   2. BGP drop immediately after (logs)
   3. This matches INC-2024-0228-003 (history)
   4. Not an attack (security)
   5. Fix worked before: BGP graceful-restart (history)
   Conclusion: Memory exhaustion caused CPU overload → BGP timeout"

Output:
  Root Cause: Memory exhaustion (Confidence: 92%)
  Evidence:
    • CPU spiked 92% at 08:15 (snmp_metrics.csv row 14)
    • Memory spiked 95% at 08:15 (snmp_metrics.csv row 15)
    • BGP dropped 2 seconds later (router_syslog.log line 9)
    • bgpd crashed at 08:17 (router_syslog.log line 14)
  Fix:
    1. router bgp 65001
    2. bgp graceful-restart
    3. memory free low-watermark processor 20
  Historical:
    INC-2024-0228-003 had identical symptoms.
    This fix succeeded and resolved the issue in 15 minutes.
  Impact:
    5 downstream devices affected (ROUTER-02, SW-LAB-01, etc)
    Feature validation blocked until resolved.
```

---

## Step 8: Format and Display Output

```python
# cli.py → format_response()

# Takes Claude's response and formats it beautifully with Rich

┌─────────────────────────────────────────────────────────────────┐
│                        ROOT CAUSE ANALYSIS                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Root Cause:   Memory exhaustion → CPU spike → BGP timeout     │
│  Confidence:   92%                                              │
│  Severity:     CRITICAL (P1)                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  EVIDENCE GROUNDING                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✓ CPU spiked from 45% to 92% at 08:15:00                     │
│    Source: snmp_metrics.csv row 14                             │
│                                                                 │
│  ✓ Memory spiked from 60% to 95% at 08:15:00                  │
│    Source: snmp_metrics.csv row 15                             │
│                                                                 │
│  ✓ BGP peer 10.0.0.3 session dropped at 08:15:03              │
│    Source: router_syslog.log line 9                            │
│    Reason: Hold timer expired                                   │
│                                                                 │
│  ✓ bgpd process crashed at 08:17:00                            │
│    Source: router_syslog.log line 14                           │
│                                                                 │
│  ✓ Packet drops spiked to 4523 pps                             │
│    Source: snmp_metrics.csv row 16                             │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  SECURITY ASSESSMENT                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Verdict:      LEGITIMATE FAILURE (not an attack)              │
│  Confidence:   95%                                              │
│  Reason:       No DDoS/scan/compromise signatures detected.    │
│                CPU/memory spike matches legitimate resource    │
│                exhaustion pattern.                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  REMEDIATION STEPS                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Configure BGP graceful-restart:                            │
│     router bgp 65001                                            │
│     bgp graceful-restart                                        │
│                                                                 │
│  2. Set memory low-watermark:                                  │
│     memory free low-watermark processor 20                      │
│                                                                 │
│  3. Monitor CPU recovery:                                       │
│     show processes cpu (should drop below 75%)                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  BLAST RADIUS (Impact Analysis)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Affected Devices:                                              │
│  • ROUTER-LAB-02 (lost BGP peer) ⚠️                            │
│  • SW-LAB-01 (trunk link degraded) ⚠️                          │
│  • FIREWALL-01 (downstream impact)                             │
│  • LB-LAB-01 (downstream impact)                               │
│  • DNS-SERVER-01 (management link affected)                    │
│                                                                 │
│  Critical Paths Lost:  12 MPLS LSPs                            │
│  Redundancy Impact:    LOST (no secondary route)               │
│  Tests Blocked:        5G feature regression suite             │
│  Estimated Recovery:   5-10 minutes with fix                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  HISTORICAL CONTEXT                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Similar Incident:     INC-2024-0228-003                       │
│  Similarity Score:     91%                                      │
│  Symptoms:             CPU spike → BGP timeout → bgpd crash    │
│  Resolution Applied:   BGP graceful-restart + memory guards    │
│  Outcome:              ✓ Successful (resolved in 15 min)       │
│                                                                 │
│  Recommendation:       Apply same fix as INC-2024-0228-003     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Complete Data Flow (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│  1. USER INPUT (CLI)                                        │
│  $ network-guy query "ROUTER-LAB-01 dropping packets"      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  2. SUPERVISOR PARSES QUERY                                 │
│  Extract: devices, symptoms, time_range, intent             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  3. ROUTE TO AGENTS (Decide what to call)                   │
│  Decision: All 5 agents needed → parallel execution         │
└──┬────────┬──────────┬──────────┬────────┬───────────────────┘
   │        │          │          │        │
   ▼        ▼          ▼          ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌─────────┐
│ Log  │ │Metric│ │ Topo │ │Incident│ │Security │
│Agent │ │Agent │ │Agent │ │ Agent  │ │ Agent   │
└──┬───┘ └──┬───┘ └──┬───┘ └────┬───┘ └────┬────┘
   │        │        │          │           │
   ▼        ▼        ▼          ▼           ▼
┌──────────────────────────────────────────────────────┐
│  4. AGENTS QUERY DATA STORES (PARALLEL - 200ms)     │
│                                                      │
│  ChromaDB   SQLite      NetworkX   ChromaDB  Hybrid  │
│  (search)   (query)     (traverse)  (search)  (scan) │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  5. AGENTS RETURN FINDINGS                           │
│  {log_timeline, metrics_peaks, blast_radius,        │
│   historical_match, security_verdict}                │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  6. SUPERVISOR COLLECTS ALL FINDINGS                 │
│  360° view of the problem                            │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  7. SEND TO CLAUDE API                               │
│  System prompt + all agent findings                  │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  8. CLAUDE SYNTHESIZES RCA                           │
│  Generates evidence-backed root cause analysis       │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  9. FORMAT & DISPLAY (Rich CLI)                      │
│  Beautiful formatted output with citations           │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│  10. ENGINEER GETS ANSWER                            │
│  Root cause + fix + blast radius + evidence          │
│  (All in <60 seconds)                                │
└───────────────────────────────────────────────────────┘

TOTAL TIME: ~60 seconds
  Setup & serialization: 10ms
  Agent execution (parallel): 200ms
  Claude API call: 800ms
  Formatting: 50ms
  Total: 1060ms ≈ 1 second
```

---

## Why We Need Memory (Conversation History)

You asked: **"Is memory just for searching faster, or do we retain it locally?"**

### The Answer: Both + More

#### 1. **Conversation Memory** (What We Retain Locally)

When engineer asks follow-up questions:

```
Turn 1:
  Engineer: "ROUTER-LAB-01 is dropping packets. What's the issue?"
  System: [Analysis from step above]
  Memory stored: {query, findings, root_cause, evidence}

Turn 2:
  Engineer: "How do I fix the BGP issue?"
  System: [Knows from memory: BGP is the cause]
           [Doesn't re-analyze, just focuses on fix]
  Memory: Add remediation steps to session

Turn 3:
  Engineer: "Has this happened before?"
  System: [Knows from memory: This is about ROUTER-LAB-01 + CPU spike]
           [Already searched: INC-2024-0228-003]
           [Just returns: Here's what fixed it last time]
  Memory: Add historical context to session
```

**Without memory:**
```
Turn 1: 1000ms (full analysis)
Turn 2: 1000ms (re-does Turn 1 analysis, then adds fix)
Turn 3: 1000ms (re-does everything again, then searches history)
Total: 3000ms
```

**With memory:**
```
Turn 1: 1000ms (full analysis, store in memory)
Turn 2: 100ms (use memory, just focus on fix)
Turn 3: 50ms (use memory, just retrieve historical match)
Total: 1150ms
```

#### 2. **Where Is Memory Stored?**

```python
# In LangGraph (the orchestrator)

conversation_memory = {
    "session_id": "engineer-john-03-26-2024",
    "timestamp_start": "08:16:00",

    "context": {
        "primary_device": "ROUTER-LAB-01",
        "symptoms": ["dropping packets", "BGP flapping"],
        "initial_query": "What's the root cause?"
    },

    "findings": {
        "root_cause": "Memory exhaustion",
        "confidence": 0.92,
        "evidence": [log_line_9, metric_row_14, ...],
        "affected_devices": ["D002", "D003", ...],
        "attack_verdict": "LEGITIMATE"
    },

    "turns": [
        {
            "turn": 1,
            "user_query": "ROUTER-LAB-01 is dropping packets",
            "system_response": "[full RCA]",
            "timestamp": "08:16:00"
        },
        {
            "turn": 2,
            "user_query": "How do I fix the BGP issue?",
            "system_response": "[remediation steps, using Turn 1 memory]",
            "timestamp": "08:16:15"
        }
    ]
}
```

**Storage location: LangGraph's MemorySaver**
```
Location: ~/.langraph/sessions/{session_id}
Or: In-memory (RAM) if not persistent
Duration: Until engineer exits the chat session
Cleared: When `network-guy chat` session ends
```

#### 3. **Why Memory Matters Beyond Speed**

**Scenario 1: Root Cause Context**
```
Turn 1: "ROUTER-LAB-01 is dropping packets"
        System: Root cause is memory exhaustion

Turn 2: "Why is that related to my 5G test failures?"
        System: [Uses memory] ROUTER-LAB-01 is primary gateway
                for NET-LAB-ALPHA. 5G tests route through it.
                Without it, all 5G data plane tests fail.
                [Doesn't re-query topology, uses memory]
```

**Scenario 2: Narrowing Down**
```
Turn 1: "Show me all critical events"
        System: Lists 4 CRITICAL events (too broad)

Turn 2: "Just the ones related to BGP"
        System: [Uses memory of Turn 1]
                Filters: Only show CRITICAL events affecting BGP
                (Routes flapping, BGP timeout, bgpd crash)
```

**Scenario 3: Comparing with History**
```
Turn 1: "This happened before, right?"
        System: [Searches incidents] INC-2024-0228-003 matches

Turn 2: "What was different last time?"
        System: [Uses memory] Last time, CPU hit 85%. This time 92%.
                Last time, recovery took 15 min. This time 8 min.
                [Analysis powered by memory comparison]
```

---

## Complete Data Flow Diagram (Detailed)

```
┌─────────────────────────────────────────────────────────────────┐
│  USER INPUT                                                     │
│  $ network-guy query "ROUTER-LAB-01 dropping packets"          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                    ┌────────────▼──────────┐
                    │  supervisor.py        │
                    │  - Parse query        │
                    │  - Extract devices    │
                    │  - Determine intent   │
                    └────────────┬──────────┘
                                 │
        ┌────────────┬───────────┼───────────┬────────────┐
        │            │           │           │            │
        ▼            ▼           ▼           ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐  ┌─────────┐  ┌──────────┐
    │Log Ast │  │Metrics │  │Topo    │  │Incident │  │Security  │
    │Agent   │  │Agent   │  │Agent   │  │Agent    │  │Agent     │
    └───┬────┘  └────┬───┘  └────┬───┘  └────┬────┘  └─────┬────┘
        │            │           │           │             │
        │            │           │           │             │
        │  ChromaDB  │  SQLite   │  NetworkX │  ChromaDB   │
        │  Query     │  Query    │  BFS      │  Query      │
        │            │           │           │  +Signature │
        │            │           │           │   Scan      │
        │            │           │           │  +Anomaly   │
        │            │           │           │   Check     │
        │            │           │           │             │
        ▼            ▼           ▼           ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │Event     │ │CPU 92%   │ │Blast R.  │ │Match 91% │ │Not Attack│
    │Timeline  │ │Memory 95%│ │5 devices │ │INC-0228  │ │Conf 95%  │
    │CPU→BGP   │ │Drops4523 │ │12 paths  │ │BGP grace │ │Legit     │
    │at 08:15  │ │@08:15    │ │loss      │ │-restart  │ │failure   │
    └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
         │            │            │            │             │
         └────────────┼────────────┼────────────┼─────────────┘
                      │
          ┌───────────▼──────────────┐
          │ supervisor.py            │
          │ Collect all findings     │
          │ Build context dict       │
          └───────────┬──────────────┘
                      │
          ┌───────────▼──────────────┐
          │ Claude API call          │
          │ System prompt +          │
          │ All findings +           │
          │ Conversation history     │
          └───────────┬──────────────┘
                      │
          ┌───────────▼──────────────┐
          │ Claude LLM               │
          │ Synthesizes RCA          │
          │ (generates text)         │
          └───────────┬──────────────┘
                      │
          ┌───────────▼──────────────┐
          │ cli.py                   │
          │ Format with Rich         │
          │ Add colors, tables       │
          │ Pretty output            │
          └───────────┬──────────────┘
                      │
          ┌───────────▼──────────────┐
          │ Engineer sees:           │
          │ ✓ Root cause             │
          │ ✓ Evidence citations     │
          │ ✓ Remediation steps      │
          │ ✓ Blast radius           │
          │ ✓ Historical match       │
          │ ✓ Security verdict       │
          │ (all in <60 seconds)     │
          └──────────────────────────┘


MEMORY STORAGE (Optional, for multi-turn):
┌─────────────────────────────────────────┐
│ LangGraph MemorySaver                   │
│                                         │
│ session_0001 = {                        │
│   "device": "ROUTER-LAB-01",            │
│   "root_cause": "Memory exhaustion",    │
│   "previous_queries": [...],            │
│   "findings": {...},                    │
│   "created_at": "2024-03-26 08:16"      │
│ }                                       │
│                                         │
│ Location: ~/.langraph/                  │
│ Lifetime: Session length (or persistent)│
└─────────────────────────────────────────┘
```

---

## Summary: What Happens When You Type A Query

```
1. YOU TYPE:    "ROUTER-LAB-01 is dropping packets"
                (1 second to type)

2. SYSTEM PARSES:
                Devices: [D001]
                Symptoms: [packet_loss, bgp_drop]
                Intent: root_cause_analysis

3. SYSTEM ROUTES:
                "I need 5 agents: Log, Metrics, Topo, Incident, Security"

4. AGENTS RUN IN PARALLEL (200ms total):
                Log Agent:       Searches syslog, finds timeline
                Metrics Agent:   Queries CPU/memory, finds peaks
                Topo Agent:      BFS graph, finds impact
                Incident Agent:  Searches past incidents, finds match
                Security Agent:  Scans signatures, rules out attack

5. SUPERVISOR COLLECTS:
                All 5 findings → single context dict

6. CLAUDE SYNTHESIZES (800ms):
                "Based on all this data, the root cause is X because Y and Z"

7. CLI FORMATS (50ms):
                Pretty tables, colors, evidence citations

8. YOU READ:    Root cause + evidence + fix + impact
                (30 seconds to read and understand)

TOTAL TIME:     ~1 second system + 30 seconds engineer = 31 seconds
EFFICIENCY:     25x faster than manual troubleshooting (25 min → 1 min)
ACCURACY:       5 data sources correlated → 90%+ confidence
GROUNDING:      Every claim cites exact source (log line, metric, topology)
```

---

## Memory: Why It's Essential (Real Example)

```
❌ WITHOUT MEMORY:
  Turn 1 (08:16):
    Q: "Why is ROUTER-LAB-01 dropping packets?"
    System: Analyzes all data → CPU spike + memory exhaustion
    A: Root cause is memory exhaustion
    Time: 1000ms

  Turn 2 (08:17):
    Q: "How do I fix this?"
    System: [RE-ANALYZES everything from scratch]
            Then looks up fixes for memory exhaustion
    A: Apply BGP graceful-restart
    Time: 1000ms

  Turn 3 (08:18):
    Q: "Is this the same issue as last month?"
    System: [RE-ANALYZES everything again]
            Then searches past incidents
    A: Yes, INC-2024-0228-003 had same symptoms
    Time: 1000ms

  TOTAL: 3000ms + engineer frustration (why is it slow again?)

✅ WITH MEMORY:
  Turn 1 (08:16):
    Q: "Why is ROUTER-LAB-01 dropping packets?"
    System: Analyzes, stores findings in memory
    A: Root cause is memory exhaustion
    Memory: {root_cause, findings, affected_devices, ...}
    Time: 1000ms

  Turn 2 (08:17):
    Q: "How do I fix this?"
    System: [Uses memory] "I already know the root cause.
             Just generate fix steps for memory exhaustion."
    A: Apply BGP graceful-restart
    Time: 100ms

  Turn 3 (08:18):
    Q: "Is this the same issue as last month?"
    System: [Uses memory] "I already know it's memory exhaustion.
             Just search for similar past incidents."
    A: Yes, INC-2024-0228-003 had same symptoms
    Time: 50ms

  TOTAL: 1150ms + engineer happy (instant responses!)
```

---

## Key Takeaways

1. **Data Flow**: User query → Supervisor → 5 agents (parallel) → Collect → Claude → Format → Display

2. **Parallel Execution**: All 5 agents run simultaneously, not sequentially. This saves ~3x time.

3. **Agent Specialization**: Each agent is an expert in one type of query (logs, metrics, topology, history, security).

4. **Memory Purpose**:
   - ✅ Makes multi-turn conversation fast (100ms vs 1000ms)
   - ✅ Provides context for follow-up questions
   - ✅ Enables comparative analysis ("compare to last month")
   - ✅ NOT just for search speed, but for full conversation context

5. **Storage**: LangGraph's MemorySaver (local file or in-memory)

6. **Total Latency**: ~1 second system + 30 seconds engineer to read = 31 seconds total (25x faster than manual)

---

Ready to build this?
