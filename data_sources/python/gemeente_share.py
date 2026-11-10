"""Module 2D, step 2: the Python part of the roundtrip between GeoDMS and pandas.

Reads the municipalities that the GeoDMS wrote with Export/gemeente_export, removes the rows
without data, computes for each remaining municipality its share of the total number of
inhabitants, and writes GM_CODE and that share (INW_SHARE) to gemeente_python.parquet, which
FromPython/gemeente_python in result.dms reads back.

Usage: python gemeente_share.py [folder]

The folder holds both parquet files. By default it is C:/LocalData/data_sources/python, where
%LocalDataProjDir%/python points to when the project folder is called data_sources.
"""
import sys
from pathlib import Path

import pandas as pd

MISSING = -99999999  # how this dataset codes a missing value

folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/LocalData/data_sources/python")

df = pd.read_parquet(folder / "gemeente.parquet")
df = df[df["AANT_INW"] != MISSING].copy()
df["INW_SHARE"] = df["AANT_INW"] / df["AANT_INW"].sum()
df[["GM_CODE", "INW_SHARE"]].to_parquet(folder / "gemeente_python.parquet", index=False)

print(f"{len(df)} municipalities with data, shares written to {folder / 'gemeente_python.parquet'}")
