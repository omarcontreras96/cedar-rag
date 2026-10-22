# CEDAR-RAG

A small teaching project for the retrieval half of RAG. It uses a keyword
retriever built from Python's standard library. It does not generate answers yet.

> Cedar Lab is fictional. Its rules are classroom examples, not operational
> safety guidance.

## Layout

```
docs/access.txt     [A1], [A2]
docs/training.txt   [T1], [T2]
docs/booking.txt    [B1], [B2]
retrieve.py         keyword retriever (standard library only)
```

Each labeled paragraph is one chunk. The retriever stores its ID (`A1`) and
filename (`access.txt`) as metadata. Only the paragraph text is searched, never
the label.

## How it works

1. Lowercase the question and each chunk, extract `[a-z0-9]+` words, and remove
   the stopwords `a an the is are to of in at for and or may can i it be`.
2. A chunk's score is the number of distinct query words it shares with the question.
3. Rank chunks by descending score, breaking ties by ascending chunk ID.
4. Print all six scores, then up to `k` chunks with a positive score (default `k = 2`).
   If no chunk scores above zero, print `No matching passages.`

There is no stemming, no synonyms, and no semantic search. So `student` does not match
`students`, and `19:00` becomes the tokens `19` and `00`.

## Run

Run these from the `cedar-rag` directory. Any Python 3.8+ works, and no venv is needed.

```bash
python3 retrieve.py "May a trained graduate student operate the laser alone at 19:00?"
```

```bash
python3 retrieve.py "May a trained graduate student operate the laser alone at 19:00?" 3
```

```bash
python3 retrieve.py --help
```

## Embedding retriever

`embed_retrieve.py` encodes the same six passage texts with
`sentence-transformers/all-MiniLM-L6-v2` on the CPU, using `encode_document()`
for passages and `encode_query()` for questions. Both use `normalize_embeddings=True`.
It scores each passage with the dot product of the two unit-length vectors (cosine
similarity) over all 384 coordinates, and always returns the top `k` (default 2).
There is no relevance threshold. The passages are encoded once per run and reused for
every question. It needs the project venv. See `requirements-embedding.txt`.

```bash
.venv/bin/python embed_retrieve.py "May a trained graduate student operate the laser alone at 19:00?"
```

```bash
.venv/bin/python embed_retrieve.py "May a trained graduate student operate the laser alone at 19:00?" "How long can I book the laser room?" -k 3
```

Saved Q1 output: `evidence/embedding-inspection.txt`.

## Comparison runs (Q1–Q4, k = 2)

```bash
.venv/bin/python make_results.py
```

This writes `results.csv` (top-k IDs and scores for both methods; the judgement
columns are left blank). Saved output from the runs: `evidence/retrieval-runs.txt`,
`evidence/k-experiment.txt`. Inspection notes: `evidence/retrieval-notes.md`.

## Model and versions

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`, run on the CPU
- Python 3.14.8 (Homebrew, arm64 macOS)
- sentence-transformers 6.2.0
- torch 2.14.1
- transformers 5.20.2
- numpy 2.5.4

These pins are in `requirements-embedding.txt`. The folder is in iCloud Drive, so
the venv lives in `.venv.nosync` (iCloud skips it) with `.venv` as a symlink to
it. Set it up from the `cedar-rag` directory, with `python3` being Python 3.14.8:

```bash
python3 -m venv .venv.nosync
```

```bash
ln -s .venv.nosync .venv
```

```bash
.venv/bin/python -m pip install -r requirements-embedding.txt
```

The model weights are downloaded from the Hugging Face Hub on first use and cached.

## Evidence

- `evidence/embedding-inspection.txt`: full embedding-retriever output for Q1. It covers model and versions, matrix and vector shapes, the first 12 coordinates of each vector, lengths, all six scores, the cosine check, and the coordinate-product breakdown for the top passage.
- `evidence/retrieval-runs.txt`: actual output of the keyword and embedding retrievers for Q1–Q4 at k = 2.
- `evidence/k-experiment.txt`: Q1 embedding output at k = 1 and k = 3, with a table of selected IDs, A1/A2 presence, and coverage.
- `evidence/retrieval-notes.md`: inspection notes. It covers rankings, required-evidence coverage, paraphrase and no-answer behaviour, the cutoff discussion, and the k experiment.
- `evidence/answer-Q1.md`: the Q1 prompt sent to a fresh claude.ai chat with the embedding top-2 passages (A2, T1), the verbatim answer, and its audit.
- `evidence/answer-Q4.md`: the same for Q4 (passages T1, A2), with its audit.
- `results.csv`: one row per question with top-k IDs and scores for both methods, the required IDs, evidence-completeness judgements, and observations.

## Partners

Solo submission

## Reflections

This tool goes from a question to a cited answer not by answering from its knowledge implicit from its training, but on bringing the right information right into context. This process relies on having a corpus of information relevant to the questions at hand, the processing of that information into chunks that are embedded and compared to those embeddings of the question to be asked to the model, adding to context only the k most similar chunks of data.

In terms of failures during retrieval, I was surprised mostly by the embedding retriever missing A1 in Q1, where it ranked behind both T1 and B1.

If I had more than an hour, I would try to see if chunking the information differently (different lengths) would yield different results. I would like to see for example if A1 makes it into the top 2 for Q1.
