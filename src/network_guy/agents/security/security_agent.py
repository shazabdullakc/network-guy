"""Security Agent — main entry point for attack detection.

Combines three sub-engines:
1. Signature scan → match known attack patterns
2. Anomaly detection → flag statistical outliers
3. Correlation → build attack chain + determine verdict
"""

from __future__ import annotations

from network_guy.agents.security.anomaly import detect_anomalies
from network_guy.agents.security.correlator import correlate_threats
from network_guy.agents.security.signatures import scan_signatures
from network_guy.models import (
    AttackType,
    SecurityAnalysisResult,
    SecurityEvent,
    ThreatVerdict,
)
from network_guy.stores.metrics_db import MetricsDB


# Map string attack types to enum
_ATTACK_TYPE_MAP = {
    "brute_force": AttackType.BRUTE_FORCE,
    "port_scan": AttackType.PORT_SCAN,
    "ddos": AttackType.DDOS,
    "bgp_hijack": AttackType.BGP_HIJACK,
    "arp_spoof": AttackType.ARP_SPOOF,
    "unauthorized_access": AttackType.UNAUTHORIZED_ACCESS,
    "rogue_device": AttackType.ROGUE_DEVICE,
}


def analyze_security(
    security_events: list[SecurityEvent],
    metrics_db: MetricsDB,
) -> SecurityAnalysisResult:
    """Run the full security analysis pipeline.

    Args:
        security_events: Parsed security log events
        metrics_db: SQLite instance (for traffic flow analysis)

    Returns:
        SecurityAnalysisResult with verdict, attack chain, evidence, and containment steps.
    """
    # Step 1: Signature scan
    signature_hits = scan_signatures(security_events)

    # Step 2: Anomaly detection
    anomaly_findings = detect_anomalies(metrics_db)

    # Step 3: Correlate everything
    assessment = correlate_threats(signature_hits, anomaly_findings)

    # Determine primary attack type (highest confidence hit)
    primary_attack = None
    if assessment.attack_types:
        primary_type = assessment.attack_types[0]
        primary_attack = _ATTACK_TYPE_MAP.get(primary_type)

    return SecurityAnalysisResult(
        is_attack=assessment.verdict == ThreatVerdict.ATTACK,
        verdict=assessment.verdict,
        confidence=assessment.confidence,
        attack_type=primary_attack,
        attack_chain=assessment.attack_chain,
        evidence=assessment.evidence,
        containment_steps=assessment.containment_steps,
    )
