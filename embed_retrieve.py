"""CEDAR-RAG embedding retriever: all-MiniLM-L6-v2 on the CPU, scored with numpy.

Cedar Lab is fictional; its rules are classroom examples, not safety guidance.

Usage: .venv/bin/python embed_retrieve.py "QUESTION" ["QUESTION" ...] [-k K]
"""

import argparse
import platform

import numpy as np
import sentence_transformers
import torch
import transformers
from sentence_transformers import SentenceTransformer

from retrieve import load_chunks  # same six chunks as the keyword retriever

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SHOW = 12     # coordinates displayed per vector (retrieval uses all of them)
TOL = 1e-5    # numerical tolerance for "approximately equal"


def fmt(values):
    """Format numbers to four decimals for display only."""
    return "[" + ", ".join(f"{v:+.4f}" for v in values) + "]"


def encode_documents(model, chunks):
    """Encode passage text only; IDs and filenames stay in the chunk metadata."""
    texts = [chunk["text"] for chunk in chunks]
    return model.encode_document(texts, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)


def encode_question(model, question):
    return model.encode_query(question, normalize_embeddings=True,
                              convert_to_numpy=True, show_progress_bar=False)


def rank(chunks, scores):
    """Indices ordered by descending score; ties broken by ascending chunk ID."""
    return sorted(range(len(chunks)), key=lambda i: (-scores[i], chunks[i]["id"]))


def main():
    parser = argparse.ArgumentParser(description="CEDAR-RAG embedding retriever")
    parser.add_argument("questions", nargs="+", help="one or more questions (quote each)")
    parser.add_argument("-k", type=int, default=2, help="passages to select (default 2)")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("k must be a positive integer")

    print("=== Setup ===")
    print(f"Model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, device="cpu")
    print(f"Device: {model.device}")
    print(f"Python {platform.python_version()} | sentence-transformers {sentence_transformers.__version__}"
          f" | torch {torch.__version__} | transformers {transformers.__version__} | numpy {np.__version__}")

    # Encode the six passages once per run; every question below reuses this matrix.
    chunks = load_chunks()
    doc_vecs = encode_documents(model, chunks)
    D = doc_vecs.astype(np.float64)  # full precision for all arithmetic
    dim = D.shape[1]
    print(f"Document matrix shape: {doc_vecs.shape} (dtype {doc_vecs.dtype})")
    print(f"Retrieval uses all {dim} coordinates of every vector; only the first {SHOW} are displayed.")
    print()

    doc_lengths = np.linalg.norm(D, axis=1)
    print(f"=== Document vectors (first {SHOW} of {dim} coordinates) ===")
    for chunk, vec, length in zip(chunks, D, doc_lengths):
        print(f"{chunk['id']} ({chunk['filename']}) length={length:.6f}")
        print(f"    {fmt(vec[:SHOW])}")
    ok = np.allclose(doc_lengths, 1.0, atol=TOL)
    print(f"All document lengths within {TOL:g} of 1: {ok} "
          f"(max |length - 1| = {np.max(np.abs(doc_lengths - 1)):.2e})")

    for n, question in enumerate(args.questions, start=1):
        print()
        print(f"=== Question {n} ===")
        print(f"Question: {question}")
        q_vec = encode_question(model, question)
        q = q_vec.astype(np.float64)
        q_length = np.linalg.norm(q)
        print(f"Question vector shape: {q_vec.shape} (dtype {q_vec.dtype})")
        print(f"Question vector length={q_length:.6f}; within {TOL:g} of 1: "
              f"{bool(abs(q_length - 1) <= TOL)}")
        print(f"    {fmt(q[:SHOW])}")

        # Similarity: dot product of the normalized question with each normalized passage.
        scores = D @ q
        order = rank(chunks, scores)

        print()
        print(f"All scores (dot product over {dim} coordinates, ranked):")
        for i in order:
            print(f"  {chunks[i]['id']:<3} {chunks[i]['filename']:<13} score={scores[i]:.6f}")

        # Independent check: cosine = dot / (|q| * |d|) using the measured lengths.
        cosines = scores / (q_length * doc_lengths)
        max_diff = np.max(np.abs(cosines - scores))
        print(f"Cosine check: max |cosine - dot| = {max_diff:.2e}; agree within {TOL:g}: "
              f"{bool(max_diff <= TOL)}")

        print()
        selected = order[: args.k]
        print(f"Selected passages (top k = {args.k}):")
        for i in selected:
            print(f"[{chunks[i]['id']}] ({chunks[i]['filename']}) {chunks[i]['text']}")

        top = order[0]
        products = q * D[top]
        head = products[:SHOW].sum()
        tail = products[SHOW:].sum()
        print()
        print(f"Breakdown for top passage {chunks[top]['id']}: question[i] x document[i]")
        for i in range(SHOW):
            print(f"  i={i:<3} {q[i]:+.4f} x {D[top][i]:+.4f} = {products[i]:+.4f}")
        print(f"  {f'Subtotal, coordinates 0-{SHOW - 1} ({SHOW} terms):':<48}{head:+.6f}")
        print(f"  {f'Subtotal, coordinates {SHOW}-{dim - 1} ({dim - SHOW} terms):':<48}{tail:+.6f}")
        print(f"  {'Full similarity (sum of both subtotals):':<48}{head + tail:+.6f}")
        print(f"  Matches ranked score {scores[top]:.6f}: "
              f"{bool(abs((head + tail) - scores[top]) <= TOL)}")


if __name__ == "__main__":
    main()
