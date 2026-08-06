# AI Runtime Test Timing Report

This report records the timing observed during the v32-A work session. It is intended as a reproducible summary of what was run and how long the suite took in this workspace.

## Commands and Observed Duration

| Command | Outcome | Observed duration |
|---|---|---:|
| `python -m unittest -v tests.test_component_manager_migration tests.test_component_manager_contracts tests.test_component_manager_cli tests.test_transcription_no_hidden_download tests.test_transcription_service tests.test_paths tests.test_bootstrap` | passed | 76.637 s |
| `python -m unittest -v tests.test_ai_runtime_providers` | passed | 0.011 s |
| `python -m unittest -v tests.test_ai_runtime_orchestrator` | timed out | 124 s |
| `python -m unittest -v tests.test_ai_runtime_gui` | timed out | 124 s |
| `python -m unittest -v tests.test_ai_runtime_model_selection` | timed out | 124 s |
| `python -m unittest -v tests.test_ai_runtime_guided_configuration` | timed out | 124 s |
| `python -m unittest discover -v -s tests -p "test_ai_runtime_*.py"` | timed out | 124 s |

## Notes

- The long AI Runtime suites were attempted individually and as a discover run, but the execution window expired before completion.
- The timeout did not come from the v32-A component foundation code; the component foundation suites passed locally.
- The workspace still needs a longer uninterrupted run if a full AI Runtime timing profile is required.

