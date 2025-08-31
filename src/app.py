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
    Categories are the base proposal names (e.g., 'proposal_01', 'basic_proposal_02').
    """
    if not os.path.exists(PROPOSALS_DIR):
        return []
    
    categories = set()
    for filename in os.listdir(PROPOSALS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            name = os.path.splitext(filename)[0]
            # Extract base category (everything before the last underscore if it's a subtype)
            if "_부서별" in name or "_직무별" in name or "_직위직급별" in name or "_기본" in name:
                # Find the last occurrence of these patterns and extract the base
                for pattern in ["_부서별", "_직무별", "_직위직급별", "_기본"]:
                    if name.endswith(pattern):
                        categories.add(name[:-len(pattern)])
                        break
            else:
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
    
    # Check for markdown files (개요)
    md_patterns = [f"{category}_개요.md"]
    for pattern in md_patterns:
        if os.path.exists(os.path.join(PROPOSALS_DIR, pattern)):
            subtypes.add("개요")
    
    # Check for python subtypes
    py_patterns = [
        f"{category}_부서별.py",
        f"{category}_직무별.py", 
        f"{category}_직위직급별.py",
        f"{category}_기본.py"
    ]
    
    for pattern in py_patterns:
        if os.path.exists(os.path.join(PROPOSALS_DIR, pattern)):
            if pattern.endswith("_부서별.py"):
                subtypes.add("부서별")
            elif pattern.endswith("_직무별.py"):
                subtypes.add("직무별")
            elif pattern.endswith("_직위직급별.py"):
                subtypes.add("직위직급별")
            elif pattern.endswith("_기본.py"):
                subtypes.add("기본")
    
    # If no subtypes found, check for base file
    if not subtypes and os.path.exists(os.path.join(PROPOSALS_DIR, f"{category}.py")):
        subtypes.add("기본")
    
    # Sort subtypes in a logical order
    order = ["개요", "기본", "부서별", "직무별", "직위직급별"]
    sorted_subtypes = [subtype for subtype in order if subtype in subtypes]
    
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
def load_proposal_figure(category: str, subtype: str):
    """
    Dynamically imports the specified proposal module and returns its figure.
    The result is cached to prevent reloading.
    """
    # Determine the module file based on category and subtype
    if subtype == "개요":
        # For 개요, no figure is expected (only markdown)
        return None
    elif subtype in ["부서별", "직무별", "직위직급별", "기본"]:
        # Try specific subtype file first
        module_filename = f"{category}_{subtype}.py"
        module_path = os.path.join(PROPOSALS_DIR, module_filename)
        
        # If specific subtype doesn't exist, try base file
        if not os.path.exists(module_path):
            module_filename = f"{category}.py"
            module_path = os.path.join(PROPOSALS_DIR, module_filename)
    else:
        # Default to base file
        module_filename = f"{category}.py"
        module_path = os.path.join(PROPOSALS_DIR, module_filename)

    if not os.path.exists(module_path):
        st.warning(f"No module file found for {category}_{subtype}")
        return None

    try:
        # Create a unique module name to avoid conflicts
        module_name = f"{category}_{subtype}".replace(".", "_")
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            st.error(f"Could not create module spec for {module_filename}.")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the first attribute that is a matplotlib or plotly figure.
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                attr = getattr(module, attr_name)
                if isinstance(attr, (plt.Figure, go.Figure)):
                    return attr

        st.warning(f"No figure found in module: {module_filename}")
        return None

    except Exception as e:
        st.error(f"Error loading figure from {module_filename}: {e}")
        return None


def main():
    """
    Main function to run the Streamlit app.
    """

    st.sidebar.title("Proposals")
    
    # Get available proposal categories
    available_categories = get_proposal_categories()

    if not available_categories:
        st.error("No proposals found in the 'PROPOSALS_DIR' directory.")
        return

    # First selectbox: Choose proposal category
    selected_category = st.sidebar.selectbox("Choose a proposal", available_categories)
    
    if selected_category:
        # Get available subtypes for the selected category
        available_subtypes = get_proposal_subtypes(selected_category)
        
        if not available_subtypes:
            st.error(f"No subtypes found for proposal: {selected_category}")
            return
        
        # Second selectbox: Choose subtype
        selected_subtype = st.sidebar.selectbox("Choose type", available_subtypes)
        
        if selected_subtype:
            st.title(f"Proposal: {selected_category} - {selected_subtype}")

            # Load and display markdown content if available (especially for 개요)
            md_content = load_markdown_content(selected_category, selected_subtype)
            if md_content:
                st.markdown(md_content)
                st.divider()

            # Load and display figure (not for 개요)
            if selected_subtype != "개요":
                fig = load_proposal_figure(selected_category, selected_subtype)
                if fig is not None:
                    if isinstance(fig, plt.Figure):
                        st.pyplot(fig)
                    elif isinstance(fig, go.Figure):
                        st.plotly_chart(fig)
                else:
                    st.write("Could not load or find a figure for the selected proposal.")
            else:
                st.info("개요 페이지입니다. 그래프는 다른 타입에서 확인하실 수 있습니다.")


if __name__ == "__main__":
    main()
