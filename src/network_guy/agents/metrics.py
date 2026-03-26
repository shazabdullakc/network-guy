"""Metrics Agent — queries SNMP time-series data, detects anomalies and trends.

Input: Device ID + time range + metric names
Process: SQL queries → threshold checks → trend detection → correlation
Output: Peak values, anomalies, trend summary, correlations
"""

from __future__ import annotations

import statistics

from network_guy.models import MetricsAnalysisResult, MetricReading, MetricStatus
from network_guy.stores.metrics_db import MetricsDB


def analyze_metrics(
    device_id: str,
    metrics_db: MetricsDB,
    metric_names: list[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> MetricsAnalysisResult:
    """Analyze SNMP metrics for a device — peaks, anomalies, trends.

    Args:
        device_id: Device to analyze (e.g., "D001")
        metrics_db: SQLite instance
        metric_names: Specific metrics to check. None = all metrics.
        start_time: ISO timestamp start. None = all time.
        end_time: ISO timestamp end.
    """
    # Get all metrics for this device
    if metric_names:
        all_readings = []
        for name in metric_names:
            all_readings.extend(
                metrics_db.get_device_metrics(device_id, name, start_time, end_time)
            )
    else:
        all_readings = metrics_db.get_device_metrics(device_id, start_time=start_time, end_time=end_time)

    # Convert to MetricReading models
    readings = [
        MetricReading(
            timestamp=r["timestamp"],
            device_id=r["device_id"],
            device_name=r["device_name"],
            metric_name=r["metric_name"],
            metric_value=r["metric_value"],
            unit=r["unit"],
            threshold_warn=r["threshold_warn"],
            threshold_crit=r["threshold_crit"],
            status=MetricStatus(r["status"]),
        )
        for r in all_readings
    ]

    # Get peaks
    peaks_raw = metrics_db.get_metric_peaks(device_id)
    peak_values = {p["metric_name"]: p["peak_value"] for p in peaks_raw}

    # Detect anomalies
    anomalies = _detect_anomalies(readings, metrics_db, device_id)

    # Detect correlations
    correlations = _detect_correlations(readings)

    # Build trend summary
    trend_summary = _build_trend_summary(readings, peak_values)

    return MetricsAnalysisResult(
        readings=readings,
        anomalies=anomalies,
        peak_values=peak_values,
        correlations=correlations,
        trend_summary=trend_summary,
    )


def get_critical_devices(metrics_db: MetricsDB) -> list[dict]:
    """Find all devices with WARNING or CRITICAL status metrics."""
    warning = metrics_db.get_devices_by_status("WARNING")
    critical = metrics_db.get_devices_by_status("CRITICAL")
    return critical + warning


def _detect_anomalies(
    readings: list[MetricReading],
    metrics_db: MetricsDB,
    device_id: str,
) -> list[str]:
    """Detect anomalies using Z-score (standard deviations from baseline)."""
    anomalies = []

    # Group readings by metric name
    by_metric: dict[str, list[float]] = {}
    for r in readings:
        by_metric.setdefault(r.metric_name, []).append(r.metric_value)

    for metric_name, values in by_metric.items():
        if len(values) < 3:
            continue

        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        if stdev == 0:
            continue

        peak = max(values)
        z_score = (peak - mean) / stdev

        if z_score > 2.0:
            # Find the reading with the peak
            peak_reading = next(
                (r for r in readings if r.metric_name == metric_name and r.metric_value == peak),
                None,
            )
            status_str = f" ({peak_reading.status.value})" if peak_reading else ""
            anomalies.append(
                f"{metric_name} peaked at {peak} {peak_reading.unit if peak_reading else ''}"
                f"{status_str} — "
                f"{z_score:.1f} standard deviations above mean ({mean:.1f})"
            )

    # Check for threshold breaches
    for r in readings:
        if r.status == MetricStatus.CRITICAL and r.metric_value > r.threshold_crit:
            anomalies.append(
                f"{r.metric_name} = {r.metric_value} {r.unit} at {r.timestamp} "
                f"EXCEEDS critical threshold ({r.threshold_crit})"
            )

    # Deduplicate
    return list(dict.fromkeys(anomalies))


def _detect_correlations(readings: list[MetricReading]) -> str:
    """Detect if multiple metrics spike at the same timestamp."""
    # Group by timestamp
    by_time: dict[str, list[MetricReading]] = {}
    for r in readings:
        ts = str(r.timestamp)
        by_time.setdefault(ts, []).append(r)

    correlations = []
    for ts, time_readings in by_time.items():
        critical_metrics = [r for r in time_readings if r.status == MetricStatus.CRITICAL]
        if len(critical_metrics) >= 2:
            names = [f"{r.metric_name}={r.metric_value}{r.unit}" for r in critical_metrics]
            correlations.append(
                f"At {ts}: {len(critical_metrics)} metrics in CRITICAL state simultaneously "
                f"({', '.join(names)}) — indicates systemic issue, not isolated failure"
            )

    return "\n".join(correlations) if correlations else "No multi-metric correlations detected."


def _build_trend_summary(readings: list[MetricReading], peak_values: dict) -> str:
    """Build a human-readable summary of metric trends."""
    if not readings:
        return "No metric data available."

    # Group by metric for trend analysis
    by_metric: dict[str, list[MetricReading]] = {}
    for r in readings:
        by_metric.setdefault(r.metric_name, []).append(r)

    lines = []
    for metric_name, metric_readings in sorted(by_metric.items()):
        sorted_readings = sorted(metric_readings, key=lambda r: str(r.timestamp))
        if not sorted_readings:
            continue

        values = [r.metric_value for r in sorted_readings]
        first = values[0]
        peak = max(values)
        last = values[-1]
        unit = sorted_readings[0].unit

        # Determine trend
        if peak > first * 1.5 and last < peak * 0.7:
            trend = "spike then recovery"
        elif last > first * 1.3:
            trend = "rising"
        elif last < first * 0.7:
            trend = "falling"
        else:
            trend = "stable"

        # Only report interesting metrics (those that changed significantly)
        if trend != "stable" or peak > sorted_readings[0].threshold_warn:
            lines.append(
                f"{metric_name}: {first} → {peak} (peak) → {last} {unit} [{trend}]"
            )

    return "\n".join(lines) if lines else "All metrics stable within normal range."
