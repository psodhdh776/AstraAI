"""
Граф знаний: визуализация связей между заметками, историей, фактами пользователя.
Строит граф, где узлы = слова/темы, рёбра = совместная встречаемость (PMI).
"""

import re
import datetime
import json
import math
from collections import Counter, defaultdict


STOP_WORDS = set([
    "это", "что", "как", "так", "вот", "его", "её", "их", "все", "она",
    "они", "мы", "вы", "ты", "он", "на", "не", "да", "нет", "и", "а",
    "но", "или", "из", "за", "о", "об", "по", "до", "с", "со", "у",
    "к", "во", "от", "про", "для", "же", "ли", "бы", "было", "будет",
    "the", "is", "to", "of", "in", "that", "it", "for", "on", "with",
    "as", "at", "by", "an", "are", "be", "was", "were", "been",
    "has", "had", "have", "do", "does", "did", "but", "not", "or",
    "этот", "эта", "это", "эти", "такой", "такая", "такие", "такое",
    "который", "которая", "которые", "которое", "чтобы", "также",
    "можно", "нужно", "надо", "может", "могут", "будто", "чтобы",
    "уже", "ещё", "еще", "только", "когда", "потом", "потому",
    "поэтому", "почему", "зачем", "откуда", "куда", "где", "тут",
    "там", "здесь", "всегда", "иногда", "часто", "редко",
    "this", "that", "these", "those", "very", "just", "like",
    "about", "then", "than", "more", "some", "could", "would",
    "will", "can", "should", "may", "might", "shall",
])


class KnowledgeGraph:
    def __init__(self, assistant):
        self.assistant = assistant
        self.nodes = {}
        self.edges = {}
        self.timeline = []
        self.rebuild_count = 0
        self._total_docs = 0
        self._last_history_len = 0

    def rebuild(self):
        self.nodes = {}
        self.edges = {}
        word_pairs = Counter()
        word_counts = Counter()
        doc_count = Counter()

        sources = []

        history = getattr(self.assistant, "history", [])
        for h in history[-300:]:
            text = h.get("text", "")
            sources.append(text)

        notes = getattr(self.assistant, "notes", [])
        for n in notes:
            sources.append(n.get("text", ""))

        dialogue = getattr(self.assistant, "dialogue", None)
        if dialogue:
            facts = []
            if hasattr(dialogue, 'context') and isinstance(dialogue.context, dict):
                facts = dialogue.context.get("facts", [])
            elif hasattr(dialogue, 'memory') and hasattr(dialogue.memory, 'long_term'):
                facts = dialogue.memory.long_term.get("facts", [])
            for fact in facts:
                sources.append(fact)

        if dialogue:
            hobbies, likes = [], []
            if hasattr(dialogue, 'profile') and dialogue.profile:
                profile = dialogue.profile
                hobbies = profile.get("hobbies", [])
                likes = profile.get("likes", [])
            elif hasattr(dialogue, 'memory') and hasattr(dialogue.memory, 'long_term'):
                lt = dialogue.memory.long_term
                hobbies = lt.get("hobbies", [])
                likes = lt.get("likes", [])
            for hobby in hobbies:
                sources.append(hobby)
            for like in likes:
                sources.append(like)

        self._total_docs = len(sources)

        for text in sources:
            if not text:
                continue
            words = re.findall(r'[а-яёА-ЯЁa-zA-Z-]{3,}', text.lower())
            words = [w for w in words if w not in STOP_WORDS]

            seen = set()
            for w in words:
                word_counts[w] += 1
                seen.add(w)
            for w in seen:
                doc_count[w] += 1

            for i in range(len(words)):
                for j in range(i + 1, min(i + 4, len(words))):
                    pair = tuple(sorted([words[i], words[j]]))
                    word_pairs[pair] += 1

        if word_counts:
            max_count = max(word_counts.values())
            for word, count in word_counts.items():
                if count >= 2:
                    self.nodes[word] = {
                        "count": count,
                        "weight": count / max_count,
                        "frequency": count,
                        "doc_freq": doc_count.get(word, 1),
                    }

            total_docs = max(self._total_docs, 1)
            max_pair = max(word_pairs.values()) if word_pairs else 1
            for (w1, w2), count in word_pairs.items():
                if count >= 2 and w1 in self.nodes and w2 in self.nodes:
                    p_w1 = self.nodes[w1]["doc_freq"] / total_docs
                    p_w2 = self.nodes[w2]["doc_freq"] / total_docs
                    p_joint = count / total_docs
                    pmi = 0
                    if p_joint > 0 and p_w1 > 0 and p_w2 > 0:
                        pmi = math.log2(p_joint / (p_w1 * p_w2)) if (p_w1 * p_w2) > 0 else 0

                    self.edges[(w1, w2)] = {
                        "count": count,
                        "weight": count / max_pair,
                        "pmi": max(0, pmi),
                    }

        self._last_history_len = len(history)
        self.rebuild_count += 1
        return len(self.nodes)

    def incremental_update(self):
        history = getattr(self.assistant, "history", [])
        if len(history) <= self._last_history_len:
            return
        new_entries = history[self._last_history_len:]
        if not new_entries:
            return

        for h in new_entries:
            text = h.get("text", "")
            if not text:
                continue
            words = re.findall(r'[а-яёА-ЯЁa-zA-Z-]{3,}', text.lower())
            words = [w for w in words if w not in STOP_WORDS]
            for w in words:
                if w in self.nodes:
                    self.nodes[w]["count"] += 1
                    self.nodes[w]["frequency"] += 1
                else:
                    self.nodes[w] = {"count": 1, "weight": 0.1, "frequency": 1, "doc_freq": 1}

            for i in range(len(words)):
                for j in range(i + 1, min(i + 4, len(words))):
                    pair = tuple(sorted([words[i], words[j]]))
                    if pair in self.edges:
                        self.edges[pair]["count"] += 1
                    elif pair[0] in self.nodes and pair[1] in self.nodes:
                        self.edges[pair] = {"count": 1, "weight": 0.1, "pmi": 0}

        self._last_history_len = len(history)

    def get_top_nodes(self, limit=20):
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: (-x[1]["count"], x[0])
        )
        return [
            {"word": word, "count": data["count"], "weight": data["weight"]}
            for word, data in sorted_nodes[:limit]
        ]

    def get_top_edges(self, limit=10):
        sorted_edges = sorted(
            self.edges.items(),
            key=lambda x: -x[1].get("pmi", x[1]["count"])
        )
        return [
            {"source": w1, "target": w2, "weight": data["weight"],
             "count": data["count"], "pmi": data.get("pmi", 0)}
            for (w1, w2), data in sorted_edges[:limit]
        ]

    def get_connections(self, word):
        word = word.lower()
        if word not in self.nodes:
            return []

        connections = []
        for (w1, w2), data in self.edges.items():
            if w1 == word:
                connections.append({"word": w2, **data})
            elif w2 == word:
                connections.append({"word": w1, **data})

        connections.sort(key=lambda x: -x.get("pmi", x["count"]))
        return connections

    def search(self, query):
        tl = query.lower().strip()
        matches = []
        for word, data in self.nodes.items():
            if tl in word:
                connections = self.get_connections(word)
                matches.append({
                    "word": word,
                    "count": data["count"],
                    "connections": [c["word"] for c in connections[:5]],
                })
        matches.sort(key=lambda x: -x["count"])
        return matches[:10]

    def get_graph_data(self):
        return {
            "nodes": [
                {"id": node, "size": data["weight"] * 10 + 2}
                for node, data in self.nodes.items()
            ],
            "edges": [
                {"source": w1, "target": w2, "weight": data["weight"],
                 "pmi": data.get("pmi", 0)}
                for (w1, w2), data in self.edges.items()
            ],
        }

    def get_summary(self):
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "top_words": [w for w, _ in
                sorted(self.nodes.items(), key=lambda x: -x[1]["count"])[:10]],
            "rebuilds": self.rebuild_count,
        }

    def get_insights(self):
        insights = []

        if len(self.nodes) > 10:
            top = self.get_top_nodes(5)
            words = ", ".join(t["word"] for t in top)
            insights.append(f"📊 Чаще всего в диалогах: {words}")

        if len(self.edges) > 5:
            top_edges = self.get_top_edges(3)
            for e in top_edges:
                insights.append(f"🔗 <b>{e['source']}</b> ↔ <b>{e['target']}</b>")

        dialogue = getattr(self.assistant, "dialogue", None)
        hobbies, likes, facts = [], [], []
        if dialogue:
            if hasattr(dialogue, 'profile') and dialogue.profile:
                profile = dialogue.profile
                hobbies = profile.get("hobbies", [])
                likes = profile.get("likes", [])
            elif hasattr(dialogue, 'memory') and hasattr(dialogue.memory, 'long_term'):
                lt = dialogue.memory.long_term
                hobbies = lt.get("hobbies", [])
                likes = lt.get("likes", [])
                facts = lt.get("facts", [])
            if hasattr(dialogue, 'context') and isinstance(dialogue.context, dict):
                facts = dialogue.context.get("facts", facts)
        if hobbies:
            insights.append(f"🎯 Твои интересы: {', '.join(hobbies[:3])}")
        if likes:
            insights.append(f"❤️ Тебе нравится: {', '.join(likes[:3])}")
        if facts:
            insights.append(f"💡 Факты о тебе: {', '.join(facts[:3])}")

        if not insights:
            insights.append("💬 Начни общение, чтобы я узнал тебя лучше")

        return insights