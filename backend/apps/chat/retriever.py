"""
Tiny dependency-free retriever for RailSetu's RAG chatbot.

Loads the markdown knowledge base, splits it into chunks, and ranks chunks against
a query with TF-IDF cosine similarity. No numpy or scikit-learn needed, so it adds
no weight to the Django service. The corpus is small and curated, which is exactly
where lexical TF-IDF retrieval works well. You can later swap this for sentence
embeddings if you want semantic matching.
"""

import math
import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "be",
    "as", "at", "by", "it", "its", "this", "that", "these", "those", "with", "from",
    "you", "your", "i", "we", "they", "he", "she", "if", "so", "do", "does", "can",
    "will", "would", "about", "what", "which", "how", "when", "where", "who", "my",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1]


class _Index:
    def __init__(self):
        self.chunks = []        # list of {"source", "title", "text"}
        self.vectors = []       # list of {term: tfidf}
        self.norms = []         # list of float
        self.idf = {}
        self._build()

    def _load_chunks(self):
        chunks = []
        if not KNOWLEDGE_DIR.exists():
            return chunks
        for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
            raw = path.read_text(encoding="utf-8")
            title = path.stem
            # Split on blank lines into paragraphs; keep a leading heading as title.
            blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]
            doc_title = title
            for b in blocks:
                if b.startswith("# "):
                    doc_title = b.lstrip("# ").strip()
                    continue
                chunks.append({"source": path.name, "title": doc_title, "text": b})
        return chunks

    def _build(self):
        self.chunks = self._load_chunks()
        if not self.chunks:
            return
        # document frequency
        df = {}
        tokenised = []
        for c in self.chunks:
            toks = _tokens(c["title"] + " " + c["text"])
            tokenised.append(toks)
            for term in set(toks):
                df[term] = df.get(term, 0) + 1
        n = len(self.chunks)
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
        # tf-idf vectors
        for toks in tokenised:
            tf = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            vec = {t: (count / len(toks)) * self.idf.get(t, 0) for t, count in tf.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self.vectors.append(vec)
            self.norms.append(norm)

    def search(self, query, k=4):
        if not self.chunks:
            return []
        q_toks = _tokens(query)
        if not q_toks:
            return []
        q_tf = {}
        for t in q_toks:
            q_tf[t] = q_tf.get(t, 0) + 1
        q_vec = {t: (c / len(q_toks)) * self.idf.get(t, 0) for t, c in q_tf.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        scored = []
        for i, vec in enumerate(self.vectors):
            # dot over the smaller dict
            small, big = (q_vec, vec) if len(q_vec) < len(vec) else (vec, q_vec)
            dot = sum(val * big.get(term, 0) for term, val in small.items())
            if dot <= 0:
                continue
            sim = dot / (q_norm * self.norms[i])
            scored.append((sim, i))
        scored.sort(reverse=True)
        out = []
        for sim, i in scored[:k]:
            c = self.chunks[i]
            out.append({"source": c["source"], "title": c["title"], "text": c["text"], "score": round(sim, 3)})
        return out


_INDEX = None


def get_index():
    global _INDEX
    if _INDEX is None:
        _INDEX = _Index()
    return _INDEX


def retrieve(query, k=4):
    """Return up to k relevant knowledge chunks for the query."""
    return get_index().search(query, k=k)


def context_block(chunks):
    """Format retrieved chunks into a context string for the LLM prompt."""
    if not chunks:
        return "(no relevant knowledge base entries found)"
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] ({c['source']} - {c['title']})\n{c['text']}")
    return "\n\n".join(parts)