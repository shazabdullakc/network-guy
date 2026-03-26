"""SQLite store for SNMP metrics and traffic flows.

Why SQLite instead of ChromaDB for metrics?
- Metrics are NUMERIC (CPU=92%, drops=4523). SQL is precise: WHERE cpu > 80.
- ChromaDB does semantic search ("find similar text"). Useless for exact thresholds.
- Traffic flows need aggregation (SUM bytes, COUNT packets). SQL handles this natively.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from network_guy.models import MetricReading, TrafficFlow


class MetricsDB:
    """SQLite wrapper for time-series metrics and traffic flows."""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize SQLite database. Defaults to in-memory (fast, no disk)."""
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                device_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                unit TEXT,
                threshold_warn REAL,
                threshold_crit REAL,
                status TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_metrics_device_time
                ON metrics(device_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_metrics_status
                ON metrics(status);

            CREATE TABLE IF NOT EXISTS flows (
                timestamp TEXT NOT NULL,
                src_ip TEXT NOT NULL,
                dst_ip TEXT NOT NULL,
                src_port INTEGER,
                dst_port TEXT,
                protocol TEXT,
                bytes INTEGER,
                packets INTEGER,
                flags TEXT,
                duration_sec INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_flows_src ON flows(src_ip);
            CREATE INDEX IF NOT EXISTS idx_flows_dst ON flows(dst_ip);
            CREATE INDEX IF NOT EXISTS idx_flows_time ON flows(timestamp);
        """)

    def insert_metrics(self, readings: list[MetricReading]):
        """Bulk insert metric readings."""
        self.conn.executemany(
            """INSERT INTO metrics
               (timestamp, device_id, device_name, metric_name, metric_value,
                unit, threshold_warn, threshold_crit, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    r.timestamp.isoformat(),
                    r.device_id,
                    r.device_name,
                    r.metric_name,
                    r.metric_value,
                    r.unit,
                    r.threshold_warn,
                    r.threshold_crit,
                    r.status.value,
                )
                for r in readings
            ],
        )
        self.conn.commit()

    def insert_flows(self, flows: list[TrafficFlow]):
        """Bulk insert traffic flow records."""
        self.conn.executemany(
            """INSERT INTO flows
               (timestamp, src_ip, dst_ip, src_port, dst_port, protocol,
                bytes, packets, flags, duration_sec)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    f.timestamp.isoformat(),
                    f.src_ip,
                    f.dst_ip,
                    f.src_port,
                    f.dst_port,
                    f.protocol,
                    f.bytes,
                    f.packets,
                    f.flags,
                    f.duration_sec,
                )
                for f in flows
            ],
        )
        self.conn.commit()

    # --- Query Methods ---

    def get_device_metrics(
        self,
        device_id: str,
        metric_name: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[dict]:
        """Get metrics for a device, optionally filtered by metric name and time range."""
        query = "SELECT * FROM metrics WHERE device_id = ?"
        params: list = [device_id]

        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp"
        return [dict(row) for row in self.conn.execute(query, params)]

    def get_critical_metrics(self, device_id: str | None = None) -> list[dict]:
        """Get all CRITICAL status metrics, optionally filtered by device."""
        query = "SELECT * FROM metrics WHERE status = 'CRITICAL'"
        params: list = []
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        query += " ORDER BY timestamp"
        return [dict(row) for row in self.conn.execute(query, params)]

    def get_devices_by_status(self, status: str) -> list[dict]:
        """Find all devices with a specific metric status (WARNING, CRITICAL)."""
        query = """
            SELECT DISTINCT device_id, device_name, metric_name, metric_value, status, timestamp
            FROM metrics WHERE status = ?
            ORDER BY timestamp DESC
        """
        return [dict(row) for row in self.conn.execute(query, [status])]

    def get_metric_peaks(self, device_id: str) -> list[dict]:
        """Get peak (max) value for each metric on a device."""
        query = """
            SELECT metric_name, MAX(metric_value) as peak_value, unit,
                   threshold_warn, threshold_crit
            FROM metrics
            WHERE device_id = ?
            GROUP BY metric_name
            ORDER BY metric_name
        """
        return [dict(row) for row in self.conn.execute(query, [device_id])]

    def get_metric_timeline(self, device_id: str, metric_name: str) -> list[dict]:
        """Get full timeline of a specific metric for trend analysis."""
        query = """
            SELECT timestamp, metric_value, status
            FROM metrics
            WHERE device_id = ? AND metric_name = ?
            ORDER BY timestamp
        """
        return [dict(row) for row in self.conn.execute(query, [device_id, metric_name])]

    # --- Traffic Flow Queries ---

    def get_flows_by_source(self, src_ip: str) -> list[dict]:
        """Get all traffic flows from a specific source IP."""
        query = "SELECT * FROM flows WHERE src_ip = ? ORDER BY timestamp"
        return [dict(row) for row in self.conn.execute(query, [src_ip])]

    def get_top_talkers(self, limit: int = 10) -> list[dict]:
        """Find top source IPs by total bytes sent."""
        query = """
            SELECT src_ip, SUM(bytes) as total_bytes, SUM(packets) as total_packets,
                   COUNT(*) as flow_count
            FROM flows
            GROUP BY src_ip
            ORDER BY total_bytes DESC
            LIMIT ?
        """
        return [dict(row) for row in self.conn.execute(query, [limit])]

    def get_flows_to_target(self, dst_ip: str) -> list[dict]:
        """Get all traffic flows targeting a specific destination IP."""
        query = "SELECT * FROM flows WHERE dst_ip = ? ORDER BY timestamp"
        return [dict(row) for row in self.conn.execute(query, [dst_ip])]

    def get_suspicious_flows(self) -> list[dict]:
        """Find flows with SYN-only flags (potential scan/flood) or very high byte counts."""
        query = """
            SELECT * FROM flows
            WHERE flags = 'SYN' OR bytes > 100000000
            ORDER BY bytes DESC
        """
        return [dict(row) for row in self.conn.execute(query)]

    # --- Stats ---

    def get_stats(self) -> dict:
        """Get summary statistics."""
        metrics_count = self.conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
        flows_count = self.conn.execute("SELECT COUNT(*) FROM flows").fetchone()[0]
        devices = self.conn.execute("SELECT DISTINCT device_id FROM metrics").fetchall()
        return {
            "metrics_count": metrics_count,
            "flows_count": flows_count,
            "devices_tracked": len(devices),
        }

    def close(self):
        self.conn.close()
