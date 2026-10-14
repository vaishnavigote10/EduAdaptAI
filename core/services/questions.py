"""Rule-based assessment generation with validation + duplicate detection (no API key needed)."""
import hashlib, random, re
from collections import Counter

STOP = set("""about above after again against because before being below between could during further
having itself might other should their there these those through under until where which while would
using used uses also each many most more such than that them then they this very what when your""".split())


def words(text):
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{4,}", text.lower()) if w not in STOP]


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if 8 <= len(s.split()) <= 34]


def tokens(s):
    return set(re.findall(r"[a-z]{3,}", s.lower()))


def concept_terms(texts, n=10):
    counts = Counter(w for t in texts for w in set(words(t)))
    return [w for w, c in counts.most_common() if c >= 2][:n]


def fingerprint(prompt):
    return hashlib.sha1(" ".join(sorted(tokens(prompt))).encode()).hexdigest()


def is_duplicate(prompt, existing_prompts, threshold=0.72):
    a = tokens(prompt)
    for p in existing_prompts:
        b = tokens(p)
        if a and b and len(a & b) / len(a | b) >= threshold:
            return True
    return False


def validate(q):
    opts = q["options"]
    return (q["prompt"].count("_____") == 1 and len(opts) >= 3 and len(set(opts)) == len(opts)
            and q["answer"] in opts and len(q["prompt"]) > 30)


def generate(topic_chunks, other_terms, existing_prompts, limit=6, seed=7):
    """topic_chunks: [{"text","doc","location"}]; other_terms: concept words from other topics."""
    rnd = random.Random(seed)
    counts = Counter(w for c in topic_chunks for w in set(words(c["text"])))
    concepts = {w for w, n in counts.items() if n >= 2} or {w for w, _ in counts.most_common(8)}
    out, taken = [], list(existing_prompts)
    for c in topic_chunks:
        for s in sentences(c["text"]):
            cands = [w for w in words(s) if w in concepts and len(w) > 5]
            if not cands:
                continue
            ans = max(cands, key=lambda w: (counts[w], len(w)))
            prompt = re.sub(re.escape(ans), "_____", s, count=1, flags=re.I)
            if prompt.count("_____") != 1:
                continue
            pool = [w for w in other_terms if w != ans and w not in s.lower()]
            pool += [w for w in concepts if w != ans and w not in s.lower()]
            rnd.shuffle(pool)
            distract = list(dict.fromkeys(pool))[:3]
            opts = distract + [ans]
            rnd.shuffle(opts)
            diff = 1 if counts[ans] >= 4 else 2 if counts[ans] == 3 else 3
            q = {"prompt": "Fill the gap: " + prompt, "options": opts, "answer": ans, "difficulty": diff,
                 "explanation": f"From {c['doc']} ({c['location']}): {s}", "source": f"{c['doc']} · {c['location']}"}
            if validate(q) and not is_duplicate(q["prompt"], taken):
                out.append(q); taken.append(q["prompt"])
            break
        if len(out) >= limit:
            break
    return out
