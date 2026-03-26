# Sample Data Analysis — Network Troubleshooting Dataset

## Overview

The provided dataset contains **5 real-world synthetic sample files** that simulate a telecom lab network experiencing multiple simultaneous failures on **2024-03-15 08:00-08:30**. This is your **test data** for the hackathon.

---

## 1. Device Inventory (`device_inventory.csv`)

### Purpose
Complete list of all network devices across 4 lab networks: NET-LAB-ALPHA, NET-LAB-BETA, NET-LAB-5G, NET-LAB-MGMT.

### Structure
15 devices with: Device ID, Name, Type, Vendor, Model, Software Version, IP, Location, Status, Uptime

### Key Insights

| Network | Device Count | Status Breakdown | Critical Notes |
|---------|--------------|-----------------|-----------------|
| **NET-LAB-ALPHA** | 9 devices | 7 UP, 1 DEGRADED, 1 UP | Primary production lab |
| **NET-LAB-BETA** | 2 devices | 1 UP, 1 DOWN | Testing network offline |
| **NET-LAB-5G** | 3 devices | 2 UP, 1 ERROR | 5G core lab in trouble |
| **NET-LAB-MGMT** | 1 device | 1 UP | Management server |

### Critical Issues Found

1. **ROUTER-LAB-01** (D001)
   - Status: **DEGRADED** (not UP)
   - Software: IOS-XE 17.6.1 (older version)
   - Last seen: 08:30:00Z, uptime only 72 hours
   - Implication: Recently rebooted, running older version than ROUTER-LAB-02 (17.9.3)

2. **SW-LAB-02** (D004)
   - Status: **DOWN**
   - Last seen: 07:15:00Z (last alive 1+ hour ago)
   - Implication: Hard failure, not just a connectivity issue

3. **LB-LAB-02** (D008)
   - Status: **DOWN**
   - Last seen: 06:45:00Z (offline for 1.75 hours)
   - Implication: Cascading failure from SW-LAB-02 (dependent on it)

4. **5G-UPF-01** (D011)
   - Status: **ERROR**
   - Last seen: 08:10:00Z (just started failing)
   - Uptime only 2 hours (very recent restart)
   - Implication: Post-upgrade crash (see incident tickets)

5. **Version Mismatch**
   - ROUTER-LAB-01: IOS-XE 17.6.1 (old)
   - ROUTER-LAB-02: IOS-XE 17.9.3 (new)
   - This version gap could cause BGP compatibility issues

---

## 2. Network Topology (`network_topology.json`)

### Purpose
Logical map of device connections, protocols, VLANs, and routing relationships in NET-LAB-ALPHA.

### Network Structure

```
┌─────────────────────────────────────────────────────────┐
│                   NET-LAB-ALPHA                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ROUTER-LAB-01 ←─ BGP_PEERING ──→ ROUTER-LAB-02       │
│     (Primary)      10G Link         (Secondary)        │
│       │              │                  │               │
│       │ TRUNK        │               TRUNK             │
│       │ 10G          │                10G               │
│       └──────┬───────┴──────────────┬─────┘            │
│              │                      │                   │
│          SW-LAB-01 (Distribution Switch)              │
│              │                                         │
│         ┌────┴────┬──────────────────┐               │
│         │          │                  │                │
│      ACCESS    SPAN             ACCESS                │
│       1G      10G                 1G                    │
│         │      │                   │                    │
│  FIREWALL-01  PACKET-BROKER-01  LB-LAB-01            │
│    (1G)       (Monitoring)        (1G)                │
│                                                        │
│   DNS-SERVER-01 (Management, 1G via GE0/0)           │
│                                                        │
└─────────────────────────────────────────────────────────┘

Routing Protocols Active:
  • BGP: Local AS 65001, with peer at 10.0.0.2 (iBGP) + external (eBGP)
  • OSPF: Area 0.0.0.0, participants: D001, D002, D003
  • MPLS: LDP enabled, 24 LSPs (Label Switched Paths)

VLANs:
  • VLAN 100 (MGMT): 10.0.0.0/24 → gateway 10.0.0.1
  • VLAN 200 (DATA): 10.1.0.0/24 → gateway 10.1.0.1
  • VLAN 300 (VOICE): 10.2.0.0/24 → gateway 10.2.0.1
  • VLAN 999 (OOB_MGMT): 192.168.1.0/24 → gateway 192.168.1.1
```

### Blast Radius Analysis

**If ROUTER-LAB-01 fails:**
- Direct impact: ROUTER-LAB-02 loses BGP peer, OSPF adjacency fails
- Cascade: SW-LAB-01 loses trunk connectivity (redundancy lost)
- Downstream: FIREWALL-01, LB-LAB-01, PACKET-BROKER-01 isolated
- Services: DNS/NTP (10.0.6.1) unreachable

**If SW-LAB-01 fails:**
- Direct impact: All distribution layer down
- Cascade: Everything below it unreachable
- Full network isolation

---

## 3. Router Syslog (`router_syslog.log`)

### Purpose
Raw log events from ROUTER-LAB-01 covering the incident window (08:00-08:30).

### Timeline Analysis

**Phase 1: Normal Boot (08:00-08:01)**
```
08:00:01 System boot initiated
08:00:45 GE0/0 UP (1Gbps)
08:01:10 GE0/1 UP (1Gbps)
08:01:30 BGP session established with 10.0.0.2
```

**Phase 2: Warning Signs (08:05-08:12)**
```
08:05:00 OSPF adjacency established
08:10:22 [WARN] CPU at 78% (threshold: 75%)
08:12:45 [WARN] Memory at 90% (1.8GB/2GB used)
```

**Phase 3: Critical Cascade (08:15)**
```
08:15:00 [ERROR] GE0/2 DOWN (link failure)
08:15:03 [ERROR] BGP peer 10.0.0.3 dropped (hold timer expiry)
08:15:10 [ERROR] OSPF neighbor 10.0.0.6 DEAD
08:15:45 [CRIT] Route table UNSTABLE: 12 routes flapping/30sec
08:16:00 [CRIT] SYSTEM OVERLOAD: 4523 packets/sec DROPPED
08:16:30 [ERROR] NTP sync lost
08:17:00 [CRIT] bgpd process CRASH (restart attempt 1/3)
```

**Phase 4: Recovery (08:18-08:30)**
```
08:18:00 [ERROR] MPLS label stack corruption on GE0/0
08:18:30 [CRIT] Memory allocation failure: OOM condition
08:19:00 [INFO] bgpd restarted successfully
08:19:30 [WARN] BGP convergence slow (342 prefixes pending)
08:20:00 [INFO] GE0/2 UP (auto-recovery)
08:22:00 [INFO] BGP peer re-established (342 prefixes)
08:30:00 [INFO] System stabilized
```

### Root Cause Indicators (From Logs)

1. **Memory exhaustion** → CPU spike → Process crash → Service disruption
2. **BGP hold timer expiry** → Session drop → Route flapping
3. **Interface failure + routing instability** → Packet drops spike
4. **NTP loss** → Time sync issues (timing-critical protocols break)

---

## 4. SNMP Metrics (`snmp_metrics.csv`)

### Purpose
Time-series performance data (CPU, memory, bandwidth, packet drops, BGP sessions) collected every 5 minutes.

### Data Timeline & Thresholds

| Timestamp | CPU | Mem | Pkt Drops | BGP Sessions | Interface | Status |
|-----------|-----|-----|-----------|--------------|-----------|--------|
| 08:00 | 45% (OK) | 60% (OK) | 0 (OK) | 3 (OK) | UP | ✅ Healthy |
| 08:05 | 58% (OK) | 72% (OK) | 0 (OK) | 3 (OK) | UP | ✅ OK |
| **08:10** | **78% (WARN)** | **88% (WARN)** | 0 (OK) | 3 (OK) | UP | ⚠️ Degraded |
| **08:15** | **92% (CRIT)** | **95% (CRIT)** | **4523 (CRIT)** | **2 (WARN)** | **DOWN** | 🔴 Critical |
| **08:20** | **82% (CRIT)** | 87% (WARN) | 210 (WARN) | 3 (OK) | UP | 🟡 Recovering |
| 08:25 | 65% (OK) | 78% (OK) | 12 (OK) | 3 (OK) | UP | ✅ OK |
| 08:30 | 48% (OK) | 71% (OK) | 0 (OK) | 3 (OK) | UP | ✅ Stable |

### Thresholds & Status

```
Metric                  | WARN Threshold | CRIT Threshold | Peak Value | Status
─────────────────────────┼────────────────┼────────────────┼────────────┼─────
cpu_utilization         | 75%            | 90%            | 92%        | 🔴
memory_utilization      | 80%            | 95%            | 95%        | 🔴
packet_drops_per_sec    | 100 pps        | 1000 pps       | 4523 pps   | 🔴
bgp_session_count       | >2             | >1             | 2 (peak)   | ⚠️
interface_GE02_status   | UP             | UP             | DOWN       | 🔴
interface_GE00_crc_err  | 100            | 500            | 1243       | 🔴
```

### Key Observations

1. **CPU spike**: 45% → 78% → 92% (100% degradation in 15 min)
2. **Memory pressure**: 60% → 88% → 95% (follows CPU spike)
3. **Packet drops**: 0 → 0 → 4523 pps (sudden massive spike)
4. **BGP sessions**: 3 active → 2 active (1 dropped during overload)
5. **CRC errors**: 1243 errors on GE0/0 (link quality degradation)

---

## 5. Incident Tickets (`incident_tickets.json`)

### Purpose
Historical incident records + current open issues. Shows 3 active incidents on 2024-03-15.

### Incident 1: P1 — ROUTER-LAB-01 Core Instability
```
Ticket ID: INC-2024-0315-001
Status: OPEN
Created: 08:16:00Z (auto-created by monitoring)
Severity: P1 (Critical)
MTTR Target: 30 minutes

Symptom Summary:
  "High CPU (78%), memory pressure, BGP drops, GE0/2 failure, 30% packet loss"

Alerts Triggered:
  • CPU_HIGH_THRESHOLD_BREACH (78%)
  • MEMORY_LOW_WARNING (88%)
  • INTERFACE_DOWN_GE02
  • BGP_SESSION_DROP
  • PACKET_LOSS_HIGH

Timeline:
  08:10 → CPU alert at 78%
  08:12 → Memory at 90%
  08:15 → GE0/2 down + BGP drop + OSPF neighbor dead
  08:16 → P1 auto-created
  08:17 → bgpd process crash
  08:19 → bgpd restart
  08:20 → GE0/2 auto-recovery
  08:22 → BGP re-established
  (System stabilized at 08:30)

Business Impact:
  "5G regression test suite blocked. Feature validation delayed."

Similar Past Incidents:
  • INC-2024-0228-003 ← Same symptoms, check resolution
  • INC-2024-0301-007 ← Related failure pattern
```

**Key Insight**: This is the **primary incident** in your dataset. All metrics and logs correlate to this event.

### Incident 2: P2 — SW-LAB-02 Hardware Failure
```
Ticket ID: INC-2024-0315-002
Status: OPEN
Created: 07:20:00Z
Severity: P2 (High)
MTTR Target: 60 minutes

Symptom Summary:
  "SW-LAB-02 completely unreachable. No lights on management port."

Affected Devices:
  • D004: SW-LAB-02 (primary failure)
  • D008: LB-LAB-02 (cascading failure — depends on SW-LAB-02)

Timeline:
  07:00 → Maintenance window ended
  07:15 → SW-LAB-02 stopped responding
  07:20 → P2 created by engineer
  07:45 → LB-LAB-02 also marked unreachable

Business Impact:
  "IPv6 feature testing on NET-LAB-BETA completely blocked."

Previous Similar: None (first-time failure)
```

**Key Insight**: **Hardware failure** (not software). Physical power/link loss likely.

### Incident 3: P1 — 5G UPF Pod Crash Loop
```
Ticket ID: INC-2024-0315-003
Status: IN_PROGRESS
Created: 08:11:00Z
Severity: P1 (Critical)
MTTR Target: 45 minutes
Assigned To: sarah.chen@telecom.com

Symptom Summary:
  "5G-UPF-01 in ERROR. Kubernetes pod in CrashLoopBackOff. All GTP tunnels down."

Root Cause Indicator:
  "Upgraded chart version yesterday: UPF v23.R1.0 → v23.R1.1"

Alerts:
  • K8S_POD_CRASHLOOP_UPF
  • GTP_TUNNEL_DOWN_ALL
  • 5G_DATAPLANE_FAILURE

Timeline:
  2024-03-14 18:00 → Helm chart upgrade
  2024-03-15 08:08 → Pod entered CrashLoopBackOff
  2024-03-15 08:11 → P1 created
  2024-03-15 08:20 → Assigned to Sarah Chen

Business Impact:
  "All 5G end-to-end data plane test cases blocked."

Similar Past: INC-2024-0210-002 ← Check this for rollback procedure
```

**Key Insight**: **Post-upgrade failure**. Likely a breaking change in the Helm chart.

---

## How to Use This Data for Hackathon

### Test Scenario 1: Primary Incident (INC-2024-0315-001)
**Engineer Query**: "ROUTER-LAB-01 is dropping packets and BGP is flapping. What's the root cause?"

**Expected Answer** (from combining all data sources):
- Logs show: CPU spike → memory pressure → process crash → BGP timeout
- Metrics show: CPU 45%→78%→92%, memory 60%→88%→95%, packet drops 0→4523 pps
- Topology: Device is core router; if it fails, all downstream nodes break
- Incidents: Similar to INC-2024-0228-003 (check for proven fix)

**Remediation Steps** (from incident history):
1. Reduce OSPF hello timer (prevent flapping)
2. Enable BGP graceful-restart
3. Add memory guards to prevent OOM
4. Monitor CPU recovery

---

### Test Scenario 2: Hardware Failure (INC-2024-0315-002)
**Engineer Query**: "SW-LAB-02 is down. What's the impact?"

**Expected Answer**:
- Status: Completely unreachable (not reachable via SNMP or SSH)
- Topology: Blast radius = LB-LAB-02, and all NET-LAB-BETA dependent devices
- Incidents: This is likely a power/physical link issue

**Remediation**:
1. Check physical cable connections
2. Power cycle the device
3. Check management interface connectivity

---

### Test Scenario 3: Post-Upgrade Crash (INC-2024-0315-003)
**Engineer Query**: "5G-UPF-01 pod keeps crashing. How do I fix it?"

**Expected Answer**:
- Root cause: Post-upgrade instability (chart v23.R1.0 → v23.R1.1)
- Evidence: Pod in CrashLoopBackOff, GTP tunnels all down
- Historical: INC-2024-0210-002 had similar symptoms

**Remediation**:
1. Rollback Helm chart to previous version
2. Validate GTP tunnel establishment
3. Re-run test suite

---

## Summary: What Each File Tells You

| File | Contains | Used For |
|------|----------|----------|
| **device_inventory.csv** | Device metadata (vendor, version, status) | Identifying version mismatches, determining MTTR impact |
| **network_topology.json** | Device connections, protocols, VLANs | Calculating blast radius, finding dependencies |
| **router_syslog.log** | Event logs (errors, warnings, state changes) | Identifying failure sequence, root cause timeline |
| **snmp_metrics.csv** | CPU, memory, bandwidth, packet drops | Detecting thresholds breaches, anomalies, trends |
| **incident_tickets.json** | Historical incidents + current open issues | Finding similar past incidents, known resolutions |

---

## Data Quality Notes

✅ **What's good about this data:**
- Realistic incident timeline (matches real telecom failures)
- Multi-device failure (tests blast radius logic)
- Mix of software (crash) + hardware (physical failure) issues
- Post-upgrade failure (common pattern)
- Clear cause-effect relationships (metrics correlate with logs)

⚠️ **What to watch for:**
- Timestamps are precise to the second (realistic SNMP polling)
- Multiple overlapping incidents (real-world complexity)
- Some devices have 0 uptime (recently restarted — consider in analysis)
- Version mismatches between similar devices (often overlooked cause)

---

## Benchmark Queries (Test Against This Data)

Your system should handle these 10 questions correctly:

1. ✅ "What happened to ROUTER-LAB-01 between 08:10 and 08:20?"
   - Answer: CPU spike → memory pressure → BGP timeout → packet drops → recovery

2. ✅ "Why did BGP session with peer 10.0.0.3 drop?"
   - Answer: Hold timer expired due to CPU overload (log line 9)

3. ✅ "Which devices in NET-LAB-ALPHA are in WARNING or CRITICAL state?"
   - Answer: ROUTER-LAB-01 (DEGRADED), metric peaks at 08:15

4. ✅ "If ROUTER-LAB-01 completely failed, which other devices are affected?"
   - Answer: ROUTER-LAB-02 (BGP peer), SW-LAB-01 (trunk link), downstream: FIREWALL-01, LB-LAB-01, DNS-SERVER-01

5. ✅ "What's the software version of ROUTER-LAB-01 vs ROUTER-LAB-02? Are they compatible?"
   - Answer: 17.6.1 vs 17.9.3 (version gap; could indicate compatibility issues)

6. ✅ "Has a CPU spike + BGP drop combo happened before?"
   - Answer: Yes — INC-2024-0228-003 (check resolution steps)

7. ✅ "What's the remediation for a Cisco BGP hold timer expiry?"
   - Answer: Increase hold timer value, enable graceful-restart, reduce process load

8. ✅ "Show all CRITICAL events from syslog in the incident window"
   - Answer: 4 CRITICAL events (lines 11-12, 14, 17-18)

9. ✅ "What is the blast radius if 5G-UPF-01 is down? Which tests are blocked?"
   - Answer: 5G data plane tests blocked, end-to-end validation halted

10. ✅ "Give me a summary of all open P1 incidents and their status"
    - Answer: INC-2024-0315-001 (OPEN, recovery in progress), INC-2024-0315-003 (IN_PROGRESS, assigned to Sarah)

---

## Ready to Build?

Copy these 5 files to your `data/` folder:
```bash
cp -r "/Users/shaz/Downloads/AI Powered Network Troubleshooting Assistant for Telecom Test Labs"/* \
      /Users/shaz/codenproject/network_guy/data/
```

Then start Phase 0-1: Build the data loaders to ingest these files!
