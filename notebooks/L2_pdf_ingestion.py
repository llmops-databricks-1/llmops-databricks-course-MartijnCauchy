# Databricks notebook source
# MAGIC %md
# MAGIC # End-to-end ingestion pipeline for arXiv papers:
# MAGIC
# MAGIC 1. **Download** — fetch PDFs from arXiv into a Unity Catalog volume and
# MAGIC    register them in the `arxiv_papers` table.
# MAGIC 2. **Parse** — extract text from each PDF using the built-in
# MAGIC    `ai_parse_document` SQL function, writing results to `arxiv_parsed`.
# MAGIC 3. **Chunk** — split parsed text into embedding-ready chunks and store
# MAGIC    them in `arxiv_chunks_table` (the source table consumed by the
# MAGIC    Vector Search index).
# MAGIC
# MAGIC All three steps are orchestrated through `DataProcessor` from the
# MAGIC `arxiv_curator` package, so the notebook stays thin and the logic is
# MAGIC reusable from jobs.

# COMMAND ----------

from databricks.connect import DatabricksSession
from loguru import logger

from arxiv_curator.config import get_env, load_config
from arxiv_curator.data_processor import DataProcessor

# COMMAND ----------

spark = DatabricksSession.builder.getOrCreate()
logger.info("✅ Using Databricks Connect Spark session")

env = get_env(spark)
cfg = load_config("../project_config.yml", env)

# Initialize the DataProcessor (reusable class from arxiv_curator package)
processor = DataProcessor(spark=spark, config=cfg)

logger.info(f"Catalog: {cfg.catalog}, Schema: {cfg.schema}, Volume: {cfg.volume}")

# COMMAND ----------

# Start processing pipeline
processor.process_and_save()
