"""Supervisor Agent — orchestrates all 5 agents and synthesizes RCA via Claude.

Flow:
  1. Parse user query → extract devices, symptoms
  2. Run 5 agents (log, metrics, topology, incident, security)
  3. Collect all findings
  4. Send to Claude API with system prompt
  5. Return structured RCA response
"""

from __future__ import annotations

import re

from network_guy.agents.incident import analyze_incidents
from network_guy.agents.log_analyst import analyze_logs
from network_guy.agents.metrics import analyze_metrics
from network_guy.agents.security.security_agent import analyze_security
from network_guy.agents.topology import analyze_topology, find_device_id_by_name
from network_guy.models import AgentFindings, QueryContext, RCAResponse, ThreatVerdict
from network_guy.prompts.system import QUERY_TEMPLATE, SYSTEM_PROMPT
from network_guy.stores.graph import TopologyGraph
from network_guy.stores.metrics_db import MetricsDB
from network_guy.stores.vector import VectorStore


# Known device names for extraction
KNOWN_DEVICES = [
    "ROUTER-LAB-01", "ROUTER-LAB-02",
    "SW-LAB-01", "SW-LAB-02",
    "FIREWALL-01", "FIREWALL-02",
    "LB-LAB-01", "LB-LAB-02",
    "5G-AMF-01", "5G-SMF-01", "5G-UPF-01",
    "ENODEB-SIM-01", "PACKET-BROKER-01",
    "DNS-SERVER-01", "MGMT-SERVER-01",
]


def parse_query(raw_query: str) -> QueryContext:
    """Extract devices, symptoms, and intent from a natural language query."""
    query_upper = raw_query.upper()

    # Extract device names mentioned in query
    devices = [d for d in KNOWN_DEVICES if d in query_upper]

    # Extract symptoms
    symptoms = []
    symptom_keywords = {
        "packet drop": "packet_loss",
        "dropping packet": "packet_loss",
        "bgp": "bgp_issue",
        "flap": "flapping",
        "cpu": "cpu_spike",
        "memory": "memory_pressure",
        "down": "device_down",
        "unreachable": "device_down",
        "crash": "process_crash",
        "attack": "security_threat",
        "hack": "security_threat",
        "suspicious": "security_threat",
        "scan": "security_threat",
        "ddos": "security_threat",
        "brute": "security_threat",
    }
    query_lower = raw_query.lower()
    for keyword, symptom in symptom_keywords.items():
        if keyword in query_lower and symptom not in symptoms:
            symptoms.append(symptom)

    # Determine intent
    intent = "root_cause_analysis"
    if any(w in query_lower for w in ["attack", "hack", "suspicious", "security", "scan", "ddos"]):
        intent = "security_analysis"
    elif any(w in query_lower for w in ["blast", "impact", "affected", "downstream"]):
        intent = "blast_radius"
    elif any(w in query_lower for w in ["happened before", "similar", "history", "past"]):
        intent = "historical_correlation"
    elif any(w in query_lower for w in ["fix", "remediat", "resolve", "how do i"]):
        intent = "remediation"
    elif any(w in query_lower for w in ["version", "software", "mismatch"]):
        intent = "version_check"
    elif any(w in query_lower for w in ["critical", "warning", "status", "state"]):
        intent = "status_check"
    elif any(w in query_lower for w in ["all", "summary", "open", "p1", "incident"]):
        intent = "incident_summary"

    return QueryContext(
        raw_query=raw_query,
        devices=devices,
        symptoms=symptoms,
        intent=intent,
    )


def run_agents(
    query_ctx: QueryContext,
    vector_store: VectorStore,
    metrics_db: MetricsDB,
    topo_graph: TopologyGraph,
    raw_data: dict,
) -> AgentFindings:
    """Run all 5 agents in parallel and collect findings."""
    findings = AgentFindings()

    # Determine device ID for metrics/topology queries
    device_id = None
    device_name = None
    if query_ctx.devices:
        device_name = query_ctx.devices[0]
        device_id = find_device_id_by_name(device_name, raw_data)

    def run_log():
        return analyze_logs(
            query=query_ctx.raw_query,
            vector_store=vector_store,
            device=device_name,
        )

    def run_metrics():
        if device_id:
            return analyze_metrics(device_id, metrics_db)
        return None

    def run_topology():
        if device_id:
            return analyze_topology(device_id, topo_graph, device_name)
        return None

    def run_incident():
        return analyze_incidents(query_ctx.raw_query, vector_store)

    def run_security():
        security_events = raw_data.get("security_events", [])
        if security_events:
            return analyze_security(security_events, metrics_db)
        return None

    # Run agents sequentially (SQLite in-memory is not thread-safe)
    # Each agent runs in <200ms so total is still <1 second
    agents = [
        ("log", run_log),
        ("metrics", run_metrics),
        ("topology", run_topology),
        ("incident", run_incident),
        ("security", run_security),
    ]

    for agent_name, agent_fn in agents:
        try:
            result = agent_fn()
            if result is not None:
                if agent_name == "log":
                    findings.log_analysis = result
                elif agent_name == "metrics":
                    findings.metrics_analysis = result
                elif agent_name == "topology":
                    findings.topology_analysis = result
                elif agent_name == "incident":
                    findings.incident_analysis = result
                elif agent_name == "security":
                    findings.security_analysis = result
        except Exception as e:
            print(f"  Warning: {agent_name} agent failed: {e}")

    return findings


def format_findings_for_llm(findings: AgentFindings, raw_data: dict, query: str) -> str:
    """Format agent findings into a prompt for Claude."""
    # Log analysis
    log_text = "No log analysis available."
    if findings.log_analysis:
        la = findings.log_analysis
        log_text = (
            f"Events found: {len(la.events)} ({la.error_count} errors, {la.critical_count} critical)\n"
            f"Patterns detected: {', '.join(la.patterns) if la.patterns else 'None'}\n"
            f"Timeline:\n{la.timeline_summary}"
        )

    # Metrics analysis
    metrics_text = "No metrics analysis available."
    if findings.metrics_analysis:
        ma = findings.metrics_analysis
        peaks = ", ".join(f"{k}={v}" for k, v in ma.peak_values.items() if v > 0)
        metrics_text = (
            f"Readings analyzed: {len(ma.readings)}\n"
            f"Peak values: {peaks}\n"
            f"Anomalies:\n" + "\n".join(f"  - {a}" for a in ma.anomalies) + "\n"
            f"Correlations: {ma.correlations}\n"
            f"Trends: {ma.trend_summary}"
        )

    # Topology analysis
    topo_text = "No topology analysis available."
    if findings.topology_analysis:
        ta = findings.topology_analysis
        topo_text = (
            f"Failed device: {ta.failed_device}\n"
            f"Downstream devices: {', '.join(ta.downstream_devices)}\n"
            f"Links affected: {ta.affected_links}\n"
            f"Critical paths lost: {ta.critical_paths_lost}\n"
            f"Impact:\n{ta.impact_summary}"
        )

    # Incident analysis
    incident_text = "No incident correlation available."
    if findings.incident_analysis:
        ia = findings.incident_analysis
        incident_text = (
            f"Matches found: {len(ia.matches)}\n"
            f"Best match: {ia.best_match_id} (similarity: {ia.similarity_score:.0%})\n"
            f"Resolution:\n{ia.recommended_resolution}"
        )

    # Security analysis
    security_text = "No security analysis available."
    if findings.security_analysis:
        sa = findings.security_analysis
        chain = "\n".join(f"  - {c}" for c in sa.attack_chain[:8])
        evidence = "\n".join(f"  - {e}" for e in sa.evidence[:5])
        containment = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sa.containment_steps[:5]))
        security_text = (
            f"Verdict: {sa.verdict.value} (confidence: {sa.confidence:.0%})\n"
            f"Attack type: {sa.attack_type.value if sa.attack_type else 'None'}\n"
            f"Is attack: {sa.is_attack}\n"
            f"Attack chain:\n{chain}\n"
            f"Evidence:\n{evidence}\n"
            f"Containment steps:\n{containment}"
        )

    # Device context
    device_ctx = "No specific device context."
    devices = raw_data.get("devices", [])
    if devices:
        lines = []
        for d in devices:
            if d.status.value != "UP":
                lines.append(
                    f"  {d.device_name} ({d.device_type}, {d.vendor} {d.model}): "
                    f"Status={d.status.value}, Version={d.software_version}, "
                    f"Network={d.lab_network}, Uptime={d.uptime_hours}h"
                )
        if lines:
            device_ctx = "Devices with non-UP status:\n" + "\n".join(lines)

    return QUERY_TEMPLATE.format(
        query=query,
        log_analysis=log_text,
        metrics_analysis=metrics_text,
        topology_analysis=topo_text,
        incident_analysis=incident_text,
        security_analysis=security_text,
        device_context=device_ctx,
    )


def call_llm(prompt: str) -> str:
    """Call the LLM with the formatted prompt.

    Auto-detects which provider has an API key set.
    Supports: DeepSeek, Gemini, OpenRouter, Grok, Anthropic.
    """
    from network_guy.llm import call_llm as _call_llm

    return _call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
    )


def process_query(
    query: str,
    vector_store: VectorStore,
    metrics_db: MetricsDB,
    topo_graph: TopologyGraph,
    raw_data: dict,
) -> RCAResponse:
    """Full pipeline: parse query → run agents → synthesize → return RCA.

    This is the main entry point called by the CLI.
    """
    # Step 1: Parse query
    query_ctx = parse_query(query)

    # Step 2: Run all agents in parallel
    findings = run_agents(query_ctx, vector_store, metrics_db, topo_graph, raw_data)

    # Step 3: Format for LLM
    prompt = format_findings_for_llm(findings, raw_data, query)

    # Step 4: Call Claude (or fallback)
    llm_response = call_llm(prompt)

    # Step 5: Build RCA response
    security_verdict = ThreatVerdict.LEGITIMATE
    security_detail = ""
    if findings.security_analysis:
        security_verdict = findings.security_analysis.verdict
        if findings.security_analysis.is_attack:
            security_detail = (
                f"Attack detected: {findings.security_analysis.attack_type.value if findings.security_analysis.attack_type else 'unknown'} "
                f"(confidence: {findings.security_analysis.confidence:.0%})"
            )
        else:
            security_detail = "No attack detected. Legitimate operational failure."

    affected = []
    blast_summary = ""
    if findings.topology_analysis:
        affected = findings.topology_analysis.downstream_devices
        blast_summary = findings.topology_analysis.impact_summary

    evidence = []
    if findings.log_analysis:
        for e in findings.log_analysis.events:
            if e.severity.value in ("ERROR", "CRIT"):
                evidence.append(f"[{e.severity.value}] {e.message}")
    if findings.metrics_analysis:
        evidence.extend(findings.metrics_analysis.anomalies[:5])

    remediation = []
    if findings.incident_analysis and findings.incident_analysis.recommended_resolution:
        remediation.append(findings.incident_analysis.recommended_resolution)

    historical = None
    if findings.incident_analysis and findings.incident_analysis.best_match_id:
        historical = (
            f"{findings.incident_analysis.best_match_id} "
            f"(similarity: {findings.incident_analysis.similarity_score:.0%})"
        )

    # Extract confidence from LLM response if present
    confidence = 0.85  # default
    conf_match = re.search(r"\*\*Confidence:\*\*\s*(\d+)%", llm_response)
    if conf_match:
        confidence = int(conf_match.group(1)) / 100

    return RCAResponse(
        root_cause="See analysis below.",
        confidence=confidence,
        severity="P1" if any(
            s in query.lower() for s in ["critical", "crash", "down", "drop"]
        ) else "P2",
        evidence=evidence[:10],
        remediation_steps=remediation,
        affected_devices=affected,
        blast_radius_summary=blast_summary,
        historical_match=historical,
        security_verdict=security_verdict,
        security_detail=security_detail,
        raw_llm_response=llm_response,
    )
