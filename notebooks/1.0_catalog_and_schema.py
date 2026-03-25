# Databricks notebook source

from loguru import logger
from pyspark.sql import SparkSession

# COMMAND ----------
# Create Spark session
spark = SparkSession.builder.getOrCreate()

# Schema name 
CATALOG = "llmops_dev"
SCHEMA = "arxiv"  # Change this to your desired schema name

# Create catalog if it doesn't exist
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
logger.info(f"Catalog {CATALOG} ready")

# Create schema if it doesn't exist
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
logger.info(f"Schema {CATALOG}.{SCHEMA} ready")
# COMMAND ----------
