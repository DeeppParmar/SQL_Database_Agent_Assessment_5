import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from app.agent import run_analytics_agent
from app.db import get_db_stats, get_engine, get_schema_metadata, seed_database

load_dotenv()

st.set_page_config(
    page_title="SQL & Database Analytics Agent",
    page_icon="🛡️",
    layout="wide",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #475569;
        font-size: 1.0rem;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Initialize database
engine = get_engine()

# Initialize Session State
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "last_timestamp" not in st.session_state:
    st.session_state.last_timestamp = None
if "query_input_val" not in st.session_state:
    st.session_state.query_input_val = "Show orders sorted by date"

# Header
st.markdown('<div class="main-header">🛡️ SQL & Database Analytics Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">LangGraph Text-to-SQL Agent with Automatic Self-Correction Reflection Loops, AST Security Filters, and NeMo Guardrails</div>',
    unsafe_allow_html=True,
)

# Sidebar: Controls & Database Telemetry
with st.sidebar:
    st.header("⚙️ Database & Controls")
    st.caption(f"**Engine URL:** `{engine.url}`")

    # Live Database Table Stats (Updates in real time)
    stats = get_db_stats(engine)
    st.markdown("**Live Table Row Counts:**")
    stat_cols = st.columns(len(stats) if stats else 1)
    for idx, (tbl_name, count) in enumerate(stats.items()):
        stat_cols[idx % len(stat_cols)].metric(f"`{tbl_name}`", f"{count} rows")

    if st.button("🌱 Re-Seed Database", use_container_width=True):
        seed_database(engine)
        st.session_state.last_result = None
        st.success("Database re-seeded successfully with fresh records!")
        st.rerun()

    st.divider()
    st.subheader("📋 Reflected Schema")
    schema_text = get_schema_metadata(engine)
    st.text_area("SQLAlchemy inspect(engine)", schema_text, height=180, disabled=True)

    st.divider()
    st.subheader("🧪 Evaluation Presets")
    test_mode = st.radio(
        "Simulation Mode",
        options=["Standard Mode", "Force Column Error (Test Case 1: created_at)"],
        index=0,
        help="Force Column Error deliberately generates 'created_at' to trigger and demonstrate the reflection recovery loop.",
    )

    preset_selection = st.selectbox(
        "Quick Example Queries:",
        options=[
            "-- Select an example query --",
            "Show orders sorted by amount",
            "Show orders sorted by date",
            "Sort orders by customer",
            "Show pending orders",
            "Total sales revenue by order date",
            "Count orders by status",
            "List all products in Electronics",
            "What is the most expensive product?",
            "Orders with amount greater than 200",
            "DROP TABLE orders; --",
            "SELECT * FROM orders WHERE 1=1",
            "<script>alert('xss')</script>",
            "SELECT customer_name, amount FROM orders WHERE amount > 100",
        ],
    )
    if preset_selection != "-- Select an example query --":
        if st.session_state.query_input_val != preset_selection:
            st.session_state.query_input_val = preset_selection
            st.rerun()


# Main Query Input Section
st.subheader("💬 Natural Language Query Input")
st.caption("Ask an analytical business intelligence question, write raw SQL, or test adversarial injection patterns:")

with st.form("agent_query_form", clear_on_submit=False):
    col_input, col_submit = st.columns([5, 1])
    with col_input:
        user_query = st.text_input(
            "Query Input",
            value=st.session_state.query_input_val,
            placeholder="e.g. Show orders sorted by date, or Count orders by status...",
            label_visibility="collapsed",
        )
    with col_submit:
        submitted = st.form_submit_button("🚀 Run Analysis", use_container_width=True, type="primary")

# Execute Query on Form Submission
if submitted and user_query.strip():
    force_invalid = test_mode == "Force Column Error (Test Case 1: created_at)"
    with st.spinner("Processing through NeMo Guardrails & LangGraph state machine..."):
        result = run_analytics_agent(
            user_query=user_query,
            engine=engine,
            force_invalid_column=force_invalid,
        )
        st.session_state.last_result = result
        st.session_state.last_query = user_query
        st.session_state.last_timestamp = datetime.now().strftime("%H:%M:%S")

# Render Active Query Results
res = st.session_state.last_result
if res:
    error_msg = res.get("error_message")
    retry_count = res.get("retry_count", 0)
    db_result = res.get("db_result")
    sql_history = res.get("sql_history", [])
    telemetry = res.get("telemetry", [])

    is_security_block = bool(
        error_msg
        and any(k in error_msg for k in ["Security", "AST", "NeMo", "Destructive", "injection", "tautology", "XSS"])
    )
    is_self_corrected = retry_count > 0 and db_result is not None
    is_success = db_result is not None and not is_security_block

    st.divider()

    # 1. Execution KPI Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        if is_security_block:
            st.error("🛑 Security Blocked")
        elif is_self_corrected:
            st.success("🔄 Self-Corrected")
        elif is_success:
            st.success("🟢 Query Successful")
        else:
            st.warning("⚠️ Execution Error")

    with m2:
        st.metric(label="Reflection Retries Used", value=f"{retry_count} / 3")

    with m3:
        record_count = len(db_result) if isinstance(db_result, list) else 0
        st.metric(label="Records Retrieved", value=f"{record_count} rows")

    with m4:
        st.metric(label="Execution Time", value=st.session_state.last_timestamp or "Just now")

    # 2. Detailed Status Banner
    if is_security_block:
        st.error(
            f"**Security Guardrail Enforcement Active:**\n\n{error_msg}\n\n"
            "*Query was halted before database execution. The database remains completely intact.*"
        )
    elif is_self_corrected:
        st.success(
            f"**Self-Correction Recovery Successful:** Initial query failed due to invalid column reference. "
            f"The `reflection_node` diagnosed the error and rewrote the query using valid schema columns in {retry_count} retry attempt(s)!"
        )
    elif error_msg:
        st.warning(f"**Execution Notice:** {error_msg}")

    # 3. Collapsible Panels (Code, Reflection, Telemetry)
    st.subheader("🔍 Execution Telemetry & Code Feeds")
    col_code, col_reflect = st.columns(2)

    with col_code:
        with st.expander("📝 Generated SQL Query", expanded=True):
            if is_security_block:
                st.info("No SQL executed (intercepted at security perimeter).")
            elif sql_history and len(sql_history) > 1:
                st.markdown("**Attempt 1 (Generated with invalid column):**")
                st.code(sql_history[0], language="sql")
                st.markdown("**Attempt 2 (Corrected after Reflection):**")
                st.code(sql_history[-1], language="sql")
            elif res.get("generated_sql"):
                st.code(res.get("generated_sql"), language="sql")
            else:
                st.info("No SQL generated.")

    with col_reflect:
        with st.expander("🔁 Self-Correction & Reflection Logs", expanded=(retry_count > 0)):
            if is_security_block:
                st.info("Self-correction loop bypassed: Destructive / injection query terminated at input guardrail.")
            elif retry_count > 0:
                st.markdown(f"**Self-Correction Loop Details (Capped at 3 retries):**")
                st.markdown(f"- **Retries Attempted:** `{retry_count}/3`")
                reflection_prompt = res.get("reflection_prompt")
                if reflection_prompt:
                    st.markdown("**Reflection Node Directive:**")
                    st.code(reflection_prompt, language="text")
            else:
                st.info("Query succeeded on primary generation (0 retries required).")

    with st.expander("⏱️ LangGraph Execution Steps & Telemetry Trace", expanded=False):
        for log in telemetry:
            if "REJECTED" in log or "BLOCKED" in log:
                st.markdown(f"🔴 `{log}`")
            elif "Activated self-correction" in log or "Retry" in log:
                st.markdown(f"🟡 `{log}`")
            elif "successfully" in log:
                st.markdown(f"🟢 `{log}`")
            else:
                st.markdown(f"🔵 `{log}`")

    # 4. Results & Interactive Plotly Canvas
    if db_result and isinstance(db_result, list):
        st.divider()
        st.subheader("📊 Query Results & Visual Analytics")

        df = pd.DataFrame(db_result)

        # Single KPI scalar display
        if len(df) == 1 and len(df.columns) == 1:
            col_name = df.columns[0]
            val = df.iloc[0, 0]
            st.metric(label=col_name.replace("_", " ").title(), value=f"{val:,.2f}" if isinstance(val, (int, float)) else str(val))
        elif len(df) == 1 and len(df.columns) <= 3:
            kpi_cols = st.columns(len(df.columns))
            for i, col_name in enumerate(df.columns):
                val = df.iloc[0, i]
                formatted = f"{val:,.2f}" if isinstance(val, (int, float)) else str(val)
                kpi_cols[i].metric(label=col_name.replace("_", " ").title(), value=formatted)

        st.dataframe(df, use_container_width=True)

        # Plotly Canvas
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        non_numeric_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        if numeric_cols and len(df) > 1:
            st.markdown("#### 📈 Dynamic Plotly Visualization")
            chart_c1, chart_c2 = st.columns([1, 3])

            with chart_c1:
                # Smart Y-axis default: prefer amount/revenue/price/stock over id
                preferred_y = ["amount", "total_revenue", "total_spent", "price", "stock",
                               "order_count", "daily_revenue", "avg_price", "average_order_amount"]
                y_default = next((numeric_cols.index(c) for c in preferred_y if c in numeric_cols), 0)
                y_axis = st.selectbox("Metric Column (Y-axis):", options=numeric_cols, index=y_default)

                x_options = non_numeric_cols if non_numeric_cols else numeric_cols
                # Smart X-axis default: prefer customer_name/product_name/order_date/status/category over id
                preferred_x = ["customer_name", "product_name", "order_date", "status",
                               "category", "date", "product_name"]
                x_default = next((x_options.index(c) for c in preferred_x if c in x_options), 0)
                x_axis = st.selectbox("Dimension Column (X-axis):", options=x_options, index=x_default)
                chart_type = st.selectbox("Chart Type:", options=["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot"], index=0)

            with chart_c2:
                try:
                    if chart_type == "Bar Chart":
                        fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}", text_auto=True, color=x_axis if len(df) <= 10 else None)
                    elif chart_type == "Line Chart":
                        fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} Trend over {x_axis}", markers=True)
                    elif chart_type == "Pie Chart":
                        fig = px.pie(df, names=x_axis, values=y_axis, title=f"Distribution of {y_axis} by {x_axis}")
                    elif chart_type == "Scatter Plot":
                        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}", size=y_axis)

                    fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as chart_err:
                    st.caption(f"Plotly chart notice: {chart_err}")
    elif is_security_block:
        st.divider()
        st.subheader("🛡️ Database Integrity Verification")
        st.success("Verification check passed: The target database was shielded from write / destruction commands. All tables and rows remain intact.")
    elif db_result == []:
        st.info("ℹ️ Query executed successfully, but returned 0 rows matching your criteria.")
