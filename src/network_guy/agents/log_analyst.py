"""Log Analyst Agent — searches syslog events, identifies error patterns and timelines.

Input: User query + device + time range
Process: Semantic search ChromaDB → parse results → identify patterns → rank by severity
Output: Event timeline with patterns and evidence citations
"""

from __future__ import annotations

from network_guy.models import LogAnalysisResult, LogEvent, Severity
from network_guy.stores.vector import VectorStore


def analyze_logs(
    query: str,
    vector_store: VectorStore,
    device: str | None = None,
    top_k: int = 10,
) -> LogAnalysisResult:
    """Search syslog chunks and extract relevant events with patterns.

    Args:
        query: Natural language query (e.g., "BGP dropped on ROUTER-LAB-01")
        vector_store: ChromaDB instance with syslog_chunks collection
        device: Optional device filter
        top_k: Number of chunks to retrieve
    """
    # Search ChromaDB for relevant syslog chunks
    where = {"device": device} if device else None
    results = vector_store.search(
        collection_name="syslog_chunks",
        query=query,
        top_k=top_k,
        where=where,
    )

    # Parse events from chunks
    events: list[LogEvent] = []
    for result in results:
        doc = result["document"]
        metadata = result["metadata"]
        source = metadata.get("source", "router_syslog.log")

        for line in doc.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Parse: [SEVERITY] HH:MM:SS — message
            severity = Severity.INFO
            for sev in Severity:
                if f"[{sev.value}]" in line:
                    severity = sev
                    break

            # Extract time
            time_str = ""
            parts = line.split("—", 1)
            if len(parts) == 2:
                time_part = parts[0].strip()
                # Get just the time after severity tag
                time_tokens = time_part.split("]", 1)
                if len(time_tokens) == 2:
                    time_str = time_tokens[1].strip()

            message = parts[-1].strip() if parts else line

            events.append(
                LogEvent(
                    timestamp=_parse_time_or_default(time_str),
                    severity=severity,
                    device=metadata.get("device", "unknown"),
                    message=message,
                    details={},
                    raw_line=line,
                    line_number=0,
                )
            )

    # Sort by severity (CRIT first) then timestamp
    severity_order = {Severity.CRIT: 0, Severity.ERROR: 1, Severity.WARN: 2, Severity.INFO: 3}
    events.sort(key=lambda e: (severity_order.get(e.severity, 4), e.timestamp))

    # Identify patterns
    patterns = _identify_patterns(events)

    # Build timeline summary
    error_count = sum(1 for e in events if e.severity == Severity.ERROR)
    critical_count = sum(1 for e in events if e.severity == Severity.CRIT)

    timeline = _build_timeline_summary(events)

    return LogAnalysisResult(
        events=events,
        patterns=patterns,
        timeline_summary=timeline,
        error_count=error_count,
        critical_count=critical_count,
    )


def _identify_patterns(events: list[LogEvent]) -> list[str]:
    """Detect common failure patterns from event sequences."""
    patterns = []
    messages = " ".join(e.message.lower() for e in events)

    # Pattern: CPU spike precedes other failures
    if "cpu" in messages and ("bgp" in messages or "interface" in messages):
        patterns.append("CPU spike precedes routing/interface failures")

    # Pattern: Memory pressure cascade
    if "memory" in messages and ("crash" in messages or "oom" in messages):
        patterns.append("Memory exhaustion leading to process crash (OOM)")

    # Pattern: BGP instability
    if "bgp" in messages and ("drop" in messages or "flap" in messages or "expired" in messages):
        patterns.append("BGP session instability (hold timer expiry or peer drop)")

    # Pattern: Interface flapping
    if "interface" in messages and ("down" in messages and "up" in messages):
        patterns.append("Interface flapping (going down and recovering)")

    # Pattern: Route instability
    if "route" in messages and ("flap" in messages or "unstable" in messages):
        patterns.append("Route table instability (multiple routes flapping)")

    # Pattern: NTP sync loss
    if "ntp" in messages and "lost" in messages:
        patterns.append("NTP sync lost (time-sensitive protocols may be affected)")

    # Pattern: MPLS corruption
    if "mpls" in messages and "corruption" in messages:
        patterns.append("MPLS label stack corruption detected")

    # Pattern: Cascading failure
    error_events = [e for e in events if e.severity in (Severity.ERROR, Severity.CRIT)]
    if len(error_events) >= 3:
        patterns.append(
            f"Cascading failure: {len(error_events)} critical/error events in sequence"
        )

    return patterns


def _build_timeline_summary(events: list[LogEvent]) -> str:
    """Build a human-readable timeline of key events."""
    if not events:
        return "No events found."

    lines = []
    for e in sorted(events, key=lambda x: x.timestamp):
        if e.severity in (Severity.ERROR, Severity.CRIT, Severity.WARN):
            time_str = e.timestamp.strftime("%H:%M:%S") if e.timestamp.year > 1 else "??:??:??"
            lines.append(f"{time_str} [{e.severity.value}] {e.message}")

    if not lines:
        return "All events are INFO-level. No warnings or errors detected."

    return "\n".join(lines)


def _parse_time_or_default(time_str: str):
    """Try to parse a time string, return epoch if it fails."""
    from datetime import datetime, timezone

    time_str = time_str.strip()
    for fmt in ("%H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(time_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=2024, month=3, day=15, tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return datetime(2024, 3, 15, tzinfo=timezone.utc)
