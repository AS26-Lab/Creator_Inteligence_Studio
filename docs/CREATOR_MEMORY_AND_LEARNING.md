# Creator Memory And Learning

## Purpose

This document defines the approved memory, corpus, retrieval, and learning model for creator-specific intelligence.

## Corpus Strategy

By default, the application does not permanently duplicate MP4 files.

Persist:

- transcripts;
- timestamps;
- metadata;
- hashes;
- narrative structure;
- segments;
- results;
- metrics;
- titles;
- copy;
- captions;
- feedback;
- versions;
- corrections;
- embeddings;
- compressed thumbnails;
- essential frames;
- references to original files while they remain available.

Temporary artifacts:

- extracted audio;
- proxies;
- temporary frames;
- intermediate files.

Temporary artifacts should be removed after processing unless the user explicitly decides otherwise.

## Sample Classes

Samples are classified as:

1. Gold or authentic
2. Approved
3. Corrected
4. Rejected
5. External reference
6. Historical
7. Current

Never confuse:

- authentic content;
- generated content;
- corrected content;
- external content.

Everything is isolated by `creator_id`.

## Memory Dimensions

Retrieval and memory must consider:

- narrative segment;
- semantic segment;
- previous and next context;
- timestamps;
- platform;
- format;
- topic;
- date;
- authenticity;
- freshness;
- creative stage;
- provenance.

## Retrieval Priority

1. Recent authentic material
2. Historical authentic material that is still valid
3. Creator corrections
4. Approved material
5. Explicit Creator Memory rules
6. Own results and experiments
7. Universal knowledge
8. Anonymous collective patterns
9. External references
10. Unreviewed generated text

Rejected material works as a negative signal, not as a positive example.

## Creator Context Builder

The Creator Context Builder is a central future component.

Responsibilities:

- receive the task;
- receive `creator_id`;
- receive platform;
- receive format;
- receive objective;
- receive sensitivity;
- receive context budget;
- select allowed sources;
- retrieve examples;
- remove duplicates;
- preserve diversity;
- separate creative evidence from strategic evidence;
- enforce token budget;
- preserve critical constraints;
- record exactly what context was sent;
- support reproducibility.

## Embeddings And Search

Approved decisions:

- local embeddings;
- multilingual support;
- no third external provider;
- SQLite as the initial store;
- exact similarity computed in Python during MVP;
- replaceable interface for another vector store;
- hybrid retrieval with filters, text search, semantic search, and diversity;
- strict separation by `creator_id`;
- no mixing vectors from different models.

Benchmark candidates:

- BGE-M3
- Multilingual E5 Large Instruct

Only the winner remains installed.

Benchmark language and constraints:

- Mexican Spanish;
- humor;
- voice;
- narrative;
- strategy;
- negatives;
- filters.

## Learning From Corrections

Cycle:

context -> generation -> creator decision -> corrected version -> diff -> observation -> candidate pattern -> repeated pattern -> human confirmation -> active preference -> obsolete or replaced

Store:

- generated version;
- final version;
- context;
- provider;
- model;
- cost;
- latency;
- feedback;
- optional explanation;
- rewrite percentage;
- later result.

Do not convert an isolated correction into a rule.

Separate:

- creative preference;
- strategic performance.

## Quality Evaluation

Human evaluation is the primary authority.

Initial target:

- authenticity >= 7/10

Also track:

- rewrite magnitude;
- creative quality;
- strategic usefulness;
- constraint compliance;
- evidence strength;
- later results;
- blind OpenAI vs Anthropic comparisons;
- different winners by task;
- automatic judges as secondary signals only.

## Discrepancy Note

Current repository modules labeled memory or personalization are structural foundations. They are not yet the semantic retrieval layer described here.

