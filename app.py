import os
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from app.agent import run_analytics_agent
from app.db import get_engine, get_schema_metadata, seed_database

load_dotenv()

st.set_page_config(
    page_title="SQL & Database Analytics Agent",
    page_icon="🛡️",
    layout="wide",
)

# Custom header styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #64748B;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .telemetry-box {
        background-color: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 0.75rem 1rem;
        font-family: monospace;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">🛡️ SQL & Database Analytics Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">LangGraph text-to-SQL agent with self-correction reflection loops, AST security filters, and NeMo Guardrails</div>',
    unsafe_allow_html=True,
)

# Initialize database
engine = get_engine()

# Sidebar: Environment & Database controls
with st.sidebar:
    st.header("⚙️ Configuration & Database")
    st.caption(f"**Database URL:** `{engine.url}`")

    if st.button("🌱 Re-Seed Sample Database", use_container_width=True):
        seed_database(engine)
        st.success("Database re-seeded with sample 'orders' and 'products' tables!")

    st.divider()
    st.subheader("📋 Reflected Schema Metadata")
    schema_text = get_schema_metadata(engine)
    st.text_area("SQLAlchemy Schema Inspection", schema_text, height=220, disabled=True)

    st.divider()
    st.subheader("🧪 Quick Test Presets")
    test_mode = st.radio(
        "Simulation Mode",
        options=["Standard", "Simulate Column Error (Self-Correction Test)"],
        index=0,
        help="Use 'Simulate Column Error' to force column mismatch ('created_at') and test the reflection loop.",
    )

    preset_query = st.selectbox(
        "Load Example Query:",
        options=[
            "",
            "Show orders sorted by date",
            "DROP TABLE orders; --",
            "SELECT * FROM orders WHERE 1=1",
            "<script>alert('xss')</script>",
            "Total sales revenue by order date",
            "List product counts and average price by category",
        ],
    )

# Main Query Panel
st.subheader("💬 Natural Language Query Input")
col_input, col_btn = st.columns([5, 1])

with col_input:
    user_query = st.text_input(
        "Ask a business intelligence question or test safety boundaries:",
        value=preset_query if preset_query else "Show orders sorted by date",
        placeholder="e.g. Show orders sorted by date",
    )

with col_btn:
    st.write("")
    st.write("")
    run_btn = st.button("🚀 Run Query", use_container_width=True, type="primary")

if run_btn or user_query:
    force_invalid = test_mode == "Simulate Column Error (Self-Correction Test)"

    with st.spinner("Processing query through Guardrails & LangGraph state machine..."):
        result = run_analytics_agent(
            user_query=user_query,
            engine=engine,
            force_invalid_column=force_invalid,
        )

    # 1. Security Alert & Error Handling
    error_msg = result.get("error_message")
    retry_count = result.get("retry_count", 0)

    if error_msg:
        if "Security" in error_msg or "AST" in error_msg or "NeMo" in error_msg:
            st.error(f"🛑 **Security Policy Block:** {error_msg}")
        else:
            st.warning(f"⚠️ **Execution Notice:** {error_msg}")

    # 2. Collapsible Panels: Code, Telemetry & Reflection Logs
    st.divider()
    st.subheader("🔍 Execution Telemetry & Code Feeds")

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("📝 Generated SQL Query", expanded=True):
            gen_sql = result.get("generated_sql")
            if gen_sql:
                st.code(gen_sql, language="sql")
            else:
                st.info("No SQL generated (blocked before execution).")

    with col2:
        with st.expander("🔁 Self-Correction & Reflection Logs", expanded=(retry_count > 0)):
            if retry_count > 0:
                st.success(f"Self-Correction loop activated! Recovered after {retry_count} retry attempt(s).")
                reflection_prompt = result.get("reflection_prompt")
                if reflection_prompt:
                    st.markdown(f"**Correction Directive:**\n```\n{reflection_prompt}\n```")
            else:
                st.info("Query succeeded on primary generation (0 retries required).")

    with st.expander("⏱️ LangGraph Execution Steps & Telemetry", expanded=False):
        telemetry = result.get("telemetry", [])
        for log in telemetry:
            st.markdown(f"- `{log}`")

    # 3. Tabular Results & Plotly Visuals
    rows = result.get("db_result")
    if rows and isinstance(rows, list):
        st.divider()
        st.subheader("📊 Query Results & Analytics Canvas")

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # Plotly Canvas: check for numeric data
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        non_numeric_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        if numeric_cols:
            st.markdown("#### 📈 Interactive Plotly Chart")
            chart_col1, chart_col2 = st.columns([1, 3])

            with chart_col1:
                y_axis = st.selectbox("Value Column (Y-axis)", options=numeric_cols, index=0)
                x_options = non_numeric_cols if non_numeric_cols else numeric_cols
                x_axis = st.selectbox("Category/Date Column (X-axis)", options=x_options, index=0)
                chart_type = st.selectbox("Chart Type", options=["Bar", "Line", "Scatter", "Pie"], index=0)

            with chart_col2:
                try:
                    if chart_type == "Bar":
                        fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}", text_auto=True)
                    elif chart_type == "Line":
                        fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} Trend over {x_axis}", markers=True)
                    elif chart_type == "Scatter":
                        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}", size=y_axis)
                    elif chart_type == "Pie":
                        fig = px.pie(df, names=x_axis, values=y_axis, title=f"Distribution of {y_axis}")

                    fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as chart_err:
                    st.caption(f"Plotly chart could not be rendered: {chart_err}")
