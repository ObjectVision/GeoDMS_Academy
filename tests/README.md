# Testing the Academy on a GeoDMS release

The exercises of the Academy only help students if they run on the GeoDMS release they install. Run this test after every new release, before the Academy refers to it:

```
python tests/run_tests.py
```

It loads every configuration listed in `configurations.csv`, resolves the meta information of every item and calculates the data items, and compares the number of errors with the number expected. It ends with a line such as `37 configurations, 0 failed` and with exit code 1 if a configuration gives another number of errors than expected. The details, one tsv file per configuration and `summary.txt`, are in `tests/results`.

## Options

| Option | Meaning |
|---|---|
| `--geodms <folder>` | the GeoDMS release to test; default the newest one in `C:/Program Files/ObjectVision` |
| `--source-data-dir <folder>` | the folder to use as `%SourceDataDir%`, instead of the one in the GeoDMS settings |
| `--local-data-dir <folder>` | the folder to use as `%LocalDataDir%` |
| `--only <text>` | test only the configurations whose path contains this text |
| `--budget <seconds>` | time per configuration for calculating items; default 300 |

## What it needs

- Python with the GeoDMS binding of the release. A GeoDMS folder has a `geodms.cp3XX-win_amd64.pyd` for a few Python versions; use one of those versions.
- The source data of Module 6b in `%SourceDataDir%/GeoDMS_Academy/networks_publictransport`, from the Academy data folder on Stack. Without it, Module 6b is skipped. With `--source-data-dir` the test can read it from another folder without changing the GeoDMS settings.
- For Modules 7, 8 and 9, the repositories [LandUseModelling](https://github.com/ObjectVision/LandUseModelling) and [RS_Deltares_Cursus](https://github.com/ObjectVision/RS_Deltares_Cursus) checked out next to this repository. Without them, those configurations are skipped.

## How to read the result

- `PASS`: as many errors as expected. The exercise of Module 1a has 16 errors on purpose.
- `FAIL`: another number of errors, or the run stopped before the end. The line gives the first error; the tsv file of the configuration has them all, with the item and the message.
- `SKIP`: the configuration or its source data is not there.

Some configurations are only tested on their meta information (mode `meta`), because calculating them takes too long: the public transport network of Module 6b, the allocation and the game of life. The calculation of a configuration also stops when its time budget is used up; the line then says so.

A configuration that passes has no errors, but its results can still be wrong. Look at the results of the configurations you changed, as Module 1e describes under *when there is no error: checking a result*.

## Changing the list

`configurations.csv` has one line per configuration: its path from the root of this repository, the mode (`calc` or `meta`), the number of errors expected, the folder under `%SourceDataDir%` it needs, and a note. Add a line when you add an exercise. When a release fixes or causes an error in a configuration on purpose, change the expected number and explain it in the note.

The module 2 result reads files that earlier steps of that exercise write (`Preprocessing` and `python/gemeente_share.py`). On a computer where the exercise has not been done yet, those items fail.
