import os
import subprocess

def convert_notebooks_in_dir(source_root, dest_root):
    """
    Recursively finds .ipynb files in source_root, converts them to .py,
    and saves them in dest_root, preserving the directory structure.
    """
    print(f"Starting conversion from '{source_root}' to '{dest_root}'...")
    for dirpath, _, filenames in os.walk(source_root):
        for filename in filenames:
            if filename.endswith(".ipynb"):
                notebook_full_path = os.path.join(dirpath, filename)
                
                # Determine the relative path to maintain directory structure
                relative_path = os.path.relpath(dirpath, source_root)
                
                # For the root, relpath is '.', handle this case
                if relative_path == ".":
                    dest_dir = dest_root
                else:
                    dest_dir = os.path.join(dest_root, relative_path)

                # Ensure the destination directory exists
                os.makedirs(dest_dir, exist_ok=True)

                print(f"Converting '{notebook_full_path}'...")
                try:
                    # Use jupyter nbconvert to convert the notebook to a python script
                    subprocess.run(
                        [
                            "jupyter",
                            "nbconvert",
                            "--to",
                            "python",
                            notebook_full_path,
                            "--output-dir",
                            dest_dir,
                        ],
                        check=True,
                    )
                    print(f"  -> Successfully converted to '{dest_dir}'")
                except subprocess.CalledProcessError as e:
                    print(f"  -> Error converting {notebook_full_path}: {e}")
                except FileNotFoundError:
                    print(
                        "Error: 'jupyter' command not found. Make sure Jupyter is installed and in your PATH."
                    )
                    return # Exit if jupyter is not found

def main():
    """
    Main function to define source and destination directories and
    start the conversion process.
    """
    # Get the absolute path of the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Run the conversion
    convert_notebooks_in_dir(
        source_root=os.path.join(script_dir, "notebooks", "tables"),
        dest_root=os.path.join(script_dir, "src", "services", "tables"),
    )

    convert_notebooks_in_dir(
        source_root=os.path.join(script_dir, "notebooks", "proposals"),
        dest_root=os.path.join(script_dir, "src", "services", "proposals"),
    )

    print("\nConversion process finished.")

if __name__ == "__main__":
    main()