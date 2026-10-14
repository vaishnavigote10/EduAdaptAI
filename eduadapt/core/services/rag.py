"""Source-grounded retrieval. Pure functions over plain dicts so they are easy to test.
chunk = {"id", "text", "doc", "kind", "location", "topic"}"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SUPPORT_THRESHOLD = 0.065


def retrieve(query, chunks, k=4):
    if not chunks:
        return []
    vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
    try:
        m = vec.fit_transform([c["text"] for c in chunks] + [query])
    except ValueError:
        return []
    sims = cosine_similarity(m[-1], m[:-1]).ravel()
    order = sims.argsort()[::-1][:k]
    return [(chunks[i], float(sims[i])) for i in order if sims[i] > 0]


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 5]


def extractive_answer(query, hits, n=3):
    qterms = set(re.findall(r"[a-z]{3,}", query.lower()))
    scored = []
    for chunk, score in hits[:3]:
        for s in _sentences(chunk["text"]):
            overlap = len(qterms & set(re.findall(r"[a-z]{3,}", s.lower())))
            scored.append((overlap + score, s))
    scored.sort(key=lambda x: -x[0])
    picked, seen = [], set()
    for _, s in scored:
        if s not in seen:
            picked.append(s); seen.add(s)
        if len(picked) == n:
            break
    return " ".join(picked)


def answer(query, chunks, llm_chat=None):
    hits = retrieve(query, chunks)
    best = hits[0][1] if hits else 0.0
    if best < SUPPORT_THRESHOLD:
        return {"grounded": False, "confidence": round(best, 2), "answer": (
            "I couldn't find this in your uploaded course material, so I won't guess. "
            "Try rephrasing, or upload the lecture notes or slides that cover it."), "citations": []}
    cites = [{"doc": c["doc"], "kind": c["kind"], "location": c["location"], "topic": c["topic"],
              "score": round(s, 2), "snippet": c["text"][:220]} for c, s in hits if s >= SUPPORT_THRESHOLD * 0.6]
    text = None
    if llm_chat:
        ctx = "\n\n".join(f"[{i+1}] ({c['doc']}, {c['location']}) {c['text']}" for i, (c, _) in enumerate(hits))
        text = llm_chat("You are a patient tutor. Answer ONLY from the numbered sources. Cite like [1]. "
                        "If the sources do not contain the answer, say so.", f"Sources:\n{ctx}\n\nQuestion: {query}")
    if not text:
        text = extractive_answer(query, hits)
    return {"grounded": True, "confidence": round(best, 2), "answer": text, "citations": cites}
