import sys
import os

# Add the 'src' directory to the Python path so modules can be imported as 'from services...'
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# c is a magic variable that will be available in this file
c.NotebookApp.password = ""
c.NotebookApp.token = ""
c.NotebookApp.open_browser = False
c.NotebookApp.ip = "0.0.0.0"
c.NotebookApp.port = 8888
c.NotebookApp.allow_root = True
