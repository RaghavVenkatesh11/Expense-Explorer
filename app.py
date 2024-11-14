import streamlit as st
import pandas as pd
import sqlite3

def view_table_data(table_name):
    conn = sqlite3.connect("expense_tracker1.db")
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

st.title("View Data in Database")

# Select table to view
table_name = st.selectbox("Select a table to view", ["users", "expenses", "budget_limits"])

# Show table data
if st.button("View Data"):
    data = view_table_data(table_name)
    st.write(data)
