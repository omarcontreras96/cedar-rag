"""CEDAR-RAG keyword retriever (standard library only).

Cedar Lab is fictional; its rules are classroom examples, not safety guidance.

Usage: python3 retrieve.py "QUESTION" [K]
"""

import argparse
import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "docs"
DOC_FILES = ["access.txt", "training.txt", "booking.txt"]
STOPWORDS = {
    "a", "an", "the", "is", "are", "to", "of", "in", "at",
    "for", "and", "or", "may", "can", "i", "it", "be",
}
LABEL_RE = re.compile(r"^\[(\w+)\]\s+(.*)$")  # "[A1] text" -> ("A1", "text")
WORD_RE = re.compile(r"[a-z0-9]+")


def load_chunks():
    """Read each labeled paragraph as one chunk: {id, filename, text}."""
    chunks = []
    for filename in DOC_FILES:
        for line in (DOCS_DIR / filename).read_text(encoding="utf-8").splitlines():
            match = LABEL_RE.match(line.strip())
            if match:
                chunk_id, text = match.groups()
                chunks.append({"id": chunk_id, "filename": filename, "text": text})
    return chunks


def keywords(text):
    """Lowercase, extract alphanumeric words, drop stopwords; return a set."""
    return {word for word in WORD_RE.findall(text.lower()) if word not in STOPWORDS}


def score_chunks(question, chunks):
    """Score = number of distinct query keywords that also appear in the chunk."""
    query_words = keywords(question)
    results = []
    for chunk in chunks:
        matched = query_words & keywords(chunk["text"])  # label is not in text
        results.append({**chunk, "score": len(matched), "matched": sorted(matched)})
    return query_words, results


def rank(results):
    """Highest score first; ties broken by ascending chunk ID."""
    return sorted(results, key=lambda r: (-r["score"], r["id"]))


def main():
    parser = argparse.ArgumentParser(description="CEDAR-RAG keyword retriever")
    parser.add_argument("question", help="question to search for (quote it)")
    parser.add_argument("k", nargs="?", type=int, default=2,
                        help="max number of passages to select (default 2)")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("k must be a positive integer")

    chunks = load_chunks()
    query_words, results = score_chunks(args.question, chunks)
    ranked = rank(results)

    print(f"Question: {args.question}")
    print(f"Query keywords: {', '.join(sorted(query_words)) or '(none)'}")
    print(f"k = {args.k}")
    print()
    print("All scores (ranked):")
    for r in ranked:
        matched = ", ".join(r["matched"]) or "-"
        print(f"  {r['id']:<3} {r['filename']:<13} score={r['score']}  matched: {matched}")
    print()

    selected = [r for r in ranked if r["score"] > 0][: args.k]
    if not selected:
        print("No matching passages.")
        return

    print(f"Selected passages ({len(selected)}):")
    for r in selected:
        print(f"[{r['id']}] ({r['filename']}) {r['text']}")


if __name__ == "__main__":
    main()
