import nbformat
from nbclient import execute
import sys
import os

# Assume we run this from the project root
os.chdir('.')

# Load the notebook with UTF-8 encoding
with open('notebooks/favar_taylor_comparison_executed.ipynb', 'r', encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

# Execute the notebook
try:
    print("Starting notebook execution...")
    execute(nb, cwd='notebooks', timeout=600)

    print("\n" + "=" * 80)
    print("NOTEBOOK EXECUTION COMPLETED SUCCESSFULLY")
    print("=" * 80)

    # Save executed notebook
    os.makedirs('results', exist_ok=True)
    with open('results/favar_taylor_comparison_executed.ipynb', 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print("Executed notebook saved as: results/favar_taylor_comparison_executed.ipynb")

except Exception as e:
    print(f"Error during execution: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
