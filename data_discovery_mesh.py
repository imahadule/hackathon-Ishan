# Directory: data_discovery_ai_datamesh

# === BACKEND ===
# File: backend/ingest_metadata.py
import json
import os
from typing import List, Dict

MOCK_METADATA = [
    {"table": "customer_churn", "domain": "marketing", "columns": ["id", "churn", "date"], "owner": "alice", "freshness": "daily", "pii": True},
    {"table": "transactions", "domain": "finance", "columns": ["txn_id", "amount", "timestamp"], "owner": "bob", "freshness": "hourly", "pii": False},
    {"table": "feedback", "domain": "product", "columns": ["user_id", "rating", "comment"], "owner": "carol", "freshness": "weekly", "pii": True},
]

def ingest_metadata() -> List[Dict]:
    with open("backend/metadata.json", "w") as f:
        json.dump(MOCK_METADATA, f, indent=2)
    return MOCK_METADATA

if __name__ == "__main__":
    ingest_metadata()

# === BACKEND ===
# File: backend/embedding_service.py
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import faiss
import os

EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def generate_embeddings(metadata_path: str = "backend/metadata.json"):
    with open(metadata_path) as f:
        metadata = json.load(f)

    corpus = [f"{entry['table']} {entry['domain']} {' '.join(entry['columns'])}" for entry in metadata]
    embeddings = EMBEDDING_MODEL.encode(corpus, show_progress_bar=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    faiss.write_index(index, "backend/faiss.index")
    with open("backend/corpus.json", "w") as f:
        json.dump(corpus, f)
    return corpus

if __name__ == "__main__":
    generate_embeddings()

# === BACKEND ===
# File: backend/rag_pipeline.py
import openai
import faiss
import numpy as np
import json
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def query_rag(user_query: str):
    index = faiss.read_index("backend/faiss.index")
    with open("backend/corpus.json") as f:
        corpus = json.load(f)

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_embedding = model.encode([user_query])

    D, I = index.search(np.array(query_embedding).astype("float32"), k=3)
    matched = [corpus[i] for i in I[0]]

    context = "\n".join(matched)
    prompt = f"You are a data discovery assistant. Based on the metadata below, answer the user's question.\n\nMetadata:\n{context}\n\nUser: {user_query}\nAnswer:"

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"]

# === BACKEND ===
# File: backend/automl_profiler.py
import random

def simulate_profile(table_name: str):
    profiling = {
        "pii_detected": random.choice([True, False]),
        "anomalies": random.choice(["none", "high nulls", "skewed distribution"]),
        "recommended_model": random.choice(["RandomForest", "XGBoost", "LogisticRegression"])
    }
    return {"table": table_name, "profiling_summary": profiling}

# === BACKEND ===
# File: backend/mlflow_logger.py
import mlflow
import random

def log_metadata_analysis(table: str, profiling_summary: dict):
    with mlflow.start_run(run_name=f"Profiling_{table}"):
        mlflow.log_param("table", table)
        for key, val in profiling_summary.items():
            mlflow.log_param(key, val)
        mlflow.log_metric("profiling_score", random.uniform(0.7, 0.99))

# === FRONTEND ===
# File: frontend/app.py
import streamlit as st
from backend.rag_pipeline import query_rag
from backend.automl_profiler import simulate_profile
from backend.mlflow_logger import log_metadata_analysis

st.set_page_config(page_title="AI Data Discovery on Data Mesh", layout="centered")
st.title("🔍 AI-Powered Data Discovery")

query = st.text_input("Ask a question about your data products:", placeholder="e.g. Which dataset has customer churn info?")

if query:
    with st.spinner("Thinking..."):
        answer = query_rag(query)
    st.success("Answer:")
    st.write(answer)

    if st.toggle("Show raw metadata used in this answer"):
        st.code(answer, language="text")

    if st.button("Simulate AutoML Profiling"):
        table = answer.split()[0]  # crude example to extract table name
        profile = simulate_profile(table)
        st.subheader("📊 AutoML Profiling Results")
        st.json(profile["profiling_summary"])
        log_metadata_analysis(table, profile["profiling_summary"])
        st.info("Profiling logged to MLflow")
