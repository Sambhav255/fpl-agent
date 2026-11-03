# Audit probes

These probes reproduce two behaviours in repository commit `e759bcfb299d3f818d2e80ebb017796874cf8019`: a missed two transfer funding plan and availability frozen across eight events. Inputs are synthetic.

Use the actual project environment, which already declares the required packages. From the project root, with this kit stored under `docs/intelligence_upgrade/`, run:

```sh
cd backend
uv run python ../docs/intelligence_upgrade/verification/audit_probes.py ..
```

The argument is the project root. The script imports its `backend/src` code. It writes a JSON result beside itself. It does not connect to FPL, change your team or modify the application database.

Recorded audit output shows Keep at 84, the best returned plan at 94, and the exhaustive legal plan at 101. All numbers describe this constructed case. After a successful search fix, the returned plan should match 101. The script prints evidence; port its assertions into the normal regression suite rather than treating it as a full test runner.

The original source was retrieved through GitHub at the pinned commit into a separate audit copy. Reproducing against a later branch measures that branch, which may already contain fixes. The historical audit commit recorded in the results is an evidence reference, not an automatic assertion that your current checkout is identical.
