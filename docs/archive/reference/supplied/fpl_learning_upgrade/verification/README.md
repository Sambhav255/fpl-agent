# Verification scope

`latest_probes.py` imports the supplied project's actual source. It does not fetch provider data or write manager state. It reproduces the funding fix, conditional future availability, one event replay override and absent strict prediction origin check.

Normal project environment, from repository root after copying this package to `docs/learning_upgrade`:

```bash
backend/.venv/bin/python docs/learning_upgrade/verification/latest_probes.py .
```

The audit runtime ran:

```bash
python fpl_learning_upgrade/verification/latest_probes.py repo_latest --minimal-storage
```

Only `fpl_app.storage.fingerprint` and `utcnow` were supplied locally because SQLAlchemy is absent. Contracts, rules, optimiser, oracle, baseline and replay were actual repository code. No database behavior was tested. `latest_probe_results.json` records this limitation and the reviewed commit. Remove the option when running through the full project environment.

The script asserts the reviewed behavior, including known limitations. After implementing replay corrections, update or replace these checks with regression tests that assert the corrected behavior. Do not preserve an accepted future origin just to keep this historical audit script green.

This is a read only audit probe, not an application test suite or training performance benchmark. Synthetic point differences must not appear in real team performance claims.
