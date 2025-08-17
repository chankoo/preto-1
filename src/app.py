import streamlit as st
import os
import importlib.util
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

DATA_DIR = "src/services/tables"
PROPOSALS_DIR = "src/services/proposals"


def get_available_data_tables():
    """
    Recursively scans the data directory and returns a list of available table names
    (relative to DATA_DIR, without .py extension), including files in subdirectories.
    """
    if not os.path.exists(DATA_DIR):
        return []
    tables = []
    for root, _, files in os.walk(DATA_DIR):
        for filename in files:
            if filename.endswith(".py") and not filename.startswith("__"):
                # Get relative path from DATA_DIR, remove .py extension, replace os.sep with '/'
                rel_path = os.path.relpath(os.path.join(root, filename), DATA_DIR)
                table_name = rel_path[:-3].replace(os.sep, "/")
                tables.append(table_name)
    return sorted(tables)


def get_available_proposals():
    """
    Scans the proposals directory and returns a list of available proposal names.
    """
    if not os.path.exists(PROPOSALS_DIR):
        return []
    proposals = []
    for filename in os.listdir(PROPOSALS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            proposals.append(os.path.splitext(filename)[0])
    return sorted(proposals)


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


@st.cache_data
def load_proposal_figure(proposal_name: str):
    """
    Dynamically imports the specified proposal module and returns its figure.
    The result is cached to prevent reloading.
    """
    module_path = os.path.join(PROPOSALS_DIR, f"{proposal_name}.py")

    try:
        spec = importlib.util.spec_from_file_location(proposal_name, module_path)
        if spec is None or spec.loader is None:
            st.error(f"Could not create module spec for {proposal_name}.")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the first attribute that is a matplotlib or plotly figure.
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                attr = getattr(module, attr_name)
                if isinstance(attr, (plt.Figure, go.Figure)):
                    return attr

        st.warning(f"No figure found in module: {proposal_name}")
        return None

    except Exception as e:
        st.error(f"Error loading figure from {proposal_name}: {e}")
        return None


def main():
    """
    Main function to run the Streamlit app.
    """
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Choose a page", ["Data Tables", "Proposals"])

    if page == "Data Tables":
        st.sidebar.title("Data Tables")
        available_tables = get_available_data_tables()

        if not available_tables:
            st.error("No data tables found in the 'DATA_DIR' directory.")
            return

        selection = st.sidebar.selectbox("Choose a data table", available_tables)

        if selection:
            st.title(f"Data Table: {selection}")
            df = load_data(selection)
            if df is not None:
                st.write(f"Displaying data from `{selection}`")
                st.dataframe(df)
            else:
                st.write("Could not load or find data for the selected table.")

    elif page == "Proposals":
        st.sidebar.title("Proposals")
        available_proposals = get_available_proposals()

        if not available_proposals:
            st.error("No proposals found in the 'PROPOSALS_DIR' directory.")
            return

        selection = st.sidebar.selectbox("Choose a proposal", available_proposals)

        if selection:
            st.title(f"Proposal: {selection}")
            fig = load_proposal_figure(selection)

            if fig is not None:
                if isinstance(fig, plt.Figure):
                    st.pyplot(fig)
                elif isinstance(fig, go.Figure):
                    st.plotly_chart(fig)
            else:
                st.write("Could not load or find a figure for the selected proposal.")


if __name__ == "__main__":
    main()
