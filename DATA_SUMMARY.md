# 📊 Sample Data Summary — What You Have

## 5 Files in Your `data/` Folder

### 1. **device_inventory.csv** (1.9 KB)
**15 network devices** across 4 lab networks.

```
Core Routers:
  • ROUTER-LAB-01 (Cisco ASR 9000, IOS-XE 17.6.1) — DEGRADED ⚠️
  • ROUTER-LAB-02 (Cisco ASR 9000, IOS-XE 17.9.3) — UP ✅

Switches:
  • SW-LAB-01 (Juniper EX4300) — UP ✅
  • SW-LAB-02 (Juniper EX4300) — DOWN 🔴

Firewalls:
  • FIREWALL-01, FIREWALL-02 (Palo Alto PA-3260) — Both UP ✅

Load Balancers:
  • LB-LAB-01 (F5 BIG-IP) — UP ✅
  • LB-LAB-02 (F5 BIG-IP) — DOWN 🔴

5G Core:
  • 5G-AMF-01 (Nokia AirScale) — UP ✅
  • 5G-SMF-01 (Nokia AirScale) — UP ✅
  • 5G-UPF-01 (Nokia AirScale) — ERROR 🔴

Other:
  • Packet Broker, DNS/NTP Server, Management Server
```

**What it tells you**: Device roles, vendor types, software versions, health status.

---

### 2. **network_topology.json** (2.8 KB)
**Physical & logical connections** for NET-LAB-ALPHA.

```json
Nodes:
  ROUTER-LAB-01 (Primary Gateway)
    ↓ BGP_PEERING (10G) ↙ TRUNK (10G)
  ROUTER-LAB-02 (Secondary Gateway)

  Both routers → TRUNK (10G) → SW-LAB-01 (Distribution)
       ↓
       ├─ ACCESS (1G) → FIREWALL-01
       ├─ ACCESS (1G) → LB-LAB-01
       └─ SPAN (10G) → PACKET-BROKER-01 (monitoring)

  Routing Protocols:
    • BGP: AS 65001 (iBGP + eBGP)
    • OSPF: Area 0.0.0.0
    • MPLS: 24 LSPs active

  VLANs:
    • 100 (MGMT)
    • 200 (DATA)
    • 300 (VOICE)
    • 999 (Out-of-Band Management)
```

**What it tells you**: Which devices connect to what, redundancy paths, failure impact.

---

### 3. **router_syslog.log** (2.3 KB)
**23 log events** from ROUTER-LAB-01, covering the incident from 08:00-08:30.

```
Timeline:
  08:00-08:01 ← Boot + interfaces UP
  08:01-08:05 ← BGP & OSPF establish
  08:10-08:12 ← WARNING: CPU 78%, memory 88%
  08:15-08:17 ← CRITICAL: Interface DOWN, BGP drops, bgpd CRASH
  08:18-08:19 ← Recovery: bgpd restart, MPLS corruption detected
  08:20-08:22 ← Interface UP again, BGP re-established
  08:25-08:30 ← System stabilizes
```

**Events by severity**:
- 12 INFO (normal operations)
- 6 WARN (thresholds exceeded)
- 3 ERROR (failures)
- 2 CRIT (system overload)

**What it tells you**: Exact sequence of failure, timing correlations, state changes.

---

### 4. **snmp_metrics.csv** (3.0 KB)
**Time-series performance data** for multiple devices, 5-minute intervals.

```
ROUTER-LAB-01 (08:00-08:30):
  CPU:        45% → 58% → 78% (WARN) → 92% (CRIT) → 82% (CRIT) → 65% → 48%
  Memory:     60% → 72% → 88% (WARN) → 95% (CRIT) → 87% → 78% → 71%
  Bandwidth:  250M → 820M (WARN) → drops measured
  Packet Loss: 0 → 0 → 4523 pps (CRITICAL spike!) → 210 → 12 → 0
  BGP Sessions: 3 → 3 → 3 → 2 (one dropped!) → 3 → 3 → 3

ROUTER-LAB-02:
  CPU: Stable 22-24% (good redundancy, took over during incident)
  Memory: Stable 45%

SW-LAB-01:
  CPU: 12%, Memory: 35% (healthy)

SW-LAB-02:
  device_reachable = 0 (CRITICAL) — completely offline

5G-UPF-01:
  pod_restart_count = 7 (CRITICAL) — CrashLoopBackOff
  gtp_tunnel_count = 0 (CRITICAL) — no tunnels up
  upf_throughput = 0 Gbps (CRITICAL) — no data plane
```

**What it tells you**: Exact thresholds breached, correlation between metrics, anomaly detection.

---

### 5. **incident_tickets.json** (4.5 KB)
**3 open incidents** with root causes, timelines, business impact.

```
P1: INC-2024-0315-001 — ROUTER-LAB-01 CPU Spike + BGP Drop
    Status: OPEN
    MTTR Target: 30 minutes
    Root Cause: CPU/memory exhaustion → process crash → BGP timeout
    Similar Past: INC-2024-0228-003, INC-2024-0301-007
    Impact: 5G regression tests blocked

P2: INC-2024-0315-002 — SW-LAB-02 Hardware Down
    Status: OPEN
    MTTR Target: 60 minutes
    Root Cause: Physical failure (no lights on management port)
    Similar Past: None
    Impact: IPv6 testing blocked

P1: INC-2024-0315-003 — 5G-UPF-01 Pod CrashLoop
    Status: IN_PROGRESS (assigned to Sarah Chen)
    MTTR Target: 45 minutes
    Root Cause: Post-upgrade failure (chart v23.R1.0 → v23.R1.1)
    Similar Past: INC-2024-0210-002
    Impact: All 5G end-to-end tests blocked
```

**What it tells you**: Root cause knowledge base, proven remediation steps, patterns.

---

## The Story: What Happened on 2024-03-15

### Timeline

```
08:00-08:05 ← All systems healthy, lab running
08:10       ← CPU warning (78%)
08:12       ← Memory pressure (88%)
08:15       ← CRITICAL: Interface fails, BGP drops, packet loss spikes to 4523 pps
08:16       ← P1 incident auto-created
08:17       ← bgpd process crashes
08:18-08:19 ← Recovery: bgpd restarts, MPLS corruption detected
08:20       ← Interface auto-recovers
08:22       ← BGP re-establishes
08:25-08:30 ← System stabilizes (CPU back to 48%, packet drops near 0)

Parallel Issues:
  07:15 ← SW-LAB-02 goes offline (separate hardware failure)
  08:08 ← 5G-UPF-01 enters CrashLoop (post-upgrade issue)
```

### Cascading Failure Chain

```
Resource Exhaustion
    ↓ (high packet processing load)
CPU Spike (45% → 92%)
    ↓ (can't allocate memory)
Memory Pressure (60% → 95%)
    ↓ (bgpd process affected)
BGP Process Crash (hold timer expires)
    ↓ (routing destabilized)
Interface Flapping + Route Instability
    ↓ (packets queuing, dropping)
Packet Loss Spike (0 → 4523 pps)
    ↓ (system recovers)
Recovery Phase → Auto-restart → Stabilization
```

---

## 10 Benchmark Queries (Test Your System)

Your AI should answer these correctly:

| # | Query | Expected Answer | Data Source |
|---|-------|-----------------|-------------|
| 1 | "What happened to ROUTER-LAB-01 between 08:10-08:20?" | CPU spike → memory pressure → BGP timeout → recovery | Logs + Metrics |
| 2 | "Why did BGP session with 10.0.0.3 drop?" | Hold timer expired due to CPU overload | Syslog line 9 |
| 3 | "Which devices in NET-LAB-ALPHA are WARNING/CRITICAL?" | ROUTER-LAB-01 (peak at 08:15) | Metrics + Status |
| 4 | "If ROUTER-LAB-01 fails, what's the blast radius?" | ROUTER-LAB-02, SW-LAB-01, FIREWALL-01, LB-LAB-01, DNS | Topology graph |
| 5 | "Is ROUTER-LAB-01 same version as ROUTER-LAB-02?" | No: 17.6.1 vs 17.9.3 (gap could cause issues) | Inventory |
| 6 | "Has CPU spike + BGP drop happened before?" | Yes: INC-2024-0228-003 (check it) | Incidents |
| 7 | "How do I fix Cisco BGP hold timer expiry?" | Increase timers, enable graceful-restart, reduce load | Incident resolution |
| 8 | "Show all CRITICAL events from syslog" | 4 CRITICAL lines: route flap (11), packet loss (12), crash (14), memory OOM (17) | Syslog |
| 9 | "What's the blast radius if 5G-UPF-01 is down?" | 5G data plane tests blocked, end-to-end validation halted | Topology + Incidents |
| 10 | "Summary of all open P1 incidents" | INC-2024-0315-001 (CPU/BGP, recovery in progress) + INC-2024-0315-003 (UPF crash, assigned) | Incidents |

---

## Key Data Patterns

### Pattern 1: Resource Exhaustion Cascade
CPU ↑ → Memory ↑ → BGP crash → Interface flap → Packet loss

### Pattern 2: Version Mismatch Issues
ROUTER-LAB-01 (17.6.1) vs ROUTER-LAB-02 (17.9.3) — can cause protocol incompatibility

### Pattern 3: Post-Upgrade Instability
5G-UPF upgrade (v23.R1.0 → v23.R1.1) → CrashLoopBackOff within 14 hours

### Pattern 4: Hardware Failures
SW-LAB-02 (no management lights) → cascading impact on LB-LAB-02

### Pattern 5: Multi-Device Correlation
3 simultaneous incidents, but different root causes (resource, hardware, software)

---

## How Your System Uses This Data

```
Engineer Query
    ↓
┌─────────────────────────────────────────────────┐
│ 1. LOG ANALYST: Search syslog (timestamps)      │
│    Find: "BGP dropped at 08:15:03"              │
│                                                 │
│ 2. METRICS AGENT: Query metrics (thresholds)    │
│    Find: "CPU peaked 92% at 08:15"              │
│                                                 │
│ 3. TOPOLOGY AGENT: Blast radius (BFS)           │
│    Find: "If ROUTER-LAB-01 dies, these break"  │
│                                                 │
│ 4. INCIDENT AGENT: Historical correlation      │
│    Find: "Similar to INC-2024-0228-003"        │
└─────────────────────────────────────────────────┘
    ↓
SYNTHESIZE: "Root cause is CPU exhaustion.
  Evidence:
  • Syslog line 6: CPU 78% at 08:10:22
  • Metrics: CPU 92% (CRITICAL) at 08:15
  • Syslog line 9: BGP dropped at 08:15:03
  • Metrics: Packet drops 4523 pps at 08:15

  Fix:
  1. Restart BGP daemon
  2. Apply graceful-restart config
  3. Monitor CPU recovery

  Historical: INC-2024-0228-003 had same symptoms.
              Applied: memory guards + BGP timer tuning"
```

---

## Ready to Start Building?

You now have:
- ✅ 4 architecture documents (BRIEF, IMPLEMENTATION_PLAN, ANALYSIS, SAMPLE_DATA_ANALYSIS)
- ✅ Complete sample dataset (5 files)
- ✅ 10 benchmark queries to validate against
- ✅ GitHub repo initialized

**Next steps**:
1. Set up Poetry + dependencies
2. Build data loaders (Phase 0-1)
3. Build storage layer (Phase 1)
4. Build agents (Phase 2)
5. Build orchestrator (Phase 3)
6. CLI + testing (Phase 4)

Let's go! 🚀
