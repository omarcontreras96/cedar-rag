"""Write results.csv: top-k IDs and scores for Q1-Q4 from both retrievers.

Judgement columns (evidence_complete, observation) are filled in by people, not
by this script: new rows get blanks, and values already in results.csv are kept.

Usage: .venv/bin/python make_results.py
"""

import csv
from pathlib import Path

from sentence_transformers import SentenceTransformer

import embed_retrieve
import retrieve

K = 2
QUESTIONS = [
    ("Q1", "May a trained graduate student operate the laser alone at 19:00?", "A1;A2"),
    ("Q2", "Can I use the laser without another person present?", "A2"),
    ("Q3", "How frequently must I refresh my laser qualification?", "T1"),
    ("Q4", "What is the laser wavelength?", "absent"),
]
COLUMNS = [
    "question_id", "keyword_top_ids", "keyword_scores", "embedding_top_ids",
    "embedding_scores", "required_ids", "keyword_evidence_complete",
    "embedding_evidence_complete", "observation",
]
JUDGEMENT_COLUMNS = ["keyword_evidence_complete", "embedding_evidence_complete", "observation"]
OUT = Path(__file__).parent / "results.csv"


def existing_judgements():
    """Judgement values already in results.csv, keyed by question_id."""
    if not OUT.exists():
        return {}
    with OUT.open(newline="", encoding="utf-8") as f:
        return {row["question_id"]: {c: row.get(c) or "" for c in JUDGEMENT_COLUMNS}
                for row in csv.DictReader(f)}


def main():
    judgements = existing_judgements()
    chunks = retrieve.load_chunks()
    model = SentenceTransformer(embed_retrieve.MODEL_NAME, device="cpu")
    D = embed_retrieve.encode_documents(model, chunks).astype("float64")  # once per run

    rows = []
    for qid, question, required in QUESTIONS:
        _, results = retrieve.score_chunks(question, chunks)
        kw = [r for r in retrieve.rank(results) if r["score"] > 0][:K]

        q = embed_retrieve.encode_question(model, question).astype("float64")
        scores = D @ q
        em = embed_retrieve.rank(chunks, scores)[:K]

        rows.append({
            "question_id": qid,
            "keyword_top_ids": ";".join(r["id"] for r in kw),
            "keyword_scores": ";".join(str(r["score"]) for r in kw),
            "embedding_top_ids": ";".join(chunks[i]["id"] for i in em),
            "embedding_scores": ";".join(f"{scores[i]:.6f}" for i in em),
            "required_ids": required,
            **judgements.get(qid, dict.fromkeys(JUDGEMENT_COLUMNS, "")),
        })

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(OUT.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
