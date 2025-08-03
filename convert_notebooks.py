import os
import glob
import subprocess

# Get the absolute path of the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define source and destination directories relative to the script's location
source_dir = os.path.join(script_dir, "notebooks", "tables")
dest_dir = os.path.join(script_dir, "src", "services", "data")

print(f"Searching for notebooks in: {source_dir}")

# Ensure the destination directory exists
os.makedirs(dest_dir, exist_ok=True)

# Find all .ipynb files in the source directory
notebook_files = glob.glob(os.path.join(source_dir, "*.ipynb"))

if not notebook_files:
    print(f"No notebook files (.ipynb) found.")
else:
    print(f"Found notebooks: {notebook_files}")
    for notebook_path in notebook_files:
        print(f"Converting {notebook_path}...")
        try:
            # Use jupyter nbconvert to convert the notebook to a python script
            subprocess.run(
                [
                    "jupyter",
                    "nbconvert",
                    "--to",
                    "python",
                    notebook_path,
                    "--output-dir",
                    dest_dir,
                ],
                check=True,
            )
            print(
                f"Successfully converted {notebook_path} to a .py file in '{dest_dir}'"
            )
        except subprocess.CalledProcessError as e:
            print(f"Error converting {notebook_path}: {e}")
        except FileNotFoundError:
            print(
                "Error: 'jupyter' command not found. Make sure Jupyter is installed and in your PATH."
            )

print("\nConversion process finished.")
