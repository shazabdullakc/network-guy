"""Signature Engine — matches known attack patterns against security events.

Each signature is a regex pattern + threshold that identifies a specific attack type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from network_guy.models import SecurityEvent


@dataclass
class SignatureHit:
    """A single signature match result."""

    attack_type: str
    confidence: float
    severity: str
    evidence: list[str] = field(default_factory=list)
    source_ips: list[str] = field(default_factory=list)
    details: str = ""


# --- Signature Definitions ---

SIGNATURES = {
    "brute_force": {
        "patterns": [
            r"(?i)ssh login failed",
            r"(?i)brute force threshold",
            r"(?i)authentication failure",
        ],
        "min_matches": 5,
        "confidence": 0.95,
        "severity": "HIGH",
    },
    "port_scan": {
        "patterns": [
            r"(?i)port scan detected",
            r"(?i)connection attempt.*dest.*:\d+",
        ],
        "min_matches": 3,
        "confidence": 0.90,
        "severity": "MEDIUM",
    },
    "ddos": {
        "patterns": [
            r"(?i)syn flood",
            r"(?i)traffic spike",
            r"(?i)saturated",
            r"(?i)udp flood",
        ],
        "min_matches": 1,
        "confidence": 0.85,
        "severity": "CRITICAL",
    },
    "bgp_hijack": {
        "patterns": [
            r"(?i)bgp hijack",
            r"(?i)route origin mismatch",
            r"(?i)rogue as",
        ],
        "min_matches": 1,
        "confidence": 0.92,
        "severity": "CRITICAL",
    },
    "arp_spoof": {
        "patterns": [
            r"(?i)arp spoof",
            r"(?i)mac address conflict",
            r"(?i)gratuitous arp",
        ],
        "min_matches": 1,
        "confidence": 0.88,
        "severity": "HIGH",
    },
    "unauthorized_access": {
        "patterns": [
            r"(?i)acl modified",
            r"(?i)snmp community.*changed",
            r"(?i)config.*change.*unknown",
        ],
        "min_matches": 1,
        "confidence": 0.75,
        "severity": "CRITICAL",
    },
    "rogue_device": {
        "patterns": [
            r"(?i)not in inventory",
            r"(?i)dhcp snooping violation",
            r"(?i)unauthorized dhcp",
        ],
        "min_matches": 1,
        "confidence": 0.90,
        "severity": "HIGH",
    },
}


def scan_signatures(events: list[SecurityEvent]) -> list[SignatureHit]:
    """Scan security events against all known attack signatures.

    Returns a list of SignatureHit for each detected attack type.
    """
    hits = []

    for attack_type, sig in SIGNATURES.items():
        matching_events = []
        for event in events:
            raw = event.raw_line
            for pattern in sig["patterns"]:
                if re.search(pattern, raw):
                    matching_events.append(event)
                    break

        if len(matching_events) >= sig["min_matches"]:
            source_ips = list({e.source_ip for e in matching_events if e.source_ip})
            evidence = [
                f"Line {e.line_number}: [{e.severity.value}] {e.device} — "
                f"{e.raw_line.split('|', 1)[-1].strip()[:100]}"
                for e in matching_events[:5]  # Top 5 evidence lines
            ]

            hits.append(
                SignatureHit(
                    attack_type=attack_type,
                    confidence=sig["confidence"],
                    severity=sig["severity"],
                    evidence=evidence,
                    source_ips=source_ips,
                    details=f"{len(matching_events)} events matched {attack_type} signature",
                )
            )

    return hits
