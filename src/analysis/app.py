import streamlit as st
import duckdb
import pandas as pd
import os

# Set page configuration
st.set_page_config(page_title="Court Cases Analysis", page_icon="⚖️", layout="wide")

# Database connection
DB_PATH = os.getenv("DUCKDB_PATH", "output/gold/court_analytics.duckdb")


@st.cache_resource
def get_connection():
    """Establishes a connection to the DuckDB database."""
    if not os.path.exists(DB_PATH):
        st.error(
            f"Database not found at {DB_PATH}. Please run the data loader script first."
        )
        return None
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        return conn
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None


def main():
    st.title("⚖️ Court Cases Analysis UI")

    conn = get_connection()
    if not conn:
        return

    # Sidebar for navigation
    st.sidebar.header("Navigation")
    page = st.sidebar.radio("Go to", ["SQL Editor", "Table Explorer", "Statistics"])

    if page == "SQL Editor":
        st.header("SQL Editor")
        st.write("Run custom SQL queries against the `court_cases` table.")

        default_query = "SELECT * FROM court_cases LIMIT 10;"
        query = st.text_area("SQL Query", value=default_query, height=150)

        if st.button("Run Query"):
            try:
                df = conn.execute(query).df()
                st.success(f"Query returned {len(df)} rows.")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error executing query: {e}")

    elif page == "Table Explorer":
        st.header("Table Explorer")

        # Get list of tables
        tables = conn.execute("SHOW TABLES").df()
        if tables.empty:
            st.warning("No tables found in the database.")
        else:
            table_name = st.selectbox("Select Table", tables["name"])

            # Show schema
            st.subheader(f"Schema: {table_name}")
            schema = conn.execute(f"DESCRIBE {table_name}").df()
            st.dataframe(schema, use_container_width=True)

            # Show data
            st.subheader(f"Data: {table_name}")
            limit = st.slider("Rows to display", 10, 1000, 100)
            df = conn.execute(f"SELECT * FROM {table_name} LIMIT {limit}").df()
            st.dataframe(df, use_container_width=True)

    elif page == "Statistics":
        st.header("Basic Statistics")

        try:
            # Total cases
            count = conn.execute("SELECT COUNT(*) FROM court_cases").fetchone()[0]
            st.metric("Total Cases", f"{count:,}")

            # Dismissal Rate
            dismissed = conn.execute(
                "SELECT COUNT(*) FROM court_cases WHERE dispositionText = 'D'"
            ).fetchone()[0]
            rate = (dismissed / count) * 100 if count > 0 else 0
            st.metric("Dismissal Rate", f"{rate:.2f}%")

            # Top Charges
            st.subheader("Top 10 Charges")
            top_charges = conn.execute("""
                SELECT charge, COUNT(*) as count 
                FROM court_cases 
                GROUP BY charge 
                ORDER BY count DESC 
                LIMIT 10
            """).df()
            st.bar_chart(top_charges.set_index("charge"))

        except Exception as e:
            st.error(f"Error calculating statistics: {e}")


if __name__ == "__main__":
    main()
