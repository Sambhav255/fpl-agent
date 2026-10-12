# Verification scope

`latest_probes.py` imports the project's actual source. It does not fetch provider data or write manager state. The canonical copy now verifies the funding fix, conditional future availability, supported six-event replay and explicitly reconstructed historical timing. `replay_upgrade_probe_results.json` records this run; `latest_probe_results.json` preserves the original audit findings. Strict future-origin rejection and retained evidence mutation checks are in `backend/tests/test_replay_learning.py`.

Normal project environment, from repository root:

```bash
backend/.venv/bin/python docs/learning_upgrade/verification/latest_probes.py .
```

The audit runtime ran:

```bash
python docs/reference/supplied/fpl_learning_upgrade/verification/latest_probes.py repo_latest --minimal-storage
```

Only `fpl_app.storage.fingerprint` and `utcnow` were supplied locally because SQLAlchemy is absent. Contracts, rules, optimiser, oracle, baseline and replay were actual repository code. No database behavior was tested. `latest_probe_results.json` records this limitation and the reviewed commit. Remove the option when running through the full project environment.

The original supplied script is preserved under `docs/reference/supplied/fpl_learning_upgrade/verification/` as historical evidence. Its one-event-only input does not test supported six-event planning. The canonical regression uses a genuinely authored six-event forecast path. A present-day artifact is permitted only as explicitly labelled historical reconstruction; it is not prospective deployment evidence.

This is a read only audit probe, not an application test suite or training performance benchmark. Synthetic point differences must not appear in real team performance claims.
