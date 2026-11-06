# Optional supervised local worker on macOS

The ordinary development launcher already starts a worker. A launchd user agent
is an optional alternative for the same absolute data directory. It runs only
while the Mac is awake and the user session is available; it cannot recover
captures missed during downtime. This setup does not start the API or interface.

Generate a reviewable template from the repository root:

```sh
backend/.venv/bin/python scripts/macos_worker.py \
  --data-dir "$PWD/data" --output "$PWD/data/worker.launchd.plist"
plutil -lint "$PWD/data/worker.launchd.plist"
DATA_DIR="$PWD/data" backend/.venv/bin/python scripts/worker_status.py
```

For a research store, replace both data-directory arguments with that store's
absolute path. Generation creates only the template and its ignored log folder;
it does not install or start a service. Review the Python path, working directory,
DATA_DIR, explicit SQLite URL, and log paths in the plist. The template refuses
to overwrite a prior file. Generate a fresh filename after moving the repository
or replacing its environment.

Stop the launcher-owned worker before loading the optional service. Confirm the
existing worker's store from its startup environment; a missing heartbeat can
mean an older worker, so process inspection is still necessary. Use one worker
per intended store. Do not run the normal launcher and launchd worker together.

After reviewing the template, these are manual installation commands:

```sh
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PWD/data/worker.launchd.plist" "$HOME/Library/LaunchAgents/local.fpl.worker.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/local.fpl.worker.plist"
launchctl print "gui/$(id -u)/local.fpl.worker"
```

Inspect `DATA_DIR/runtime/logs/worker.stderr.log` for startup errors and rerun
`scripts/worker_status.py` with the same DATA_DIR. Its learning section shows
actual finality observations, finalized scoring, successful fit publication,
pending jobs, historical failures and the next action. Missing receipts remain
unknown. A heartbeat is stale after 90 seconds. The independent process pulse
continues during a long fit; pending jobs and expired leases are reported
separately. Normal lease recovery resumes queued work after a restart.

For a supervised restart or removal:

```sh
launchctl kickstart -k "gui/$(id -u)/local.fpl.worker"
launchctl bootout "gui/$(id -u)/local.fpl.worker"
```

`bootout` stops supervision. Remove the copied LaunchAgents plist manually if
you want to prevent loading it at a future login. The generated configuration
and source repository are unchanged. Logs can contain operational errors and
belong in ignored storage; do not add them to a source export.
