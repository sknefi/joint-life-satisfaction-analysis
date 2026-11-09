#!/usr/bin/env python3
"""Execute the data-free quickstart with the current Python interpreter."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
state = ROOT / "tmp/jupyter"
kernel = state / "kernels/evs-develop"
kernel.mkdir(parents=True, exist_ok=True)
(kernel / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"], "display_name": "EVS Develop", "language": "python"}))
os.environ["JUPYTER_PATH"] = str(state)
os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / "tmp/jupyter-runtime")
os.environ["IPYTHONDIR"] = str(ROOT / "tmp/ipython")
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import nbformat
from nbclient import NotebookClient

path = ROOT / "notebooks/quickstart.ipynb"
notebook = nbformat.read(path, as_version=4)
NotebookClient(notebook, timeout=120, kernel_name="evs-develop", resources={"metadata": {"path": str(ROOT)}}).execute()
notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbformat.write(notebook, path)
print("Quickstart executed successfully using synthetic profiles only.")
