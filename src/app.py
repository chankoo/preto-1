import streamlit as st
import os
import importlib.util
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

PROPOSALS_DIR = "src/services/proposals"


def get_proposal_categories():
    """
    Scans the proposals directory and returns a list of unique proposal categories.
    Categories are the base proposal names (e.g., 'proposal_01', 'basic_proposal').
    """
    if not os.path.exists(PROPOSALS_DIR):
        return []

    categories = set()
    for filename in os.listdir(PROPOSALS_DIR):
        if filename.endswith((".py", ".md")) and not filename.startswith("__"):
            name = os.path.splitext(filename)[0]

            # Extract base category from filename patterns
            if name.startswith("basic_proposal"):
                if "_" in name[len("basic_proposal") :]:
                    # Has subtype (e.g., basic_proposal_부서별)
                    categories.add("basic_proposal")
                else:
                    # Base file (e.g., basic_proposal.py) - shouldn't exist but handle it
                    categories.add(name)
            elif name.startswith("proposal_"):
                # Extract proposal number (e.g., proposal_01, proposal_01_부서별)
                parts = name.split("_")
                if len(parts) >= 2:
                    # proposal_XX or proposal_XX_subtype
                    category = "_".join(parts[:2])  # proposal_01
                    categories.add(category)
            else:
                # Other files without standard pattern
                if "_" in name:
                    # Assume format: category_subtype
                    category = name.rsplit("_", 1)[0]
                    categories.add(category)
                else:
                    # Base file
                    categories.add(name)

    return sorted(list(categories))


def get_proposal_subtypes(category):
    """
    Returns available subtypes for a given proposal category.
    Subtypes include markdown files (개요) and python files (부서별, 직무별, etc.).
    """
    if not os.path.exists(PROPOSALS_DIR):
        return []

    subtypes = set()

    # Dynamically scan for all subtypes for this category
    for filename in os.listdir(PROPOSALS_DIR):
        if filename.startswith(f"{category}_") and not filename.startswith("__"):
            name = os.path.splitext(filename)[0]

            # Extract subtype (everything after category_)
            subtype = name[len(f"{category}_") :]
            if subtype:  # Make sure subtype is not empty
                subtypes.add(subtype)

    # If no subtypes found, check for base file (should add "기본")
    if not subtypes and os.path.exists(os.path.join(PROPOSALS_DIR, f"{category}.py")):
        subtypes.add("기본")

    # Sort subtypes in a logical order
    priority_order = ["개요", "기본", "부서별", "직무별", "직위직급별"]
    sorted_subtypes = []

    # Add priority items first
    for item in priority_order:
        if item in subtypes:
            sorted_subtypes.append(item)
            subtypes.remove(item)

    # Add remaining subtypes in alphabetical order
    sorted_subtypes.extend(sorted(list(subtypes)))

    return sorted_subtypes


@st.cache_data
def load_markdown_content(category: str, subtype: str):
    """
    Loads markdown content for a proposal category and subtype.
    Returns the content as a string or None if not found.
    """
    # For 개요 subtype, look for {category}_개요.md
    if subtype == "개요":
        md_path = os.path.join(PROPOSALS_DIR, f"{category}_개요.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                st.error(f"Error reading markdown file {category}_개요.md: {e}")

    # For other subtypes, try legacy patterns as fallback
    possible_names = [f"{category}_instruction.md", f"{category}.md"]
    for md_name in possible_names:
        md_path = os.path.join(PROPOSALS_DIR, md_name)
        if os.path.exists(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                st.error(f"Error reading markdown file {md_name}: {e}")

    return None


@st.cache_data
def load_proposal_data(category: str, subtype: str):
    """
    Dynamically imports the specified proposal module and returns its figure and aggregate_df.
    Returns a tuple (figure, aggregate_df). aggregate_df is None if not available.
    The result is cached to prevent reloading.
    """
    # Determine the module file based on category and subtype
    if subtype == "개요":
        # For 개요, no figure is expected (only markdown)
        return None, None
    else:
        # Try specific subtype file first
        if subtype == "기본":
            # For 기본, try base file first, then {category}_기본.py
            module_filename = f"{category}.py"
            module_path = os.path.join(PROPOSALS_DIR, module_filename)

            if not os.path.exists(module_path):
                module_filename = f"{category}_기본.py"
                module_path = os.path.join(PROPOSALS_DIR, module_filename)
        else:
            # For all other subtypes, try {category}_{subtype}.py
            module_filename = f"{category}_{subtype}.py"
            module_path = os.path.join(PROPOSALS_DIR, module_filename)

            # If specific subtype doesn't exist, try base file as fallback
            if not os.path.exists(module_path):
                module_filename = f"{category}.py"
                module_path = os.path.join(PROPOSALS_DIR, module_filename)

    if not os.path.exists(module_path):
        st.warning(f"No module file found for {category}_{subtype}")
        return None, None

    try:
        # Create a unique module name to avoid conflicts
        module_name = f"{category}_{subtype}".replace(".", "_")
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            st.error(f"Could not create module spec for {module_filename}.")
            return None, None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Try to find create_figure_and_df function first (returns both figure and aggregate_df)
        if hasattr(module, "create_figure_and_df"):
            result = module.create_figure_and_df()
            if isinstance(result, tuple) and len(result) == 2:
                fig, aggregate_df = result
                if isinstance(fig, (plt.Figure, go.Figure)):
                    return fig, aggregate_df
            else:
                st.warning(
                    f"create_figure_and_df in {module_filename} should return a tuple (figure, aggregate_df)"
                )
                return None, None

        # If create_figure_and_df not found, try create_figure function
        elif hasattr(module, "create_figure"):
            fig = module.create_figure()
            if isinstance(fig, (plt.Figure, go.Figure)):
                return fig, None
            else:
                st.warning(f"create_figure in {module_filename} should return a figure")
                return None, None

        # Fallback: Find the first attribute that is a matplotlib or plotly figure
        else:
            for attr_name in dir(module):
                if not attr_name.startswith("_"):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, (plt.Figure, go.Figure)):
                        return attr, None

            st.warning(
                f"No figure or create_figure/create_figure_and_df function found in module: {module_filename}"
            )
            return None, None

    except Exception as e:
        st.error(f"Error loading data from {module_filename}: {e}")
        return None, None


def main():
    """
    Main function to run the Streamlit app.
    """

    st.sidebar.title("HR Analytics Graph Collection")
    st.sidebar.markdown(
        """
        더 이상 '감'과 '경험'에만 의존하는 HR의 시대는 지났습니다.\n
        조직의 숨겨진 리스크와 기회를 객관적 지표로 증명하고 선제적으로 인재관리를 시작하세요.
        """
    )

    # Get available proposal categories
    available_categories = get_proposal_categories()

    if not available_categories:
        st.error("No proposals found in the 'PROPOSALS_DIR' directory.")
        return

    # First selectbox: Choose proposal category
    selected_category = st.sidebar.selectbox("그래프 살펴보기", available_categories)

    if selected_category:
        # Get available subtypes for the selected category
        available_subtypes = get_proposal_subtypes(selected_category)

        if not available_subtypes:
            st.error(f"No subtypes found for proposal: {selected_category}")
            return

        # Second selectbox: Choose subtype
        selected_subtype = st.sidebar.selectbox("하위 내용 선택", available_subtypes)

        if selected_subtype:
            st.title(f"Proposal: {selected_category} - {selected_subtype}")

            # Load and display markdown content if available (especially for 개요)
            md_content = load_markdown_content(selected_category, selected_subtype)
            if md_content:
                st.markdown(md_content)
                st.divider()

            # Load and display figure and aggregate_df (not for 개요)
            if selected_subtype != "개요":
                fig, aggregate_df = load_proposal_data(
                    selected_category, selected_subtype
                )
                if fig is not None:
                    if isinstance(fig, plt.Figure):
                        st.pyplot(fig)
                    elif isinstance(fig, go.Figure):
                        st.plotly_chart(fig)

                    # Display aggregate_df if available
                    if aggregate_df is not None:
                        st.subheader("데이터 테이블")
                        st.dataframe(aggregate_df, use_container_width=True)
                else:
                    st.write(
                        "Could not load or find a figure for the selected proposal."
                    )


if __name__ == "__main__":
    main()
