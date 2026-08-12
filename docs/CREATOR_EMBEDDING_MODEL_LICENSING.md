# Creator Embedding Model Licensing

## Candidate Evaluated

- repository: `intfloat/multilingual-e5-small`
- revision: `614241f622f53c4eeff9890bdc4f31cfecc418b3`
- license: `MIT`

## Scope

This document records the candidate embedding model evaluated for the local semantic retrieval foundation.

It does not claim the model is a shipped product component.

## Local Artifacts Used During Evaluation

The evaluation used the local ONNX candidate:

- `onnx/model_qint8_avx512_vnni.onnx`
- `tokenizer.json`
- `config.json`
- `tokenizer_config.json`

Local file sizes captured during evaluation:

- ONNX model: `118346824`
- tokenizer: `17082730`
- config: `655`
- tokenizer config: `443`
- total: `135430652`

Local SHA-256 values captured during evaluation:

- `model_qint8_avx512_vnni.onnx`: `DD476DD0C2514E9B9BE83AEB3853FAC0763E0BDF4A71645407587D77C48A2D88`
- `tokenizer.json`: `0B44A9D7B51C3C62626640CDA0E2C2F70FDACDC25BBBD68038369D14EBDF4C39`
- `config.json`: `69137736CAB8B8903A07FE8AFAAFDDA25AAC55415A12A55D1BFFA9F581ABF959`
- `tokenizer_config.json`: `A1D6BC8734A6F635DC158508BEF000F8E2E5A759C7D92F984B2C86E5FF53425B`

## Product Manifest Outcome

For product adoption, the universal CPU artifact is selected as the default managed asset:

- selected artifact: `onnx/model.onnx`
- selected artifact sha256: `ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665`
- selected artifact bytes: `470681649`

The AVX512/VNNI artifact remains an accelerator-specific variant:

- `onnx/model_qint8_avx512_vnni.onnx`
- sha256: `DD476DD0C2514E9B9BE83AEB3853FAC0763E0BDF4A71645407587D77C48A2D88`
- bytes: `118346824`

Required local files for offline embedding include:

- `onnx/model.onnx`
- `onnx/config.json`
- `onnx/tokenizer.json`
- `onnx/tokenizer_config.json`
- `onnx/special_tokens_map.json`
- `onnx/sentencepiece.bpe.model`

## Provenance

The model revision was obtained from Hugging Face primary metadata and validated locally with ONNX Runtime.

The repository had no upstream checksum source for the evaluation artifacts beyond revision identity, so the local hashes are qualification hashes, not upstream-published checksums.

## Legal Note

This document is not legal advice.

It records the observed license and evaluation provenance for later product review.
