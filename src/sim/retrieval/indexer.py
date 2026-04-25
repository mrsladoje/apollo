import sqlite3
import os
from datetime import datetime
from pylate import indexes, models

def build_index(historian_path: str = "historian.db", index_path: str = "data/lateon.index"):
    """Build the ColBERT retrieval index as defined in §12.1."""
    
    # 1. Setup model and index
    model = models.ColBERT("lightonai/lateon-code-edge")
    index = indexes.PLAID(index_folder=index_path, override=True)
    
    # 2. Extract rows from historian
    conn = sqlite3.connect(historian_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT run_id, component_id, t, health, status, metrics_json 
        FROM component_states
    """).fetchall()
    
    docs, doc_ids = [], []
    for row in rows:
        doc_id = f"{row['run_id']}|{row['component_id']}|{row['t']}"
        
        # Build token-dense snippet §12.2
        snippet = (
            f"[run={row['run_id']}] [component={row['component_id']}] [t={row['t']}] "
            f"[status={row['status']}] [health={row['health']:.2f}] "
            f"metrics={row['metrics_json']}"
        )
        
        docs.append(snippet)
        doc_ids.append(doc_id)
        
    # 3. Encode and Index
    print(f"Indexing {len(docs)} documents...")
    embeddings = model.encode(docs, is_query=False)
    index.add_documents(documents_ids=doc_ids, documents_embeddings=embeddings)
    
    print(f"Index built successfully at {index_path}")
    conn.close()

if __name__ == "__main__":
    build_index()
