# SQL & Database Analytics Agent
- **Repository**: [Insert URL]

An enterprise-ready text-to-SQL analytics agent designed with **LangGraph**, featuring an automated **Self-Correction Reflection Loop**, **Abstract Syntax Tree (AST)** security filters, **NeMo Guardrails** input protection, and an interactive **Streamlit** analytics dashboard powered by **Plotly**.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       User Question / Query Input     |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   NeMo Guardrails (Input Scanning)   |
                      |  (Blocks SQL Injections, Tautologies, |
                      |    Comment Expansions, Script Tags)   |
                      +---------------------------------------+
                                          |
                                          | Passed
                                          v
                     +-----------------------------------------+
                     |          LangGraph StateGraph           |
                     |                                         |
                     |  [inspect_schema_node]                  |
                     |         | (SQLAlchemy Reflection)       |
                     |         v                               |
                     |  [generate_sql_node] <---------------+  |
                     |         | (LLM Text-to-SQL)          |  |
                     |         v                            |  |
                     |  (AST Safety Filter: sqlparse)       |  |
                     |         |                            |  |
                     |         v                            |  |
                     |  [execute_query_node]                |  |
                     |         |                            |  |
                     |    Error?                            |  |
                     |    /     \                           |  |
                     |  Yes      No                         |  |
                     |   |        \                         |  |
                     |   v         v                        |  |
                     | [reflection] [END] -> Streamlit UI   |  |
                     |   (max 3)         & Plotly Canvas    |  |
                     +-----------------------------------------+
```

### Key Modules:
- **`app/agent.py`**: State machine in LangGraph (`StateGraph`). Manages state dictionary (`user_query`, `generated_sql`, `db_result`, `error_message`, `retry_count`), coordinates nodes (`inspect_schema_node`, `generate_sql_node`, `execute_query_node`, `reflection_node`), and enforces a 3-retry maximum reflection cap.
- **`app/guardrails.py` & `config/guardrails/`**: Two-stage security perimeter:
  1. **NeMo Guardrails**: Scans raw user input before reaching LLM, blocking tautologies (`1=1`), comment expansions (`--`, `/*`), script tags (`<script>`), and destructive commands.
  2. **AST SQL Parser (`is_safe_select_only`)**: Analyzes statements via `sqlparse` AST, enforcing strictly read-only queries (SELECT) and rejecting write commands (`DELETE`, `DROP`, `UPDATE`, `INSERT`, `ALTER`, etc.).
- **`app/db.py` & `seed_db.py`**: SQLAlchemy database connector supporting SQLite and PostgreSQL. Provides schema reflection (`inspect(engine)`) and seeds sample `orders` and `products` tables.
- **`app.py`**: Interactive Streamlit dashboard with collapsible query logs, telemetry timelines, and dynamic Plotly visualizations.
- **`tests/`**: Comprehensive pytest test suite validating AST write blocks, NeMo input guardrails, and self-correction reflection recovery loops.

---

## Quickstart (Windows .bat Launcher)

Double-click or run [`run.bat`](file:///c:/Users/Abhi/Downloads/a5/run.bat) to launch the interactive menu:
```cmd
run.bat
```
Or run directly via command-line flags:
- `run.bat all` - Seeds database, runs all 15 tests, and launches the UI dashboard
- `run.bat ui` - Launches Streamlit analytics dashboard directly
- `run.bat test` - Runs full automated test suite (`pytest`)
- `run.bat seed` - Seeds sample `orders` and `products` tables
- `run.bat install` - Installs Python dependencies

---

## Installation

### 1. Configure `.env` file
Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```
Contents of `.env`:
```ini
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///analytics.db
```
*(Note: If `OPENAI_API_KEY` is omitted, the agent automatically activates an offline heuristic generator that demonstrates full text-to-SQL generation and dynamic reflection recovery).*

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Seed Database
Initialize and seed the database with required sample tables (`orders` with `id`, `order_date`, etc.):
```bash
python seed_db.py
```

### 4. Run Streamlit UI
```bash
streamlit run app.py
```

### 5. Run tests
```bash
pytest
```
*(or `python -m pytest -v`)*

---

## Verification & Validation Test Cases

The project satisfies all required test cases specified in the evaluation brief:

### Test Case 1: SQL Self-Correction column-reference recovery loop
1. Seed database using `python seed_db.py`.
2. Start the Streamlit application: `streamlit run app.py`.
3. In the sidebar, select **"Simulate Column Error (Self-Correction Test)"** and run query:
   `Show orders sorted by date`
4. **Result:**
   - On attempt 1, the model simulates generating a query using non-existent column `created_at`.
   - `execute_query_node` catches `no such column: created_at`.
   - `reflection_node` activates (Retry 1/3), inspects schema metadata, and synthesizes a correction directive with valid column `order_date`.
   - `generate_sql_node` rewrites query to `SELECT ... FROM orders ORDER BY order_date ASC`.
   - Results are rendered in the table and Plotly chart canvas.

### Test Case 2: AST Safety Filter & SQL Injection Block
1. In Streamlit or test suite, input the malicious attack query:
   `DROP TABLE orders; --`
2. **Result:**
   - NeMo Guardrails and the AST safety filter intercept the command before execution.
   - A security warning is displayed: `Security Warning [NeMo Guardrails]: Destructive SQL statement injection detected`.
   - The query is aborted without querying the database.
   - The `orders` table remains completely intact.

### Test Case 3: Automated Test Suite Execution
Run the full test suite:
```bash
pytest -v
```
All 15 tests verify:
- AST write operation rejection (`DELETE`, `DROP`, `INSERT`, `UPDATE`, `ALTER`, multi-statement injections).
- NeMo Guardrails input moderation (tautologies, comments, script tags).
- SQLAlchemy schema reflection and database integrity.
- Mocked database errors and self-correction loop recovery.
- Maximum 3-retry cap enforcement.

---

## Monorepo Project Layout

```
.
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── README.md                 # Project documentation and evaluation guide
├── requirements.txt          # Python package dependencies
├── seed_db.py                # Database seeder script
├── app.py                    # Streamlit Dashboard application entrypoint
├── app/
│   ├── __init__.py
│   ├── agent.py              # LangGraph StateGraph Text-to-SQL & Reflection loop
│   ├── db.py                 # SQLAlchemy connection & schema inspection
│   └── guardrails.py         # AST sqlparse analyzer & NeMo Guardrails scanner
├── config/
│   └── guardrails/
│       ├── actions.py        # NeMo custom input safety actions
│       └── config.yml        # NeMo Guardrails 2.x configuration
└── tests/
    ├── __init__.py
    ├── test_ast_guardrails.py# Pytest suite for AST and NeMo filters
    ├── test_db.py            # Pytest suite for DB reflection & integrity
    └── test_self_correction.py# Pytest suite for LangGraph reflection recovery loop
```
