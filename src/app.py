import streamlit as st
import os
import importlib.util
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

PROPOSALS_DIR = "src/services/proposals"


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
