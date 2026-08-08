# Component Manager v32-I Operation Recovery Hardening

## Purpose

v32-I hardens the lifecycle of local component operations after v32-H exposed explicit GUI actions.

The goal is not to add new product sources or new installation policy. The goal is to make interrupted work safe to resume or reconcile after restart.

## What v32-I Adds

- startup reconciliation for stale component-action tasks
- cooperative cancellation for safe benchmark work
- interruption recovery for local component actions
- bounded staging cleanup for managed component work
- heartbeat-style updates on background task state
- task-center reconciliation for canceling, cancelled, interrupted, and failed states
- preservation of the previous good installation when a mutation is interrupted

## What v32-I Does Not Add

- no productive internet sources
- no automatic download
- no automatic install
- no automatic benchmark
- no migration `v33`
- no PATH mutation
- no pip / conda / winget install path

## Recovery Policy

- download interruptions remain resumable through the existing download manager
- component-action tasks are reconciled to interrupted when the app restarts without a live worker
- benchmark cancellation is cooperative and only exposed when supported
- staging directories under managed roots are cleaned after reconciliation
- previous active installations remain canonical unless a terminal backend result says otherwise

## User-Facing Principle

The GUI should say what happened in plain language:

- Cancelando...
- Interrumpido
- Cancelado
- Reintentar
- Revisar componente

Technical details stay behind the advanced view.
