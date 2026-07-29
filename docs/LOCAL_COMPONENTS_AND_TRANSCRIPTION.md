# Local Components And Transcription

## Purpose

This document defines the local component strategy, installation assumptions, and transcription baseline.

## Component Manager

The user does not install Python manually, use `pip`, or download models by hand.

The application should manage components when it is legally and technically possible.

Required behavior:

- versioned components;
- hashes;
- licenses;
- resumable downloads;
- rollback;
- repair;
- folder relocation;
- CPU support;
- NVIDIA acceleration when compatible;
- built-in FFmpeg distribution with reviewed version and license;
- large models downloaded from inside the application.

## Onboarding

The base app must not pretend to be fully configured.

First run should include:

- setup assistant;
- install recommended button;
- clearly marked limited mode;
- per-component explanations for what it enables and blocks;
- size, location, available space, estimated time, and status;
- visible dashboard warnings;
- blocked functions that offer to install the missing component;
- `Settings -> Local Components`.

## Transcription Stack

Approved candidate stack:

- `faster-whisper`;
- `large-v3-turbo` for balanced mode;
- `large-v3` for maximum quality and doubtful segments;
- CPU INT8;
- GPU FP16 or INT8-FP16 depending on hardware;
- OpenAI as an authorized remote fallback;
- optional diarization.

## Modes

- fast;
- balanced, default;
- maximum quality.

Target behavior for a 10 minute video:

- fast: about 2 to 5 minutes;
- balanced: about 5 to 10 minutes;
- maximum quality: about 10 to 20 minutes;
- several hours is not commercially acceptable.

Use selective reprocessing instead of retranscribing everything.

## Benchmark Requirements

Benchmark with:

- Mexican Spanish;
- idioms;
- profanity;
- gaming speech;
- proper names;
- music;
- multiple voices;
- personal glossary;
- doubtful segments;
- hallucination detection;
- per-segment confidence.

The benchmark must use real CUDA performance, not only `nvidia-smi`.

## Existing Implementation Reality

The repository already includes transcription commands, model status, download, verification, export, and delete flows. That is an operational foundation, but not yet the AI catch-up layer.

