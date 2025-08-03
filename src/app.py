import streamlit as st
import os
import importlib.util
import pandas as pd

DATA_DIR = "src/services/data"

def get_available_data_tables():
    """
    Scans the data directory and returns a list of available table names
    without loading the modules.
    """
    tables = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            tables.append(os.path.splitext(filename)[0])
    return sorted(tables)

@st.cache_data
def load_data(table_name: str):
    """
    Dynamically imports the specified data module and returns its DataFrame.
    The result is cached to prevent reloading.
    """
    module_path = os.path.join(DATA_DIR, f"{table_name}.py")
    
    try:
        spec = importlib.util.spec_from_file_location(table_name, module_path)
        if spec is None or spec.loader is None:
            st.error(f"Could not create module spec for {table_name}.")
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the first attribute that is a pandas DataFrame.
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                attr = getattr(module, attr_name)
                if isinstance(attr, pd.DataFrame):
                    return attr
        
        st.warning(f"No DataFrame found in module: {table_name}")
        return None

    except Exception as e:
        st.error(f"Error loading data from {table_name}: {e}")
        return None


def main():
    """
    Main function to run the Streamlit app.
    """
    st.sidebar.title("Data Tables")
    
    available_tables = get_available_data_tables()
    
    if not available_tables:
        st.error("No data tables found in the 'src/services/data' directory.")
        return

    selection = st.sidebar.selectbox("Choose a data table", available_tables)

    if selection:
        st.title(f"Data Table: {selection}")
        
        # Load data on demand when a selection is made
        df = load_data(selection)
        
        if df is not None:
            st.write(f"Displaying data from `{selection}`")
            st.dataframe(df)
        else:
            st.write("Could not load or find data for the selected table.")

if __name__ == "__main__":
    main()
