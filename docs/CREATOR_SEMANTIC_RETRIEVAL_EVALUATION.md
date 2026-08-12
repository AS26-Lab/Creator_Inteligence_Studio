# Creator Semantic Retrieval Evaluation

## Baseline

The baseline is the existing creator-scoped lexical retrieval path.

It already provides:

- creator isolation
- current-version filtering
- provenance-preserving snippets
- bounded results
- deterministic ranking
- offline operation

## Evaluation Taxonomy

The local evaluation used four deterministic query classes:

1. exact lexical match
2. paraphrase
3. conceptual similarity
4. exact-match regression under semantic noise

## Synthetic Evaluation Summary

For the four-case synthetic set used in the local harness:

- lexical top-1 hit rate: `0.50`
- lexical top-5 recall: `0.50`
- semantic top-1 hit rate: `0.75`
- semantic top-5 recall: `1.00`
- hybrid top-1 hit rate: `1.00`
- hybrid top-5 recall: `1.00`

The semantic and hybrid paths improved paraphrase coverage without breaking the exact-match case.

## Operational Conclusion

The evaluation supports a local semantic foundation, but not an immediate production replacement.

Lexical retrieval remains the product baseline.

Future adoption should still require:

- a real semantic index lifecycle
- explicit product integration
- packaging review
- size and update impact review
- a production-grade scorer/index path, not only a synthetic harness
