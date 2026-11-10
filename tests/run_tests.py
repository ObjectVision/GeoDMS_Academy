"""Load every configuration of the GeoDMS Academy in GeoDMS, calculate its items and report what fails.

Run it after every new GeoDMS release, before the Academy refers to that release:

    python tests/run_tests.py
    python tests/run_tests.py --geodms "C:/Program Files/ObjectVision/GeoDms20.26.0.m"
    python tests/run_tests.py --only networks --source-data-dir D:/SourceData

The configurations and the number of errors each is expected to give are in configurations.csv.
Each configuration runs in its own process (walk_tree.py), so a crash of the engine stops only
that configuration. The script writes a tsv per configuration and summary.txt to the output
folder, and ends with exit code 1 if a configuration gives another number of errors than expected.
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
ERROR_KINDS = ("LOADFAIL", "META", "CALC")


def newest_geodms():
    """The installed GeoDMS folder with the highest version number."""
    found = []
    for d in Path("C:/Program Files/ObjectVision").glob("GeoDms*"):
        m = re.match(r"GeoDms(\d+)\.(\d+)\.(\d+)", d.name)
        if m and (d / "GeoDmsRun.exe").exists():
            found.append((tuple(int(x) for x in m.groups()), d))
    if not found:
        sys.exit("No GeoDMS found in C:/Program Files/ObjectVision; give the folder with --geodms.")
    return max(found)[1]


def expand(geodms, text, env):
    """Fill in a placeholder such as %SourceDataDir% the way GeoDMS does."""
    r = subprocess.run([sys.executable, str(TESTS / "walk_tree.py"), str(geodms), "--expand", text],
                       env=env, capture_output=True, text=True, timeout=120)
    lines = [l for l in r.stdout.splitlines() if l and not l.startswith("[geodms]")]
    return lines[-1] if lines else ""


def count(tsv):
    """Number of errors, and whether the run ended normally and within its time limit."""
    errors, done, budget, first = 0, False, False, ""
    if tsv.exists():
        for line in tsv.read_text(encoding="utf-8").splitlines():
            kind, item, _, msg = (line.split("\t") + ["", "", "", ""])[:4]
            if kind in ERROR_KINDS:
                errors += 1
                first = first or f"{item}: {msg}"
            done |= kind == "DONE"
            budget |= kind == "BUDGET"
    return errors, done, budget, first


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--geodms", help="GeoDMS folder; default the newest one installed")
    p.add_argument("--source-data-dir", help="folder to use as %%SourceDataDir%%, instead of the one in the GeoDMS settings")
    p.add_argument("--local-data-dir", help="folder to use as %%LocalDataDir%%, instead of the one in the GeoDMS settings")
    p.add_argument("--only", help="test only the configurations whose path contains this text")
    p.add_argument("--budget", type=float, default=300, help="seconds per configuration for calculating items (default 300)")
    p.add_argument("--out", default=str(TESTS / "results"), help="output folder (default tests/results)")
    a = p.parse_args()

    geodms = Path(a.geodms) if a.geodms else newest_geodms()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if a.source_data_dir:
        env["GEODMS_directories_SourceDataDir"] = a.source_data_dir.replace("\\", "/")
    if a.local_data_dir:
        env["GEODMS_directories_LocalDataDir"] = a.local_data_dir.replace("\\", "/")
    source_data_dir = expand(geodms, "%SourceDataDir%", env)
    if not source_data_dir:
        pyds = ", ".join(sorted(x.name for x in geodms.glob("geodms*.pyd"))) or "none"
        sys.exit(f"The GeoDMS Python binding does not load in Python {sys.version.split()[0]}. "
                 f"Use a Python version that matches one of the bindings in {geodms}: {pyds}.")
    print(f"GeoDMS {geodms}\nSourceDataDir {source_data_dir}\n")

    with open(TESTS / "configurations.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if a.only:
        rows = [r for r in rows if a.only in r["config"]]

    lines, failed = [], 0
    for r in rows:
        cfg = (REPO / r["config"]).resolve()
        expected = int(r["expected_errors"])
        if not cfg.exists():
            status, detail = "SKIP", "configuration not found; is the repository checked out next to this one?"
        elif r["needs"] and not Path(source_data_dir, r["needs"]).exists():
            status, detail = "SKIP", f"source data not found in {source_data_dir}/{r['needs']}"
        else:
            tsv = out / (re.sub(r"[^A-Za-z0-9]+", "_", r["config"]).strip("_") + ".tsv")
            t = time.time()
            try:
                subprocess.run([sys.executable, str(TESTS / "walk_tree.py"), str(geodms), str(cfg), str(tsv), r["mode"], str(a.budget)],
                               env=env, capture_output=True, timeout=a.budget * 3 + 600)
            except subprocess.TimeoutExpired:
                pass
            errors, done, budget, first = count(tsv)
            secs = time.time() - t
            if not done:
                status, detail = "FAIL", f"stopped before the end (crash or time-out); last lines in {tsv.name}"
            elif errors != expected:
                status, detail = "FAIL", f"{errors} errors, expected {expected}; first: {first[:300]}"
            else:
                status, detail = "PASS", f"{errors} errors as expected" if errors else "no errors"
            if budget:
                detail += "; time limit reached, not all items calculated"
            detail += f" ({secs:.0f} s, {r['mode']})"
        failed += status == "FAIL"
        line = f"{status:4s}  {r['config']}: {detail}"
        print(line, flush=True)
        lines.append(line)

    summary = f"{len(rows)} configurations, {failed} failed, GeoDMS {geodms.name}"
    print("\n" + summary)
    (out / "summary.txt").write_text("\n".join(lines + ["", summary]) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
