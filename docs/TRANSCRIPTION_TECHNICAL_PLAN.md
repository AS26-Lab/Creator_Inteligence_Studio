# Transcription Technical Plan

## Scope

This document defines the technical plan for the next phase: local transcription of normalized WAV audio with NVIDIA acceleration, CPU fallback, caching, and a modular engine boundary. No production code is changed here.

## Local diagnostic snapshot

The following values were gathered non-destructively on this machine.

| Item | Result | Notes |
| --- | --- | --- |
| Windows version | Windows 10 Pro 22H2, build 19045 | Local probes report Windows 10 Pro, not Windows 11. |
| Python version | 3.11.9 | From the virtual environment. |
| Python architecture | 64-bit | `platform.architecture()` and pointer size agree. |
| Python interpreter | `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Scripts\python.exe` | Active venv interpreter. |
| pip version | 25.1.1 | Installed in the venv. |
| GPU | NVIDIA GeForce RTX 2080 | Detected by `nvidia-smi`. |
| VRAM total | 8192 MiB | From `nvidia-smi`. |
| VRAM in use at probe time | 5368 MiB | Desktop apps were already consuming VRAM. |
| NVIDIA driver | 576.52 | Functional. |
| CUDA reported by driver | 12.9 | This is driver-reported CUDA, not the Toolkit. |
| `nvidia-smi` summary | GPU visible, WDDM mode, default compute mode | The driver is working. |
| Maximum CUDA version reported by driver | 12.9 | From `nvidia-smi`. |
| CUDA Toolkit installed | Not detected | No `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA` path present. |
| `nvcc` available | No | Not found on PATH. |
| cuDNN detectable | No | No standard cuDNN install path detected. |
| PyTorch installed | No | `pip show torch` returned not installed. |
| Whisper packages installed | No | `whisper`, `openai-whisper`, `faster-whisper` not installed. |
| CTranslate2 installed | No | Not installed. |
| Transformers installed | No | Not installed. |
| Free RAM | 4.17 GB available, 32.27 GB total | Measured with `GlobalMemoryStatusEx`. |
| Free disk on `H:\` | 1.23 TB | Measured with `shutil.disk_usage`. |
| RTX 2080 compute capability | 7.5 | From NVIDIA compute capability table. |

### Diagnostic interpretation

- The machine is ready for local GPU transcription work, but it is currently VRAM-constrained because other desktop applications are using roughly 5.4 GiB.
- The NVIDIA driver reports CUDA 12.9, but the CUDA Toolkit is not installed locally.
- `torch.cuda.is_available()` cannot be checked yet because PyTorch is not installed.
- The local environment is compatible with a CUDA-first plan, but model choice must stay conservative because the card has 8 GB of VRAM and several gigabytes are already occupied at idle.

## Engine comparison

All speed and memory statements below are estimates unless explicitly sourced. No local benchmarks were run in this phase.

| Engine | Windows | Python 3.11 | CUDA support | Install effort | Timestamps | Word timestamps | Language detection | Spanish | Caching | Packaging | Maintenance | Fit for RTX 2080 8 GB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `faster-whisper` + CTranslate2 | Yes | Yes, Python >= 3.9 | Yes, via CUDA 12.x + cuDNN. Latest `faster-whisper` README says CUDA 12 and cuDNN 9 are required for GPU execution. | Moderate | Yes, segment timestamps | Yes | Yes | Yes | Yes, local HF cache / model directory | Moderate | Active | Best overall fit |
| `openai-whisper` + PyTorch | Yes | Yes, repo states compatibility with Python 3.8-3.11 | Yes, through a CUDA-enabled PyTorch wheel | Higher | Yes | Yes, via `word_timestamps` | Yes | Yes | Yes, Whisper cache in `~/.cache/whisper` | Heavy | Mature baseline | Usable, but heavier and slower |
| `transformers` Whisper | Yes | Yes in current releases and wheels, but verify selected wheel set | Yes, through PyTorch | High | Yes | Yes, token timestamps can be converted to word timestamps | Yes | Yes | Yes, Hugging Face cache | Heavy | Very active | Usable, but overkill for first phase |
| `whisper.cpp` | Yes | Runtime does not require Python | Yes, via `GGML_CUDA` build; also CPU-only | Moderate to high | Yes | Experimental / less first-class than the Python stacks | Not the core focus of the current Python stack | Yes | Yes, local ggml model files | Native binary build | Active | Strong fallback / escape hatch |

### Engine notes

- `faster-whisper` is the best CUDA-first fit for this project because it is Python-friendly, local, modular, and has explicit support for segment and word timestamps.
- `openai-whisper` is the best reference baseline if we want to compare semantic output against the original Whisper behavior.
- `transformers` is the most flexible if the future plan expands to multiple ASR tasks, but it adds weight and complexity without a clear benefit for this first transcription phase.
- `whisper.cpp` is a credible alternative if we later want a compact native binary runtime or a non-Python deployment path. For this app, it is better as a contingency path than as the primary engine.

## Model comparison

The OpenAI model card gives approximate VRAM for the base Whisper models. Those values are useful as a ceiling reference, but actual memory use depends on the engine and compute type. `faster-whisper` with quantization can use less VRAM than the original PyTorch stack.

| Model | Approx VRAM from official model card | Fits 8 GB? | Speed | Precision | Spanish suitability | Recommended use |
| --- | --- | --- | --- | --- | --- | --- |
| `tiny` | ~1 GB | Yes | Fastest | Lowest | Okay for smoke tests only | Tests / diagnostics |
| `base` | ~1 GB | Yes | Very fast | Low to medium | Acceptable for quick previews | Fast mode / QA |
| `small` | ~2 GB | Yes | Fast | Good | Good balance for Spanish | Default development model |
| `medium` | ~5 GB | Probably, with CUDA quantization and careful headroom | Moderate | Better | Strong choice for Spanish quality | Quality mode |
| `large` / `large-v3` | ~10 GB | No, not comfortably on 8 GB | Slowest | Best among standard Whisper models | Strong, but too heavy here | Not recommended as default |
| `turbo` | ~6 GB | Maybe, but tight on this GPU | Faster than large | Good, but model-specific tradeoffs apply | Good candidate if verified later | Possible quality candidate, not first choice |

### Model recommendation for this machine

- Initial development model: `small`
- Fast mode model: `base` or `small` depending on quality tolerance
- Quality mode model: `medium`
- Large-class models: defer until a later phase or a larger GPU

## Recommended decision

1. Main engine: `faster-whisper` with CTranslate2.
2. Alternate engine: `openai-whisper` with PyTorch, as a baseline comparator and emergency fallback.
3. Initial development model: `small`.
4. Fast mode model: `base` if latency matters most, otherwise `small`.
5. Quality mode model: `medium`.
6. Compute type: `int8_float16` on CUDA, `int8` on CPU fallback.
7. CUDA strategy: use the NVIDIA driver plus the runtime libraries required by the selected engine; do not depend on a system-wide Toolkit for the first phase.
8. CPU fallback: `int8` inference with bounded threads and chunked processing.
9. Cache strategy: cache model files separately from transcription results; key transcriptions by video/audio fingerprint plus engine, model, compute type, language, and version.
10. Long-file strategy: process normalized WAV in bounded chunks and preserve absolute timestamps; do not load unbounded audio into GPU memory in one pass.
11. VRAM safety strategy: start with `small`, use `int8_float16`, cap batch size at 1, release GPU memory between jobs, and keep the pipeline resumable by chunk.
12. Next-mission installs: `faster-whisper`, its compatible `ctranslate2`, and the CUDA/cuDNN runtime pieces required by the chosen wheel set.
13. Do not install globally: PyTorch, full CUDA Toolkit, cuDNN as a manual system-wide dependency unless a later native build truly needs it, transformers, diarization stacks, or extra ASR engines.
14. CUDA Toolkit need: not required for runtime if the selected wheel stack supplies the GPU runtime; required only if we later compile a native CUDA engine such as `whisper.cpp` with CUDA support or a custom build.
15. GPU verification after install: confirm the backend at runtime, then watch `nvidia-smi` for VRAM growth and GPU utilization during a real transcription job.

## Proposed architecture

```
domain/
    transcription/

application/
    services/
        transcription_service.py

infrastructure/
    transcription/
        engine.py
        faster_whisper_engine.py
        model_manager.py
        device_detector.py
```

### Suggested interfaces

#### Application service

- `transcribe(video_id, options)`
- `get_transcription(video_id)`
- `is_transcription_stale(video_id)`
- `cancel_transcription(video_id)`
- `list_available_models()`
- `verify_transcription_backend()`

#### Engine boundary

- `engine.transcribe(audio_path, options) -> TranscriptionResult`
- `engine.verify() -> BackendHealth`
- `engine.list_models() -> list[ModelInfo]`

#### Result shape

- `language_detected`
- `language_confidence` or `probability`
- `full_text`
- `segments`
- `segment.start`
- `segment.end`
- `segment.text`
- `segment.words` optional
- `duration_processed`
- `engine`
- `model`
- `device`
- `compute_type`
- `runtime_seconds`
- `model_version`
- `warnings`
- `errors`

### Domain boundaries

- The domain should own the transcription state model and the selection rules for stale detection.
- The application service should orchestrate job state, caching, engine selection, and error mapping.
- The infrastructure layer should own engine-specific calls, model loading, device detection, and file system interactions.

## Future persistence plan

Proposed tables for a later migration:

### `transcription_jobs`

- Job lifecycle and orchestration data.
- Suggested columns: `id`, `video_asset_id`, `status`, `requested_at`, `started_at`, `completed_at`, `canceled_at`, `engine`, `model`, `device`, `compute_type`, `options_json`, `error_code`, `error_message`.

### `transcriptions`

- One logical transcription per video and engine/configuration combination.
- Suggested columns: `id`, `video_asset_id`, `source_audio_asset_id`, `language`, `language_confidence`, `full_text`, `segment_count`, `duration_processed`, `engine`, `model`, `device`, `compute_type`, `runtime_seconds`, `model_version`, `cache_version`, `stale_reason`, `created_at`, `updated_at`.

### `transcription_segments`

- Recommended as a structured table.
- Good for ordering, seeking, and UI display.
- Suggested columns: `id`, `transcription_id`, `segment_index`, `start_seconds`, `end_seconds`, `text`, `avg_logprob`, `no_speech_prob`, `words_json` optional, `raw_json` optional.

### `transcription_words`

- Only worth a separate table if word-level search, editing, or clickable word navigation becomes a product requirement.
- For the first phase, keep words in JSON inside the segment row or omit them entirely if the selected engine does not provide stable word timestamps.

### `transcription_models`

- Track installed or cached model artifacts.
- Suggested columns: `id`, `engine`, `model_name`, `source`, `local_path`, `size_bytes`, `sha256`, `version`, `downloaded_at`, `last_used_at`, `health_status`.

### Structured vs JSON

- Store structured fields that are filtered, sorted, or joined by the UI: job status, transcript metadata, segment boundaries, engine/model/device, runtime, language, and stale state.
- Store engine-specific or diagnostic payloads in JSON: raw options, raw backend info, optional word arrays, and vendor-specific diagnostics.
- Keep the full transcript text denormalized in a top-level field for search and copy operations.

## Future CLI and GUI integration

### CLI

- `audio` and `media` remain separate; transcription should become its own top-level command group.
- Suggested commands:
  - `transcription model-status --model ...`
  - `transcription download-model --model ...`
  - `transcription verify-model --model ...`
  - `transcription transcribe --video-id ...`
  - `transcription show --video-id ...`
  - `transcription verify --video-id ...`
  - `transcription cancel --video-id ...`
  - `transcription clear-cache --video-id ...`
  - `transcription models`

### GUI

In the Videos screen:

- Add `Transcribir` and `Regenerar transcripcion` actions.
- Add a model selector.
- Add a mode selector: `Rapido`, `Equilibrado`, `Calidad`.
- Add language mode: `Auto` or manual selection.
- Add progress and cancel controls.
- Show state, engine, model, compute type, and stale status.
- Show the full transcript in a read-only panel.
- Show a segment table with clickable timestamps.
- Add copy-to-clipboard and export actions for TXT, SRT, and JSON.
- Keep the audio and transcription states visually distinct so users do not confuse preparation with transcription.

## Pilot benchmark plan

For the next phase, run a pilot on a temporary short WAV only:

- Duration: 30 to 90 seconds.
- Language: Spanish.
- Content: moderate noise, but synthetic or temporary only.
- Measure:
  - wall-clock time;
  - peak VRAM used;
  - GPU vs CPU device actually used;
  - detected language and confidence;
  - text output;
  - segment count;
  - qualitative correctness;
  - cache hit vs cache miss behavior.
- Compare CUDA vs CPU only if the GPU path is already stable and the CPU comparison does not add unnecessary cost.

## Risks

- RTX 2080 has only 8 GB of VRAM, and this machine already has significant GPU memory usage at idle.
- Windows package compatibility can drift between `faster-whisper`, `ctranslate2`, `torch`, and NVIDIA runtime packages.
- CUDA reported by the driver does not mean the Toolkit is installed.
- The first engine choice should minimize moving parts and make fallback behavior deterministic.
- Very large Whisper models are not a good default for this card.
- Long-file processing should be chunked to avoid VRAM spikes and to keep job cancellation responsive.

## Rollback plan

- No production code is changed in this phase, so rollback is trivial: delete this planning document if needed.
- For the implementation phase, keep transcription code behind a single application service and a single engine interface so the backend can be swapped without touching the UI or persistence schema.
- If CUDA proves unstable on this card, fall back to CPU `int8` before changing the user-facing workflow.

## Commands executed and summarized results

### Local diagnostics

- `python -m pip --version` -> pip 25.1.1 in the active venv.
- `.venv\Scripts\python.exe` runtime probe -> Python 3.11.9, 64-bit, interpreter at `H:\ALEJANDRO_2\CreatorIntelligenceStudio\.venv\Scripts\python.exe`.
- `nvidia-smi` -> RTX 2080, driver 576.52, CUDA 12.9 reported, 8192 MiB VRAM, 5368 MiB used at probe time.
- Registry probes -> Windows 10 Pro, 22H2, build 19045.
- `GlobalMemoryStatusEx` -> 32.27 GB total RAM, 4.17 GB available.
- `shutil.disk_usage('H:\\')` -> 1.23 TB free.
- `Get-Command nvcc` -> not found.
- `Test-Path` for `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA` and `C:\Program Files\NVIDIA\CUDNN` -> false.
- Python package probes -> `torch`, `whisper`, `openai-whisper`, `ctranslate2`, `transformers`, `faster-whisper` not installed.

### Research sources used

- [OpenAI Whisper README](https://github.com/openai/whisper)
- [OpenAI Whisper model card](https://github.com/openai/whisper/blob/main/model-card.md)
- [OpenAI Whisper transcribe implementation](https://github.com/openai/whisper/blob/main/whisper/transcribe.py)
- [faster-whisper README](https://github.com/SYSTRAN/faster-whisper)
- [faster-whisper transcription code](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
- [CTranslate2 installation docs](https://opennmt.net/CTranslate2/installation.html)
- [Transformers Whisper docs](https://huggingface.co/docs/transformers/en/model_doc/whisper)
- [Transformers Whisper generation code](https://github.com/huggingface/transformers/blob/main/src/transformers/models/whisper/generation_whisper.py)
- [Whisper.cpp README](https://github.com/ggml-org/whisper.cpp/blob/master/README.md)
- [NVIDIA CUDA Windows installation guide](https://docs.nvidia.com/cuda/archive/12.9.0/cuda-installation-guide-microsoft-windows/index.html)
- [NVIDIA cuDNN Windows installation docs](https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html)
- [NVIDIA GPU compute capability table](https://developer.nvidia.com/cuda/gpus?source=post_page-----20244437e036---------------------------------------)

## Acceptance criteria for the next phase

- The engine can transcribe a normalized WAV without installing a full system-wide CUDA Toolkit.
- The chosen model fits the RTX 2080 VRAM budget with enough headroom for 10 to 20 minute clips.
- The UI and CLI can show transcript text, segments, and stale state.
- CUDA use can be verified by runtime logs and GPU telemetry.
- CPU fallback works deterministically with the same transcript schema.

## Estado de Implementacion

La fase de planificacion ya fue materializada.
El backend formal usa `faster-whisper` + `CTranslate2`, runtimes NVIDIA oficiales dentro de `.venv`, cache de modelos local y GUI/CLI integradas.
