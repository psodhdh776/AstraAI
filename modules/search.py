"""
Full-text search across history and notes.
"""
import logging
import re
from collections import Counter

logger = logging.getLogger("Astra.Search")


def search_history(history, query, max_results=20):
    """Search history entries by text content."""
    if not query:
        return []
    q = query.lower().strip()
    results = []
    for h in reversed(history):
        text = h.get("text", h.get("content", "")).lower()
        role = h.get("role", "user")
        time = h.get("time", "")
        if q in text:
            results.append({"role": role, "text": text, "time": time, "query": query})
            if len(results) >= max_results:
                break
    return results


def search_notes(notes, query):
    if not query:
        return []
    q = query.lower()
    return [n for n in notes if q in (n.get("text", "") if isinstance(n, dict) else str(n)).lower()]


def highlight(text, query):
    """Highlight query terms in text with HTML."""
    if not query:
        return text
    q = re.escape(query)
    return re.sub(f'({q})', r'<b style="color:#6366f1">\1</b>', text, flags=re.IGNORECASE)
