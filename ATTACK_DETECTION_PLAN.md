# Attack Detection Implementation Plan

## The Core Idea

Add a **Security Agent** to the existing multi-agent system that can answer:
- "Is someone attacking the network?"
- "Is this failure caused by an attack or a legitimate issue?"
- "Show me suspicious activity in the last hour"

The agent uses **the same data sources** (logs, metrics, topology) but looks at them through a security lens.

---

## What Can We Detect vs. What We Can't

### Reality Check: What Our Data Sources Can See

```
Data Source          │ Can Detect                           │ Cannot Detect
─────────────────────┼──────────────────────────────────────┼──────────────────────
router_syslog.log    │ Auth failures, config changes,       │ Encrypted payload
                     │ process crashes, interface flaps     │ content, zero-days
                     │                                      │
snmp_metrics.csv     │ Traffic volume spikes, CPU/mem       │ Application-layer
                     │ anomalies, bandwidth saturation      │ attacks (SQL injection)
                     │                                      │
network_topology.json│ Unauthorized new devices,            │ Passive eavesdropping
                     │ unexpected path changes              │
                     │                                      │
device_inventory.csv │ Rogue devices, version               │ Firmware-level
                     │ vulnerabilities, status changes      │ compromises
                     │                                      │
incident_tickets.json│ Past security incidents,             │ Novel attack patterns
                     │ known attack signatures              │
```

### What We Need to Add (Synthetic Data for Hackathon)

Our current syslog only has operational events. Real routers also log security events. We need to **extend the sample data** with security-relevant log lines.

---

## New Data: Security Event Logs

### File: `data/security_events.log`

We'll create this synthetic file to simulate security-relevant events:

```log
# Authentication attacks
2024-03-15T08:05:12Z [WARN]  ROUTER-LAB-01 | SSH login failed | User: admin | Source: 10.99.1.15 | Attempt: 1
2024-03-15T08:05:13Z [WARN]  ROUTER-LAB-01 | SSH login failed | User: admin | Source: 10.99.1.15 | Attempt: 2
2024-03-15T08:05:14Z [WARN]  ROUTER-LAB-01 | SSH login failed | User: root  | Source: 10.99.1.15 | Attempt: 3
... (50 more in 60 seconds = brute force)
2024-03-15T08:06:15Z [CRIT]  ROUTER-LAB-01 | Brute force threshold exceeded | Source: 10.99.1.15 | Attempts: 53/min

# Port scanning
2024-03-15T08:07:00Z [WARN]  FIREWALL-01 | Connection attempt | Source: 10.99.1.15 | Dest: 10.0.0.1:22
2024-03-15T08:07:00Z [WARN]  FIREWALL-01 | Connection attempt | Source: 10.99.1.15 | Dest: 10.0.0.1:23
2024-03-15T08:07:01Z [WARN]  FIREWALL-01 | Connection attempt | Source: 10.99.1.15 | Dest: 10.0.0.1:80
2024-03-15T08:07:01Z [WARN]  FIREWALL-01 | Connection attempt | Source: 10.99.1.15 | Dest: 10.0.0.1:443
... (scanning 100+ ports in 10 seconds)
2024-03-15T08:07:10Z [CRIT]  FIREWALL-01 | Port scan detected | Source: 10.99.1.15 | Ports scanned: 127

# DDoS / Traffic flood
2024-03-15T08:09:00Z [WARN]  ROUTER-LAB-01 | Unusual traffic spike | Inbound: 850Mbps | Normal: 250Mbps
2024-03-15T08:09:30Z [WARN]  ROUTER-LAB-01 | SYN flood detected | Source: 10.99.0.0/16 | Rate: 15000 SYN/sec
2024-03-15T08:10:00Z [CRIT]  ROUTER-LAB-01 | Interface GE0/0 saturated | Utilization: 97%

# BGP hijack attempt
2024-03-15T08:11:00Z [WARN]  ROUTER-LAB-01 | BGP UPDATE received | Peer: 192.168.100.1 | Prefix: 10.0.0.0/8
2024-03-15T08:11:00Z [WARN]  ROUTER-LAB-01 | BGP route origin mismatch | Expected AS: 65001 | Received AS: 65999
2024-03-15T08:11:01Z [CRIT]  ROUTER-LAB-01 | Possible BGP hijack | Prefix: 10.0.0.0/8 | Rogue AS: 65999

# ARP spoofing
2024-03-15T08:12:00Z [WARN]  SW-LAB-01 | Gratuitous ARP received | IP: 10.0.0.1 | New MAC: aa:bb:cc:dd:ee:ff
2024-03-15T08:12:00Z [WARN]  SW-LAB-01 | MAC address conflict | IP: 10.0.0.1 | Old MAC: 00:1a:2b:3c:4d:5e | New MAC: aa:bb:cc:dd:ee:ff
2024-03-15T08:12:01Z [CRIT]  SW-LAB-01 | ARP spoofing detected | Attacker MAC: aa:bb:cc:dd:ee:ff

# Unauthorized config change
2024-03-15T08:13:00Z [WARN]  ROUTER-LAB-01 | Config change detected | User: unknown_user | Source: 10.99.1.15
2024-03-15T08:13:01Z [CRIT]  ROUTER-LAB-01 | ACL modified | ACL: MGMT-ACCESS | Action: permit any any added
2024-03-15T08:13:02Z [CRIT]  ROUTER-LAB-01 | SNMP community string changed | Old: [REDACTED] | New: public

# Rogue device
2024-03-15T08:14:00Z [WARN]  SW-LAB-01 | New device detected on port GE0/45 | MAC: ff:ee:dd:cc:bb:aa
2024-03-15T08:14:00Z [WARN]  SW-LAB-01 | Device not in inventory | MAC: ff:ee:dd:cc:bb:aa | IP: 10.0.0.99
2024-03-15T08:14:01Z [WARN]  SW-LAB-01 | DHCP snooping violation | Port: GE0/45 | Unauthorized DHCP server
```

### File: `data/traffic_flows.csv`

NetFlow/sFlow data for traffic analysis:

```csv
timestamp,src_ip,dst_ip,src_port,dst_port,protocol,bytes,packets,flags,duration_sec
2024-03-15T08:05:00Z,10.99.1.15,10.0.0.1,54321,22,TCP,4200,53,SYN,60
2024-03-15T08:07:00Z,10.99.1.15,10.0.0.1,54322,1-1024,TCP,12700,127,SYN,10
2024-03-15T08:09:00Z,10.99.0.1,10.0.0.1,0,0,UDP,950000000,750000,---,60
2024-03-15T08:09:00Z,10.99.0.2,10.0.0.1,0,0,UDP,870000000,690000,---,60
2024-03-15T08:09:00Z,10.99.0.3,10.0.0.1,0,0,UDP,920000000,720000,---,60
```

---

## Attack Types We'll Detect

### 7 Attack Categories

```
#  Attack Type              Detection Method           Data Source         Confidence
─  ──────────────────────── ────────────────────────── ─────────────────── ──────────
1  Brute Force (SSH/Telnet) Signature: failed login    security_events.log High (95%)
                            count > threshold/min

2  Port Scanning            Signature: connection      security_events.log High (90%)
                            attempts to many ports     traffic_flows.csv
                            from single IP

3  DDoS / Traffic Flood     Anomaly: bandwidth spike   snmp_metrics.csv    High (85%)
                            + packet rate anomaly      security_events.log
                            + SYN flood signature      traffic_flows.csv

4  BGP Hijack               Signature: unexpected AS   security_events.log High (92%)
                            in BGP update + route      network_topology
                            origin mismatch

5  ARP Spoofing / MITM      Signature: MAC conflict    security_events.log High (88%)
                            + gratuitous ARP from      device_inventory
                            unknown MAC

6  Unauthorized Access       Signature: config change   security_events.log Medium (75%)
                            from unknown user/IP +
                            ACL/SNMP modifications

7  Rogue Device             Anomaly: new MAC not in    security_events.log High (90%)
                            device_inventory + DHCP    device_inventory
                            snooping violation
```

---

## Architecture: How It Fits Into Existing System

```
┌──────────────────────────────────────────────────────────┐
│                   Engineer Query                         │
│  "Is someone attacking the network?"                     │
│  "Why is CPU spiked — is this a DDoS?"                  │
│  "Show suspicious activity in the last hour"             │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│              LangGraph Supervisor                         │
│                                                          │
│  Decides: Is this a security query or operational query? │
│                                                          │
│  Keywords that trigger Security Agent:                   │
│    attack, hack, suspicious, intrusion, unauthorized,    │
│    brute force, DDoS, scan, spoof, hijack, rogue,       │
│    security, threat, compromise, breach                  │
│                                                          │
│  OR: If operational analysis finds anomalies that        │
│      don't match normal failure patterns → auto-trigger  │
└──┬────────┬────────┬────────┬────────┬───────────────────┘
   │        │        │        │        │
   │   ┌────▼──┐ ┌───▼───┐ ┌─▼──┐ ┌──▼──────────────┐
   │   │ Log   │ │Metrics│ │Topo│ │ SECURITY AGENT  │ ← NEW
   │   │Analyst│ │Agent  │ │    │ │ (attack detect) │
   │   └───────┘ └───────┘ └────┘ └──┬──────────────┘
   │                                   │
   │              ┌────────────────────┘
   │              │
   │   ┌──────────▼──────────────────────────────────┐
   │   │         Security Analysis Pipeline          │
   │   │                                             │
   │   │  Step 1: Signature Scan                     │
   │   │    → Match known attack patterns in logs    │
   │   │                                             │
   │   │  Step 2: Anomaly Detection                  │
   │   │    → Compare metrics against baseline       │
   │   │    → Flag statistical outliers              │
   │   │                                             │
   │   │  Step 3: Topology Validation                │
   │   │    → Check for unknown devices              │
   │   │    → Verify BGP route origins               │
   │   │    → Detect path changes                    │
   │   │                                             │
   │   │  Step 4: Correlation                        │
   │   │    → Cross-reference findings across        │
   │   │      all data sources                       │
   │   │    → Build attack timeline                  │
   │   │    → Calculate confidence score             │
   │   │                                             │
   │   │  Step 5: Threat Classification              │
   │   │    → Classify attack type                   │
   │   │    → Assess severity (P1-P4)                │
   │   │    → Determine blast radius                 │
   │   │    → Generate containment steps             │
   │   └─────────────────────────────────────────────┘
   │
   └──→ Synthesize: Normal RCA + Security Assessment
```

---

## Component Design

### 1. Security Event Parser (`agents/security/parser.py`)

Parses `security_events.log` into structured events:

```python
@dataclass
class SecurityEvent:
    timestamp: datetime
    severity: str          # WARN, CRIT
    device: str            # ROUTER-LAB-01
    event_type: str        # AUTH_FAILURE, PORT_SCAN, SYN_FLOOD, etc.
    source_ip: str         # Attacker IP
    target_ip: str         # Victim IP
    details: dict          # Event-specific metadata
    raw_line: str          # Original log line (for citation)
    line_number: int       # For evidence grounding

# Event type enum
class SecurityEventType(Enum):
    AUTH_FAILURE = "auth_failure"
    BRUTE_FORCE = "brute_force"
    PORT_SCAN = "port_scan"
    SYN_FLOOD = "syn_flood"
    TRAFFIC_SPIKE = "traffic_spike"
    BGP_HIJACK = "bgp_hijack"
    ARP_SPOOF = "arp_spoof"
    CONFIG_CHANGE = "config_change"
    ROGUE_DEVICE = "rogue_device"
    DHCP_VIOLATION = "dhcp_violation"
```

### 2. Signature Engine (`agents/security/signatures.py`)

Pattern matching against known attack signatures:

```python
ATTACK_SIGNATURES = {
    "brute_force": {
        "patterns": [
            r"SSH login failed.*Attempt: (\d+)",
            r"Brute force threshold exceeded",
            r"Authentication failure.*(\d+) attempts"
        ],
        "threshold": {
            "count": 10,          # 10+ failures
            "window_seconds": 60  # within 60 seconds
        },
        "severity": "HIGH",
        "confidence": 0.95
    },

    "port_scan": {
        "patterns": [
            r"Port scan detected.*Ports scanned: (\d+)",
            r"Connection attempt.*Dest:.*:(\d+)"
        ],
        "threshold": {
            "unique_ports": 20,    # 20+ different ports
            "window_seconds": 30   # within 30 seconds
        },
        "severity": "MEDIUM",
        "confidence": 0.90
    },

    "ddos_flood": {
        "patterns": [
            r"SYN flood detected.*Rate: (\d+)",
            r"Interface.*saturated.*Utilization: (\d+)%",
            r"Unusual traffic spike.*Inbound: (\d+)"
        ],
        "metric_correlation": {
            "cpu_utilization": "> 85%",
            "packet_drops_per_sec": "> 1000",
            "interface_in_bps": "> 90% of bandwidth"
        },
        "severity": "CRITICAL",
        "confidence": 0.85
    },

    "bgp_hijack": {
        "patterns": [
            r"BGP route origin mismatch.*Received AS: (\d+)",
            r"Possible BGP hijack.*Rogue AS: (\d+)"
        ],
        "topology_check": "verify AS in known_peers",
        "severity": "CRITICAL",
        "confidence": 0.92
    },

    "arp_spoof": {
        "patterns": [
            r"ARP spoofing detected",
            r"MAC address conflict.*New MAC: ([0-9a-f:]+)",
            r"Gratuitous ARP.*New MAC: ([0-9a-f:]+)"
        ],
        "inventory_check": "verify MAC in device_inventory",
        "severity": "HIGH",
        "confidence": 0.88
    },

    "unauthorized_access": {
        "patterns": [
            r"Config change.*User: (\w+).*Source: ([\d.]+)",
            r"ACL modified.*permit any any",
            r"SNMP community string changed"
        ],
        "inventory_check": "verify source IP is management network",
        "severity": "CRITICAL",
        "confidence": 0.75
    },

    "rogue_device": {
        "patterns": [
            r"Device not in inventory.*MAC: ([0-9a-f:]+)",
            r"DHCP snooping violation",
            r"New device detected.*MAC: ([0-9a-f:]+)"
        ],
        "inventory_check": "MAC not in device_inventory",
        "severity": "HIGH",
        "confidence": 0.90
    }
}
```

### 3. Anomaly Detector (`agents/security/anomaly.py`)

Statistical anomaly detection on metrics:

```python
class AnomalyDetector:
    """
    Compares current metrics against a rolling baseline.
    Flags anything > N standard deviations from normal.
    """

    def detect_metric_anomalies(self, device_id, time_range):
        """
        For each metric:
        1. Calculate baseline (mean + stddev from historical data)
        2. Compare current values
        3. Flag if current > mean + 3*stddev (99.7% confidence)
        """
        # Example for ROUTER-LAB-01 CPU:
        # Baseline: mean=45%, stddev=10%
        # Current: 92%
        # Z-score: (92-45)/10 = 4.7 → way above 3σ → ANOMALY
        pass

    def detect_traffic_anomalies(self, flows):
        """
        Flag unusual traffic patterns:
        - Single source sending to many destinations (scan)
        - Many sources sending to single destination (DDoS)
        - Sudden bandwidth spike (flood)
        - Unusual protocol distribution
        """
        pass

    def detect_behavioral_anomalies(self, events):
        """
        Flag unusual behavior patterns:
        - Login attempts at unusual hours
        - Config changes from new IPs
        - New devices appearing
        - Routing changes without maintenance window
        """
        pass
```

### 4. Threat Correlator (`agents/security/correlator.py`)

Cross-references findings to build a complete attack picture:

```python
class ThreatCorrelator:
    """
    Takes individual findings from signature + anomaly engines
    and correlates them into a coherent attack narrative.
    """

    def correlate(self, signature_hits, anomalies, topology_changes):
        """
        Example correlation:

        Input findings:
          - Signature: Brute force from 10.99.1.15 at 08:05
          - Signature: Port scan from 10.99.1.15 at 08:07
          - Anomaly: Traffic spike at 08:09
          - Signature: SYN flood from 10.99.0.0/16 at 08:09
          - Anomaly: CPU spike to 92% at 08:15

        Correlated output:
          Attack Chain:
            1. Reconnaissance (08:05-08:07): Attacker at 10.99.1.15
               scanned ports and attempted brute force SSH login
            2. Amplification (08:09): Botnet activated from 10.99.0.0/16
               subnet, launching SYN flood at 15,000 SYN/sec
            3. Impact (08:10-08:15): DDoS caused CPU exhaustion (92%),
               memory pressure (95%), leading to BGP timeout and
               packet loss (4523 pps)

          Verdict: The CPU spike and BGP drop were CAUSED BY a DDoS attack,
                   not by normal operational failure.

          Confidence: 87%
        """
        pass
```

### 5. Security Agent (`agents/security_agent.py`)

The main agent that ties everything together:

```python
class SecurityAgent:
    """
    Called by Supervisor when:
    1. User explicitly asks about attacks/security
    2. Operational analysis finds anomalies that don't match
       normal failure patterns
    """

    def __init__(self):
        self.parser = SecurityEventParser()
        self.signature_engine = SignatureEngine()
        self.anomaly_detector = AnomalyDetector()
        self.correlator = ThreatCorrelator()

    def analyze(self, query, time_range, devices):
        """
        Full security analysis pipeline:

        1. Parse security events
        2. Run signature matching
        3. Run anomaly detection on metrics
        4. Cross-reference with topology (unknown devices? route changes?)
        5. Correlate all findings
        6. Classify threat type + severity
        7. Generate containment recommendations
        """

        # Step 1: Parse events
        events = self.parser.parse("data/security_events.log")

        # Step 2: Signature scan
        signature_hits = self.signature_engine.scan(events)

        # Step 3: Anomaly detection
        anomalies = self.anomaly_detector.detect_metric_anomalies(
            device_id=devices, time_range=time_range
        )

        # Step 4: Topology validation
        topo_issues = self.validate_topology(events)

        # Step 5: Correlate
        attack_chain = self.correlator.correlate(
            signature_hits, anomalies, topo_issues
        )

        # Step 6: Classify
        threat = self.classify_threat(attack_chain)

        # Step 7: Containment
        response = self.generate_response(threat)

        return SecurityReport(
            is_attack=threat.is_attack,
            attack_type=threat.type,
            confidence=threat.confidence,
            severity=threat.severity,
            attack_chain=attack_chain,
            evidence=threat.evidence,
            affected_devices=threat.blast_radius,
            containment_steps=response.containment,
            long_term_fixes=response.hardening
        )
```

---

## Output Format

### Example: DDoS Detection Response

```
┌─ SECURITY ALERT ─────────────────────────────────────────────┐
│                                                               │
│  Verdict: ATTACK DETECTED — DDoS / SYN Flood                │
│  Confidence: 87%                                              │
│  Severity: P1 (CRITICAL)                                      │
│                                                               │
├─ Attack Chain ────────────────────────────────────────────────┤
│                                                               │
│  Phase 1: Reconnaissance (08:05-08:07)                        │
│    • Brute force SSH from 10.99.1.15 (53 attempts/min)       │
│      Evidence: security_events.log lines 1-53                 │
│    • Port scan from 10.99.1.15 (127 ports in 10 sec)        │
│      Evidence: security_events.log lines 54-60                │
│                                                               │
│  Phase 2: Attack Launch (08:09)                               │
│    • SYN flood from 10.99.0.0/16 (15,000 SYN/sec)          │
│      Evidence: security_events.log line 65                    │
│    • Bandwidth saturated to 97%                               │
│      Evidence: snmp_metrics.csv row 12 (820M bps)            │
│                                                               │
│  Phase 3: Impact (08:10-08:17)                                │
│    • CPU spiked: 45% → 92% (CRITICAL)                        │
│      Evidence: snmp_metrics.csv rows 10,14                    │
│    • BGP peer 10.0.0.3 dropped (hold timer expired)          │
│      Evidence: router_syslog.log line 9                       │
│    • Packet loss: 4,523 pps                                   │
│      Evidence: snmp_metrics.csv row 16                        │
│    • bgpd process crashed                                     │
│      Evidence: router_syslog.log line 14                      │
│                                                               │
├─ Affected Devices ────────────────────────────────────────────┤
│                                                               │
│  Primary target: ROUTER-LAB-01                                │
│  Blast radius:                                                │
│    • ROUTER-LAB-02 (lost BGP peer)                           │
│    • SW-LAB-01 (trunk link degraded)                         │
│    • FIREWALL-01, LB-LAB-01 (downstream impact)             │
│    • DNS-SERVER-01 (management link affected)                │
│                                                               │
├─ IMMEDIATE CONTAINMENT ──────────────────────────────────────┤
│                                                               │
│  1. Block attacker IP at perimeter firewall:                  │
│     FIREWALL-01> set security policy deny-source 10.99.1.15  │
│                                                               │
│  2. Block DDoS subnet:                                        │
│     FIREWALL-01> set security policy deny-source 10.99.0.0/16│
│                                                               │
│  3. Enable rate-limiting on ROUTER-LAB-01 GE0/0:            │
│     ROUTER-LAB-01> rate-limit input 500000000                │
│                                                               │
│  4. Enable SYN cookies (mitigate SYN flood):                 │
│     ROUTER-LAB-01> ip tcp synwait-time 10                    │
│                                                               │
│  5. Isolate affected interface if attack continues:           │
│     ROUTER-LAB-01> interface GE0/0                           │
│     ROUTER-LAB-01> shutdown                                  │
│                                                               │
├─ LONG-TERM HARDENING ────────────────────────────────────────┤
│                                                               │
│  1. Deploy rate-limiting on all edge interfaces               │
│  2. Enable uRPF (Unicast Reverse Path Forwarding)            │
│  3. Configure BGP graceful-restart (prevents session drops)   │
│  4. Set up SSH key-only auth (prevents brute force)           │
│  5. Enable NetFlow/sFlow for continuous traffic analysis      │
│  6. Configure CoPP (Control Plane Policing) on routers       │
│  7. Add fail2ban equivalent for network device SSH            │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Key Design Decision: Attack vs. Legitimate Failure

The hardest problem is distinguishing between:
- **Legitimate failure**: CPU spikes because of a memory leak or traffic burst
- **Attack-caused failure**: CPU spikes because of a DDoS flood

### Decision Matrix

```
Indicator                    │ Legit Failure │ Attack
─────────────────────────────┼───────────────┼─────────
CPU spike                    │ ✓             │ ✓
Traffic from known devices   │ ✓             │ ✗
Traffic from unknown IPs     │ ✗             │ ✓
Preceded by auth failures    │ ✗             │ ✓
Preceded by port scan        │ ✗             │ ✓
Gradual metric degradation   │ ✓             │ ✗
Sudden metric spike          │ Possible      │ ✓
SYN/UDP flood signature      │ ✗             │ ✓
Config changes from unknown  │ ✗             │ ✓
New unknown devices          │ Rare          │ ✓
Recovery after source block  │ N/A           │ ✓
```

The Security Agent scores each indicator and produces:
```python
verdict = {
    "classification": "ATTACK" | "LEGITIMATE_FAILURE" | "INCONCLUSIVE",
    "confidence": 0.87,
    "reasoning": "Traffic spike originated from unknown subnet 10.99.0.0/16, "
                 "preceded by reconnaissance (brute force + port scan) from "
                 "10.99.1.15. Pattern matches DDoS attack chain."
}
```

---

## Project Structure (New Files)

```
src/network_guy/
├── agents/
│   ├── log_analyst.py          # Existing
│   ├── metrics.py              # Existing
│   ├── topology.py             # Existing
│   ├── incident.py             # Existing
│   └── security/               # NEW
│       ├── __init__.py
│       ├── security_agent.py   # Main security agent
│       ├── parser.py           # Parse security event logs
│       ├── signatures.py       # Known attack pattern matching
│       ├── anomaly.py          # Statistical anomaly detection
│       └── correlator.py       # Cross-reference and build attack chain

data/
├── router_syslog.log           # Existing
├── device_inventory.csv        # Existing
├── network_topology.json       # Existing
├── snmp_metrics.csv            # Existing
├── incident_tickets.json       # Existing
├── security_events.log         # NEW — security-specific log events
└── traffic_flows.csv           # NEW — NetFlow/sFlow traffic data
```

---

## Implementation Phases

### Phase A: Data Preparation (2-3 hours)
- [ ] Create `security_events.log` (synthetic security log data)
- [ ] Create `traffic_flows.csv` (synthetic NetFlow data)
- [ ] Add security event parser to data loader
- [ ] Embed security events into ChromaDB

### Phase B: Signature Engine (3-4 hours)
- [ ] Define 7 attack signature patterns (regex-based)
- [ ] Implement threshold-based detection (brute force: >10 failures/min)
- [ ] Implement multi-pattern correlation (scan + flood = DDoS chain)
- [ ] Unit test each signature against sample data

### Phase C: Anomaly Detection (2-3 hours)
- [ ] Implement baseline calculator (mean + stddev from historical metrics)
- [ ] Implement Z-score anomaly flagging (>3σ = anomaly)
- [ ] Implement traffic pattern analysis (single-source fan-out, multi-source convergence)
- [ ] Add behavioral anomaly detection (unusual time, unusual user)

### Phase D: Correlation + Agent (3-4 hours)
- [ ] Build threat correlator (timeline + multi-source cross-reference)
- [ ] Implement attack chain builder (reconnaissance → amplification → impact)
- [ ] Build attack-vs-legitimate classifier (decision matrix scoring)
- [ ] Implement containment recommendation generator
- [ ] Integrate into LangGraph supervisor

### Phase E: CLI + Testing (2-3 hours)
- [ ] Add `network-guy security-scan` CLI command
- [ ] Add security-related queries to benchmark tests
- [ ] Test: "Is this a DDoS?" → should detect flood
- [ ] Test: "Is this just a CPU issue?" → should classify as legitimate
- [ ] Test: "Who is attacking us?" → should identify source IPs

**Total effort: ~12-16 hours (1.5-2 days)**

---

## Security Benchmark Queries (Test Your System)

| # | Query | Expected Answer |
|---|-------|-----------------|
| 1 | "Is someone attacking the network?" | Yes — DDoS from 10.99.0.0/16, preceded by recon from 10.99.1.15 |
| 2 | "Is the CPU spike on ROUTER-LAB-01 caused by an attack?" | Yes — SYN flood caused CPU exhaustion (evidence: traffic spike at 08:09) |
| 3 | "Who is attacking us?" | Primary: 10.99.1.15 (recon), Botnet: 10.99.0.0/16 subnet |
| 4 | "How do I stop the attack?" | Block 10.99.1.15 and 10.99.0.0/16 at FIREWALL-01, enable rate-limiting |
| 5 | "Is the BGP drop attack-related or operational?" | Attack-related — BGP dropped because DDoS exhausted CPU past hold timer |
| 6 | "Are there any rogue devices on the network?" | Yes — unknown MAC ff:ee:dd:cc:bb:aa on SW-LAB-01 port GE0/45 |
| 7 | "Has anyone changed the router config without authorization?" | Yes — unknown_user from 10.99.1.15 modified ACL and SNMP community |
| 8 | "Show me the full attack timeline" | 08:05 recon → 08:07 scan → 08:09 flood → 08:10-08:17 impact → 08:19 partial recovery |

---

## How It Differentiates From Core RCA

| Aspect | Core RCA (Existing) | Security Agent (New) |
|--------|--------------------|--------------------|
| **Question** | "What broke?" | "Who broke it?" |
| **Data focus** | Operational logs + metrics | Security events + traffic flows |
| **Root cause** | Hardware/software/config failure | Malicious actor + attack vector |
| **Output** | Fix commands | Containment + hardening steps |
| **Timeline** | Event sequence | Attack chain (recon → exploit → impact) |
| **Blast radius** | Device dependencies | Attack surface + lateral movement |

---

## Summary

The Security Agent adds a **threat intelligence layer** on top of the existing troubleshooting system. Same architecture, same data pipeline, just a different analytical lens:

1. **Parse** security events (new log file)
2. **Match** against known attack signatures (regex patterns)
3. **Detect** statistical anomalies in metrics (Z-score)
4. **Correlate** across all sources to build attack chain
5. **Classify** as attack vs. legitimate failure
6. **Recommend** containment + long-term hardening

The key innovation is **Step 5**: the system doesn't just detect attacks — it tells you whether a failure was caused by an attack or was a normal operational issue. That's the real value for engineers.
