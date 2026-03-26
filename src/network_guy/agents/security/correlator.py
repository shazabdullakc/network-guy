"""Threat Correlator — cross-references signature hits + anomalies into attack chains.

Takes individual findings and builds a coherent attack narrative:
  Reconnaissance (08:05) → Scanning (08:07) → Flood (08:09) → Impact (08:15)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from network_guy.agents.security.anomaly import AnomalyFinding
from network_guy.agents.security.signatures import SignatureHit
from network_guy.models import ThreatVerdict


@dataclass
class ThreatAssessment:
    """Complete threat assessment combining signatures + anomalies."""

    verdict: ThreatVerdict
    confidence: float
    attack_types: list[str] = field(default_factory=list)
    attack_chain: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    source_ips: list[str] = field(default_factory=list)
    containment_steps: list[str] = field(default_factory=list)
    reasoning: str = ""


def correlate_threats(
    signature_hits: list[SignatureHit],
    anomaly_findings: list[AnomalyFinding],
) -> ThreatAssessment:
    """Correlate all security findings into a unified threat assessment.

    This is the decision engine that determines:
    1. Is this an attack or legitimate failure?
    2. What type of attack?
    3. What's the attack chain (timeline)?
    4. How to contain it?
    """
    # No findings at all → legitimate
    if not signature_hits and not anomaly_findings:
        return ThreatAssessment(
            verdict=ThreatVerdict.LEGITIMATE,
            confidence=0.95,
            reasoning="No attack signatures or anomalies detected. "
            "Failure is likely caused by normal operational issues.",
        )

    # Collect all attack types and source IPs
    attack_types = [h.attack_type for h in signature_hits]
    all_sources = []
    for h in signature_hits:
        all_sources.extend(h.source_ips)
    source_ips = list(set(all_sources))

    # Collect all evidence
    evidence = []
    for h in signature_hits:
        evidence.extend(h.evidence)
    for a in anomaly_findings:
        evidence.extend(a.evidence)

    # Build attack chain (ordered by attack phase)
    attack_chain = _build_attack_chain(signature_hits, anomaly_findings)

    # Calculate overall confidence
    confidence = _calculate_confidence(signature_hits, anomaly_findings)

    # Determine verdict
    verdict = _determine_verdict(signature_hits, anomaly_findings, confidence)

    # Generate containment steps
    containment = _generate_containment(signature_hits, anomaly_findings, source_ips)

    # Build reasoning
    reasoning = _build_reasoning(verdict, signature_hits, anomaly_findings, source_ips)

    return ThreatAssessment(
        verdict=verdict,
        confidence=confidence,
        attack_types=attack_types,
        attack_chain=attack_chain,
        evidence=evidence[:15],  # Cap at 15 evidence items
        source_ips=source_ips,
        containment_steps=containment,
        reasoning=reasoning,
    )


def _build_attack_chain(
    hits: list[SignatureHit], anomalies: list[AnomalyFinding]
) -> list[str]:
    """Build ordered attack chain from findings."""
    chain = []

    # Phase ordering: recon → scanning → exploitation → impact
    phase_order = {
        "brute_force": (1, "Reconnaissance"),
        "port_scan": (2, "Scanning"),
        "ddos": (3, "Attack"),
        "bgp_hijack": (3, "Attack"),
        "arp_spoof": (3, "Attack"),
        "unauthorized_access": (4, "Exploitation"),
        "rogue_device": (4, "Exploitation"),
    }

    for hit in sorted(hits, key=lambda h: phase_order.get(h.attack_type, (5, ""))[0]):
        order, phase = phase_order.get(hit.attack_type, (5, "Unknown"))
        ips = ", ".join(hit.source_ips[:3]) if hit.source_ips else "unknown source"
        chain.append(
            f"Phase {order} ({phase}): {hit.attack_type} detected from {ips} "
            f"[{hit.severity}, confidence: {hit.confidence:.0%}]"
        )

    # Add anomaly-based phases
    for anomaly in anomalies:
        if anomaly.anomaly_type == "resource_exhaustion":
            chain.append(f"Impact: {anomaly.description}")
        elif anomaly.anomaly_type == "traffic_spike":
            chain.append(f"Amplification: {anomaly.description}")

    return chain


def _calculate_confidence(
    hits: list[SignatureHit], anomalies: list[AnomalyFinding]
) -> float:
    """Calculate overall confidence based on findings.

    More corroborating evidence = higher confidence.
    """
    if not hits and not anomalies:
        return 0.0

    # Start with highest individual confidence
    all_confidences = [h.confidence for h in hits] + [a.confidence for a in anomalies]
    base = max(all_confidences)

    # Boost for corroborating evidence
    boost = 0.0
    if len(hits) >= 2:
        boost += 0.05  # Multiple signature types match
    if len(hits) >= 3:
        boost += 0.03
    if anomalies:
        boost += 0.03  # Anomalies support signature findings

    # Check for attack chain coherence (recon + attack = higher confidence)
    attack_types = {h.attack_type for h in hits}
    if "brute_force" in attack_types and "port_scan" in attack_types:
        boost += 0.05  # Recon before attack is classic pattern
    if "ddos" in attack_types and any(
        a.anomaly_type == "traffic_spike" for a in anomalies
    ):
        boost += 0.05  # DDoS signature confirmed by traffic anomaly

    return min(0.99, base + boost)


def _determine_verdict(
    hits: list[SignatureHit], anomalies: list[AnomalyFinding], confidence: float
) -> ThreatVerdict:
    """Determine final verdict: ATTACK, LEGITIMATE, or INCONCLUSIVE."""
    if not hits:
        # Only anomalies, no signatures
        if anomalies and any(a.confidence > 0.8 for a in anomalies):
            return ThreatVerdict.INCONCLUSIVE
        return ThreatVerdict.LEGITIMATE

    if confidence >= 0.7:
        return ThreatVerdict.ATTACK

    if confidence >= 0.5:
        return ThreatVerdict.INCONCLUSIVE

    return ThreatVerdict.LEGITIMATE


def _generate_containment(
    hits: list[SignatureHit],
    anomalies: list[AnomalyFinding],
    source_ips: list[str],
) -> list[str]:
    """Generate specific containment recommendations based on attack type."""
    steps = []

    attack_types = {h.attack_type for h in hits}

    # Always block attacker IPs first
    if source_ips:
        for ip in source_ips[:5]:
            steps.append(f"Block source IP at perimeter firewall: deny {ip}")

    if "brute_force" in attack_types:
        steps.append("Enable SSH key-only authentication (disable password login)")
        steps.append("Set SSH max-retry to 3 and lockout period to 300 seconds")

    if "port_scan" in attack_types:
        steps.append("Enable port security on all switch interfaces")
        steps.append("Configure rate-limiting for connection attempts")

    if "ddos" in attack_types:
        steps.append("Enable rate-limiting on affected interfaces")
        steps.append("Configure CoPP (Control Plane Policing) to protect management plane")
        steps.append("Enable SYN cookies: ip tcp synwait-time 10")

    if "bgp_hijack" in attack_types:
        steps.append("Enable BGP route origin validation (RPKI/ROV)")
        steps.append("Apply strict AS-path filtering on all BGP peers")
        steps.append("Verify all BGP neighbor configurations")

    if "arp_spoof" in attack_types:
        steps.append("Enable Dynamic ARP Inspection (DAI) on all VLANs")
        steps.append("Enable DHCP snooping on all access ports")

    if "unauthorized_access" in attack_types:
        steps.append("Rotate all SNMP community strings immediately")
        steps.append("Review and restore ACLs from backup configuration")
        steps.append("Audit all user accounts for unauthorized additions")

    if "rogue_device" in attack_types:
        steps.append("Shut down switch port with rogue device")
        steps.append("Enable 802.1X port-based authentication")

    # Long-term hardening
    steps.append("Review and update all firewall rules")
    steps.append("Enable comprehensive logging and SIEM integration")

    return steps


def _build_reasoning(
    verdict: ThreatVerdict,
    hits: list[SignatureHit],
    anomalies: list[AnomalyFinding],
    source_ips: list[str],
) -> str:
    """Build human-readable reasoning for the verdict."""
    if verdict == ThreatVerdict.LEGITIMATE:
        return (
            "No attack signatures detected in security logs. "
            "Anomalies (if any) are consistent with legitimate operational failures "
            "(hardware issues, software bugs, resource exhaustion from normal traffic). "
            "Recommend standard troubleshooting procedures."
        )

    if verdict == ThreatVerdict.INCONCLUSIVE:
        return (
            "Some anomalies detected but insufficient evidence for definitive attack classification. "
            "Recommend monitoring and investigation. "
            f"Suspicious indicators: {len(hits)} signature matches, {len(anomalies)} anomalies."
        )

    # ATTACK verdict
    types = ", ".join(h.attack_type for h in hits)
    ips = ", ".join(source_ips[:5])
    return (
        f"ATTACK CONFIRMED with {len(hits)} signature matches ({types}). "
        f"Source IPs: {ips}. "
        f"Attack chain shows progression from reconnaissance to exploitation. "
        f"Immediate containment recommended."
    )
