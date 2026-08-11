# Creator Memory And Learning

## Purpose

This document defines the approved memory, corpus, retrieval, and learning model for creator-specific intelligence.
v33-A now implements the local Creator Corpus foundation for identity, provenance, ingestion, deduplication, versioning, and lifecycle. Retrieval and embeddings remain future layers.

## Corpus Strategy

By default, the application does not permanently duplicate MP4 files.

Persist:

- corpus source assets;
- corpus documents;
- document versions;
- provenance edges;
- transcript segments;
- raw content;
- normalized content;
- timestamps;
- metadata;
- hashes;
- titles;
- captions;
- notes;
- script text;
- imported plain text;
- corpus-quality flags;
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

## Corpus Ingestion Reality

The current corpus implementation now distinguishes:

- raw content vs normalized content;
- creator-authored vs transcribed vs AI-generated content;
- retrieval eligibility vs voice-learning eligibility;
- source-asset identity vs document-version identity.

The ingestion layer is still local-only and does not send corpus text to OpenAI, Anthropic, Supabase, Hugging Face, or any other remote service.

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

Important current reality:

- embeddings are still not implemented in the running corpus layer;
- retrieval remains a future phase;
- the corpus now only stores eligibility metadata for that future work.

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

Current repository modules labeled memory, personalization, or corpus are structural foundations. The corpus foundation is now implemented locally, but it is still not the semantic retrieval layer described here.
