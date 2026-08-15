# GenAI-InsightIQ 🚀
> **Full-Stack AI Data Analytics, Automated Business Intelligence & AutoML Platform**

GenAI-InsightIQ is an end-to-end data intelligence web application that transforms raw, messy datasets into interactive dashboards, automated KPI models, machine learning predictions, and AI-assisted data conversations.

---

## ✨ Key Features

### 📊 1. Data Ingestion & Auto-Profiling
- **Multi-Format Ingestion**: Supports `.csv`, `.xlsx` (multi-sheet), and `.json` files.
- **Smart Data Coercion**: Automatically detects and cleans formatted numeric strings (currency symbols `$`, `€`, `£`, `¥`, `,`, `%`) into numeric floats.
- **Health & Quality Audit**: Real-time reporting on missing values, duplicate rows, constant columns, and identifier patterns.

### 📐 2. Automated KPI & DAX Engine
- **Column Classification**: Intelligently categorizes columns into `MEASURE`, `DIMENSION`, `IDENTIFIER`, `COORDINATE`, and `FREE_TEXT`.
- **KPI Recommendation**: Automatically generates high-value metrics with DAX formula equivalents (e.g. `SUM([property_loss_usd])`).
- **Dashboard Action Wiring**: One-click addition of KPI cards directly into the Analytics workspace.

### 📈 3. Smart Chart Engine & Interactive Analytics
- **Recommended Visualizations**: Generates optimal Recharts configs (Bar, Line, Scatter, Table) enforcing cardinality constraints and variety limits.
- **Dynamic Aggregations**: Supports Sum, Mean, Median, Count, Date-Granularity grouping, and Scatter sampling.

### 🤖 4. AutoML Training & Interactive Prediction Playground
- **Automated Target Detection**: Classifies targets for Binary Classification, Multi-class Classification, or Regression.
- **Model Suite**: Evaluates and trains Random Forest, Logistic Regression, Decision Trees, Ridge Regression, and Linear Models with baseline sanity checks.
- **Evaluation Metrics**: Comprehensive breakdown of Accuracy, F1-Score, ROC-AUC, Precision, Recall, MSE, RMSE, R², and Feature Importance rankings.
- **Predictive Playground**: Interactive UI for real-time model inference on custom inputs.
- **Export Engine**: Export trained models (`.joblib`), predictions (`.csv`), metric summaries (`.json`), or standalone Python inference code (`.py`).

### 💬 5. Data Chat with Tool-Calling & Chat-to-Action Wiring
- **Powered by Local Ollama (`llama3.2:3b`)**: Zero data privacy leakage — runs entirely locally.
- **Tool-Calling Architecture**: Integrates real tool execution (`calculate_statistic`, `aggregate_data`, `find_top_categories`, `recommend_chart`, `get_dataset_summary`).
- **Chat-to-Action Wiring**: Renders actionable buttons ("Create Chart", "Add to Dashboard") directly below tool output cards.
- **Strict Anti-Hallucination Directives**: Enforces hard rules preventing fabricated numbers or ungrounded statistics.
- **Streaming Responses**: Real-time server-sent streaming (SSE) for instant text output.

### 🧹 6. Categorical Fuzzy & Prefix Normalization
- **Fuzzy & Case Normalization**: Merges whitespace variants and typos (`length >= 4`, `similarity >= 0.85`).
- **Prefix Abbreviation Merging**: Merges short prefix abbreviations (`Nor` $\rightarrow$ `North`/`Northeast`, `Sou` $\rightarrow$ `South`/`Southwest`) into canonical groups while surfacing ambiguity warnings when multiple matches exist.

---

## 🛠️ Architecture & Tech Stack

```
                     ┌──────────────────────────────────────┐
                     │          React + TypeScript          │
                     │  (Vite + TailwindCSS + Recharts)     │
                     └──────────────────┬───────────────────┘
                                        │ REST / SSE
                     ┌──────────────────▼───────────────────┐
                     │          FastAPI Backend             │
                     │       (Python 3.14 + Pandas)         │
                     └─────────┬──────────────────┬─────────┘
                               │                  │
               ┌───────────────▼──────┐    ┌──────▼──────────────┐
               │    Local Ollama      │    │    Scikit-Learn     │
               │  (llama3.2:3b LLM)   │    │   AutoML Engine     │
               └──────────────────────┘    └─────────────────────┘
```

- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Recharts, Lucide Icons, React Markdown.
- **Backend**: Python 3.14, FastAPI, Pandas, NumPy, Scikit-Learn, Joblib, Pytest.
- **AI/LLM**: Local Ollama Server (`llama3.2:3b`).

---

## 🚀 Quickstart Guide

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- [Ollama](https://ollama.com) installed locally

### 1. Start Ollama Model
```bash
ollama pull llama3.2:3b
ollama serve
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # On Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Testing

Run the comprehensive Pytest backend test suite (106 tests):
```bash
cd backend
.\venv\Scripts\pytest tests/ -v
```

---

## 📄 License
MIT License. Developed for intelligent automated business intelligence & machine learning.
