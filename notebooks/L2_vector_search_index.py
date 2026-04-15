# Databricks notebook source
# MAGIC %md
# MAGIC # Embeddings & Vector Search
# MAGIC
# MAGIC Build a semantic search layer over the arXiv chunks:
# MAGIC
# MAGIC 1. **Setup** — provision (or reuse) a Vector Search endpoint and a
# MAGIC    delta-sync index over `arxiv_chunks_table`, auto-embedding the
# MAGIC    `text` column with `databricks-gte-large-en`. Trigger the initial
# MAGIC    sync.
# MAGIC 2. **Filtered search** — run a similarity query with a metadata
# MAGIC    filter (e.g. `year = 2026`).
# MAGIC 3. **Strategy comparison** — run the same query through three
# MAGIC    retrieval strategies and compare results side-by-side:
# MAGIC    - basic semantic search (bi-encoder only)
# MAGIC    - hybrid search (semantic + BM25 keyword)
# MAGIC    - hybrid + cross-encoder reranking via `DatabricksReranker`
# MAGIC 4. **Monitoring & cleanup** — inspect index health, list indexes on
# MAGIC    the endpoint, and (commented out) tear-down calls to stop billing.
# MAGIC
# MAGIC All endpoint/index lifecycle is handled by `VectorSearchManager` from
# MAGIC the `arxiv_curator` package, so the notebook stays thin and the logic
# MAGIC is reusable from jobs.
# MAGIC
# MAGIC ## Vector Search Architecture
# MAGIC
# MAGIC ```
# MAGIC ┌─────────────────────────────────────────┐
# MAGIC │     Delta Table (arxiv_chunks)          │
# MAGIC │  - id                                   │
# MAGIC │  - text                                 │
# MAGIC │  - metadata (title, author, etc.)       │
# MAGIC └──────────────┬──────────────────────────┘
# MAGIC                │
# MAGIC                │ (Automatic sync)
# MAGIC                ↓
# MAGIC ┌─────────────────────────────────────────┐
# MAGIC │     Vector Search Index                 │
# MAGIC │  - Embeddings generated automatically   │
# MAGIC │  - Stored in optimized format           │
# MAGIC │  - Supports similarity search           │
# MAGIC └──────────────┬──────────────────────────┘
# MAGIC                │
# MAGIC                │ (Query)
# MAGIC                ↓
# MAGIC ┌─────────────────────────────────────────┐
# MAGIC │     Search Results                      │
# MAGIC │  - Most similar chunks                  │
# MAGIC │  - With similarity scores               │
# MAGIC └─────────────────────────────────────────┘
# MAGIC ```

# COMMAND ----------

from databricks.vector_search.reranker import DatabricksReranker
from loguru import logger
from pyspark.sql import SparkSession

from arxiv_curator.config import get_env, load_config
from arxiv_curator.vector_search import VectorSearchManager

# COMMAND ----------

# Setup Spark session
spark = SparkSession.builder.getOrCreate()

# Load configuration
env = get_env(spark)
cfg = load_config("../project_config.yml", env)
catalog = cfg.catalog
schema = cfg.schema

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup Vector Search Endpoint & Index

# COMMAND ----------

# Initialize Vector Search Endpoint class
# Using VectorSearchManager from arxiv_curator.vector_search
# This handles endpoint and index creation automatically

vs_manager = VectorSearchManager(
    config=cfg,
    endpoint_name=cfg.vector_search_endpoint,
    embedding_model=cfg.embedding_endpoint,
)

logger.info(f"Vector Search Endpoint: {vs_manager.endpoint_name}")
logger.info(f"Embedding Model: {vs_manager.embedding_model}")
logger.info(f"Index Name: {vs_manager.index_name}")

# COMMAND ----------

# Deploy Vector Search Endpoint if not already deployed

vs_manager.create_endpoint_if_not_exists()

# COMMAND ----------

# Create or get the vector search index (on the endpoint) using VectorSearchManager
# This automatically:
# - Creates the index if it doesn't exist
# - Configures it with the embedding model
# - Sets up delta sync with the arxiv_chunks table

index = vs_manager.create_or_get_index()

logger.info("\n✓ Vector search setup complete!")
logger.info(f"  Index: {vs_manager.index_name}")
logger.info(f"  Source: {vs_manager.catalog}.{vs_manager.schema}.arxiv_chunks")
logger.info(f"  Embedding Model: {vs_manager.embedding_model}")

# COMMAND ----------

# Trigger initial sync (for TRIGGERED pipeline)
vs_manager.sync_index()

# COMMAND ----------

# Helper Function for Parsing Results


def parse_vector_search_results(results: dict) -> list[dict]:
    """Parse vector search results from array format to dict format.

    Args:
        results: Raw results from similarity_search()

    Returns:
        List of dictionaries with column names as keys
    """
    columns = [col["name"] for col in results.get("manifest", {}).get("columns", [])]
    data_array = results.get("result", {}).get("data_array", [])

    return [dict(zip(columns, row_data, strict=True)) for row_data in data_array]


# COMMAND ----------

# MAGIC %md
# MAGIC ## Filter Examples:
# MAGIC
# MAGIC ```python
# MAGIC # Single filter
# MAGIC filters = {"year": "2024"}
# MAGIC
# MAGIC # Multiple filters (AND)
# MAGIC filters = {"year": "2024", "month": "01"}
# MAGIC
# MAGIC # Range filter
# MAGIC filters = {"year >= 2023"}
# MAGIC ```

# COMMAND ----------

query = "neural networks and deep learning"

# Filter for papers from 2026
results = index.similarity_search(
    query_text=query,
    columns=["text", "id", "title", "year", "authors"],
    filters={"year": "2026"},  # Only papers from 2026
    num_results=3,
)

logger.info(f"Query: {query}")
logger.info("Filter: year = 2026\n")
logger.info("Results:")
logger.info("=" * 80)

for i, row in enumerate(parse_vector_search_results(results), 1):
    logger.info(f"\n{i}. {row.get('title', 'N/A')}")
    logger.info(f"   Year: {row.get('year', 'N/A')}")
    authors = row.get("authors", "N/A")
    logger.info(f"   Authors: {str(authors)[:100]}...")
    logger.info(f"   Text: {row.get('text', '')[:150]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compare different search strategies

# COMMAND ----------
query = "non-linear optimization algorithms"

logger.info(f"Query: {query}\n")

# Strategy 1: Basic semantic search
results_basic = index.similarity_search(
    query_text=query, columns=["text", "title"], num_results=3
)

logger.info("Strategy 1: Basic Semantic Search")
logger.info("-" * 80)
for i, row in enumerate(parse_vector_search_results(results_basic), 1):
    logger.info(f"{i}. {row.get('title', 'N/A')[:60]}...")

# Strategy 2: Hybrid search
results_hybrid = index.similarity_search(
    query_text=query, columns=["text", "title"], num_results=3, query_type="hybrid"
)

logger.info("\nStrategy 2: Hybrid Search")
logger.info("-" * 80)
for i, row in enumerate(parse_vector_search_results(results_hybrid), 1):
    logger.info(f"{i}. {row.get('title', 'N/A')[:60]}...")

# Strategy 3: Hybrid + Reranking
results_reranked = index.similarity_search(
    query_text=query,
    columns=["text", "title"],
    num_results=3,
    query_type="hybrid",
    reranker=DatabricksReranker(columns_to_rerank=["text", "title"]),
)

logger.info("\nStrategy 3: Hybrid + Reranking")
logger.info("-" * 80)
for i, row in enumerate(parse_vector_search_results(results_reranked), 1):
    logger.info(f"{i}. {row.get('title', 'N/A')[:60]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Monitoring and Maintenance

# COMMAND ----------

# Check index status
index_info = vs_manager.client.get_index(
    endpoint_name=vs_manager.endpoint_name, index_name=vs_manager.index_name
)

logger.info("Index Information:")
logger.info(f"  Name: {index_info.name}")
logger.info(f"  Endpoint: {index_info.endpoint_name}")

# List all indexes on the endpoint
logger.info(vs_manager.client.list_indexes(name=vs_manager.endpoint_name))

# Delete index (if needed)
# vs_manager.client.delete_index(index_name=vs_manager.index_name)

# Delete endpoint (if needed)
# vs_manager.client.delete_endpoint(name=vs_manager.endpoint_name)
