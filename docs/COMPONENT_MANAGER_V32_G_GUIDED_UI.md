# Component Manager v32-G Guided Local Components UI

## Purpose

v32-G adds the first guided GUI surface for local transcription readiness.

The screen does not duplicate readiness policy. It consumes the canonical result from `TranscriptionCapabilityResolver` through `WorkspaceViewModel` and presents:

- system summary
- recommended profile
- local component cards
- structured suggested actions
- onboarding shell
- advanced technical details on demand

## What the UI Shows

- whether the computer is ready now
- which profile is recommended
- which components are ready, missing, external, degraded, or incompatible
- whether GPU evidence is fresh or unverified
- whether local transcription can start now
- what the user can do next

## What the UI Does Not Do

- no network
- no product download sources
- no automatic downloads
- no automatic installation on open
- no automatic benchmark on startup
- no readiness decisions in widgets

## Startup Behavior

The main window appears first.

The onboarding shell is shown after startup bootstrap when the user has not completed or skipped it yet.

## State Persistence

The UI persists only presentation state:

- onboarding seen / completed / skipped
- last onboarding status
- local components advanced-details toggle
- transcription profile preference
- preferred transcription device

Component truth remains in the component manager and resolver.

## Current Limitations

- guided onboarding is a shell, not a full activation flow
- no product download sources are enabled
- no automatic installation is triggered from the screen
- advanced technical details remain optional and secondary
