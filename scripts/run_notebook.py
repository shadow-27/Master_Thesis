"""Execute a Jupyter notebook using nbclient.

Usage:
  python scripts/run_notebook.py [path/to/notebook.ipynb]

If no path is given, defaults to the main (non-GSW) notebook.
"""

import json
import os
import sys

import nbformat
from nbclient import NotebookClient


DEFAULT_NB_PATH = "notebooks/favar_taylor_comparison_executed.ipynb"


def _get_nb_path(argv: list[str]) -> str:
    if len(argv) >= 2 and argv[1].strip():
        return argv[1]
    return DEFAULT_NB_PATH


nb_path = _get_nb_path(sys.argv)
nb_abspath = os.path.abspath(nb_path)
nb_dir = os.path.dirname(nb_abspath)

print(f"Loading notebook: {nb_path}")
with open(nb_abspath, encoding="utf-8") as f:
    nb = nbformat.read(f, as_version=4)

# Clear outputs to avoid stale results being mistaken for fresh execution.
for cell in nb.cells:
    if cell.get("cell_type") == "code":
        cell["outputs"] = []
        cell["execution_count"] = None

kernel_name = nb.metadata.get("kernelspec", {}).get("name") or "python3"

print(f"Total cells: {len(nb.cells)}")
print(f"Kernel: {kernel_name}")
print("Starting execution (timeout = 3600s per cell)...")

client = NotebookClient(
    nb,
    timeout=3600,
    kernel_name=kernel_name,
    resources={"metadata": {"path": nb_dir}},
)

try:
    with client.setup_kernel():
        for i, cell in enumerate(nb.cells):
            if cell.cell_type != 'code':
                continue
            src_preview = (cell.source or "")[:70].replace("\n", " ")
            print(f"  Cell {i:2d}: {src_preview}", flush=True)
            try:
                client.execute_cell(cell, i)
            except Exception as e:
                print(f"  !! ERROR in cell {i}: {e}", file=sys.stderr)
                with open(nb_abspath, 'w', encoding='utf-8') as f:
                    json.dump(dict(nb), f, indent=1, ensure_ascii=False)
                print(f"  Partial notebook saved.")
                sys.exit(1)

    print("\nAll cells executed successfully.")
except Exception as e:
    print(f"Kernel error: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    with open(nb_abspath, 'w', encoding='utf-8') as f:
        json.dump(dict(nb), f, indent=1, ensure_ascii=False)
    print(f"Notebook saved to {nb_path}")
