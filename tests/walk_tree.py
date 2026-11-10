"""Load one GeoDMS configuration and report every item that fails.

Usage:
    python walk_tree.py <GeoDMS folder> <config.dms> <output.tsv> [meta|calc] [seconds]
    python walk_tree.py <GeoDMS folder> --expand <text>

meta  resolves the meta information of every item: parsing, names, domains and values units.
calc  then also calculates every data item, until the time limit in seconds is reached.

Each line of the output is: kind<TAB>item<TAB>seconds<TAB>message, with kind LOADED, COUNT, META
(meta information fails), CALC (calculation fails), SLOW (took more than 5 s), BUDGET (time limit
reached, the remaining items are not calculated) or DONE. The lines are written one by one, so
that a crash of the engine keeps the lines up to that item.

With --expand it prints the text with its placeholders filled in, such as %SourceDataDir%.
run_tests.py starts this script once per configuration, each time in a new process.
"""
import os
import sys
import tempfile
import time

gd = sys.argv[1]
os.add_dll_directory(gd)
os.environ["PATH"] = gd + os.pathsep + os.environ["PATH"]
sys.path.insert(0, gd)
import geodms  # noqa: E402


def expand(text):
    with tempfile.TemporaryDirectory() as tmp:
        cfg = os.path.join(tmp, "expand.dms")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write("container expand\n{\n\tparameter<string> value := expand(., '" + text + "');\n}\n")
        engine = geodms.Engine()
        config = engine.load_config(cfg)
        item = config.const_root().find("value")
        item.update_metainfo()
        return item.asDataItem().get_value_as_str(0)


if sys.argv[2] == "--expand":
    print(expand(sys.argv[3]))
    sys.exit(0)

cfg, out_path = sys.argv[2], sys.argv[3]
mode = sys.argv[4] if len(sys.argv) > 4 else "meta"
budget = float(sys.argv[5]) if len(sys.argv) > 5 else 300.0


def clean(s):
    return " ".join((s or "").split())[:600]


with open(out_path, "w", encoding="utf-8") as out:
    def write(kind, path, secs, msg=""):
        out.write(f"{kind}\t{path}\t{secs:.2f}\t{clean(msg)}\n")
        out.flush()

    t0 = time.time()
    try:
        engine = geodms.Engine()
        config = engine.load_config(cfg)
        root = config.const_root()
    except Exception as ex:
        write("LOADFAIL", cfg, time.time() - t0, str(ex))
        sys.exit(2)
    write("LOADED", cfg, time.time() - t0)

    items = []

    def walk(item):
        if item.is_template() or item.in_template():
            return
        items.append(item)
        for sub in item.sub_items():
            walk(sub)

    walk(root)
    write("COUNT", cfg, time.time() - t0, str(len(items)))

    good = []
    for item in items:
        t = time.time()
        try:
            if item.update_metainfo():
                good.append(item)
            else:
                write("META", item.full_name(), time.time() - t, item.fail_reason())
        except Exception as ex:
            write("META", item.full_name(), time.time() - t, str(ex))

    if mode == "calc":
        start = time.time()
        for item in good:
            if not item.isDataItem():
                continue
            if time.time() - start > budget:
                write("BUDGET", item.full_name(), time.time() - start, "time limit reached")
                break
            t = time.time()
            try:
                # update_metainfo does not calculate; asking for a value does
                data = item.asDataItem()
                if data.size() > 0:
                    data.get_value_as_str(0)
            except Exception as ex:
                # the binding reads values as text; for other value types it raises a checked_cast
                # error after the engine has calculated the data, so that is not a failure
                if not ("checked_cast" in str(ex) and "TileFunctor<struct SharedStr>" in str(ex)):
                    write("CALC", item.full_name(), time.time() - t, str(ex))
                continue
            if time.time() - t > 5:
                write("SLOW", item.full_name(), time.time() - t)
    write("DONE", cfg, time.time() - t0, f"meta information of {len(good)} of {len(items)} items resolved")
