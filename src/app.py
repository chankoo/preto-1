import streamlit as st
from services.data import departments

st.title("Hello, Streamlit!")

st.write("This is a simple Streamlit app.")


st.write(departments.department_df)
