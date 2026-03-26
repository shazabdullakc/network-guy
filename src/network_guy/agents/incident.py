"""Incident Agent — searches historical incidents for correlation.

Input: Current symptoms (from other agents' findings)
Process: Semantic search ChromaDB → similarity scoring → extract resolutions
Output: Historical matches with similarity score, past root cause, proven fix
"""

from __future__ import annotations

from network_guy.models import IncidentAnalysisResult
from network_guy.stores.vector import VectorStore


def analyze_incidents(
    query: str,
    vector_store: VectorStore,
    top_k: int = 5,
) -> IncidentAnalysisResult:
    """Search past incidents for similar symptoms and proven resolutions.

    Args:
        query: Symptom description or user query
        vector_store: ChromaDB instance with incidents collection
        top_k: Number of incident matches to return
    """
    results = vector_store.search(
        collection_name="incidents",
        query=query,
        top_k=top_k,
    )

    if not results:
        return IncidentAnalysisResult(
            matches=[],
            best_match_id=None,
            similarity_score=0.0,
            recommended_resolution="No historical incidents found matching current symptoms.",
        )

    matches = []
    for result in results:
        doc = result["document"]
        metadata = result["metadata"]
        distance = result["distance"]

        # Convert distance to similarity (ChromaDB uses L2 distance, lower = more similar)
        # Normalize to 0-1 range where 1 = perfect match
        similarity = max(0.0, 1.0 - (distance / 3.0))

        # Extract key fields from the document text
        ticket_id = metadata.get("ticket_id", "unknown")
        severity = metadata.get("severity", "unknown")
        status = metadata.get("status", "unknown")

        # Extract symptom summary and resolution from document text
        symptom_summary = _extract_section(doc, "Symptoms:")
        user_report = _extract_section(doc, "User report:")
        business_impact = _extract_section(doc, "Business impact:")
        timeline = _extract_section(doc, "Timeline:")
        similar_past = _extract_section(doc, "Similar past incidents:")

        matches.append(
            {
                "ticket_id": ticket_id,
                "similarity": round(similarity, 3),
                "severity": severity,
                "status": status,
                "symptom_summary": symptom_summary,
                "user_report": user_report,
                "business_impact": business_impact,
                "timeline": timeline,
                "similar_past_incidents": similar_past,
                "full_document": doc,
            }
        )

    # Sort by similarity (highest first)
    matches.sort(key=lambda m: m["similarity"], reverse=True)

    best = matches[0] if matches else None

    # Build recommended resolution
    resolution = "No resolution found."
    if best and best["similarity"] > 0.3:
        resolution = (
            f"Historical match: {best['ticket_id']} (similarity: {best['similarity']:.0%})\n"
            f"Severity: {best['severity']} | Status: {best['status']}\n"
            f"Symptoms: {best['symptom_summary']}\n"
            f"Impact: {best['business_impact']}\n"
        )
        if best["similar_past_incidents"] and best["similar_past_incidents"] != "No similar past incidents.":
            resolution += f"Related incidents: {best['similar_past_incidents']}\n"
        resolution += f"\nRecommendation: Review resolution from {best['ticket_id']} for applicable fix steps."

    return IncidentAnalysisResult(
        matches=matches,
        best_match_id=best["ticket_id"] if best else None,
        similarity_score=best["similarity"] if best else 0.0,
        recommended_resolution=resolution,
    )


def _extract_section(doc: str, header: str) -> str:
    """Extract a section from an incident document by its header."""
    lines = doc.split("\n")
    for i, line in enumerate(lines):
        if header.lower() in line.lower():
            # Return the content after the header
            content = line.split(header, 1)[-1].strip()
            if content:
                return content
            # If content is on the next line(s)
            result_lines = []
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                if not next_line or any(
                    h in next_line
                    for h in ["Severity:", "Status:", "Symptoms:", "Timeline:", "Alerts:"]
                ):
                    break
                result_lines.append(next_line)
            return " ".join(result_lines) if result_lines else ""
    return ""
