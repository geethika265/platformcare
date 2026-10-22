# AI-assisted development and critical review

Codex was used during implementation and verification. These examples describe changes observed during this project's testing; they are not evidence that the owner has already mastered or independently reviewed every line. Before discussing them in an interview, reproduce the relevant test and explain the code yourself.

| Observed issue | Reviewed change | Evidence |
| --- | --- | --- |
| A model could spend its final investigation round on a tool and never synthesize a response | Reserve a final synthesis step after the bounded tool budget | `platformcare/agent.py`, `tests/test_agent_live_contract.py`, Stage 3 verification |
| No successful history could be described as an available previous output | Tighten prompt/runbook instructions and test the missing-history case | `runbooks/validation.md`, live missing-history smoke report described in `VERIFICATION.md` |
| Long Slack answers could lose evidence or exceed section limits | Split responses into bounded sections while preserving evidence and next steps | `platformcare/slack_bot.py`, `tests/test_slack_bot.py` |
| The operational API imported model dependencies even when only running a pipeline | Load the agent inside the support endpoint | `platformcare/api.py`, actual isolated Airflow executions |

The optional service adapters also have contract tests that reject cross-origin pagination, validate acknowledgments/results, and preserve a PagerDuty dedup key between trigger and resolve. Fake-transport tests do not establish compatibility with a live vendor deployment.

## Owner review exercise

Choose one example. Read the implementation and regression test, explain the original failure, and show how the assertion would detect it again. Record your own explanation or review notes after doing the exercise. Using Codex is relevant AI-assisted tooling experience; claiming Claude Code use would be inaccurate unless you actually use it.
