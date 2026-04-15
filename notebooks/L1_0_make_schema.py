# Databricks notebook source
# Notebook to create schema for the course.
# You can run this notebook multiple times without error,
# as it uses "IF NOT EXISTS" in the SQL commands.

from loguru import logger
from pyspark.sql import SparkSession

# COMMAND ----------
# Create Spark session
spark = SparkSession.builder.getOrCreate()

# Schema name
CATALOG = "llmops_martijn"
SCHEMA = "arxiv"  # Change this to your desired schema name

# Create schema if it doesn't exist
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
logger.info(f"Schema {CATALOG}.{SCHEMA} ready")

# COMMAND ----------
