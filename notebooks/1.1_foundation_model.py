# Databricks notebook source
# MAGIC %md
# MAGIC # Lecture 1.1: Foundation Model
# MAGIC 1. **Foundation Model APIs (Pay-per-token)**
# MAGIC    - Serverless, fully managed
# MAGIC    - Pay only for what you use
# MAGIC    - No infrastructure management
# MAGIC    - Examples: Meta Llama, Mistral, DBRX, DeepSeek

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from loguru import logger
from openai import OpenAI

# Initialize workspace client
w = WorkspaceClient()

# COMMAND ----------

# List available foundation models
endpoints = w.serving_endpoints.list()

logger.info("Available Foundation Model Endpoints:")
logger.info("-" * 80)
for endpoint in endpoints:
    if endpoint.name and "databricks" in endpoint.name:
        logger.info(f"Name: {endpoint.name}")
        logger.info(f"State: {endpoint.state}")
        logger.info("-" * 80)

# COMMAND ----------

# Set up the OpenAI client pointing at our workspace's serving endpoints.
host = w.config.host
token = w.tokens.create(lifetime_seconds=1200).token_value

client = OpenAI(
    api_key=token,
    base_url=f"{host}/serving-endpoints",
)

# COMMAND ----------

# MAGIC %md
# MAGIC Test which endpoints your account tier (free) can actually call.
# MAGIC Sends a minimal request (1 token) to each databricks-* endpoint.
# MAGIC Not all endpoints support chat — embedding models will fail with a different error.

# COMMAND ----------
endpoints = w.serving_endpoints.list()
for endpoint in endpoints:
    if endpoint.name and "databricks" in endpoint.name:
        try:
            r = client.chat.completions.create(
                model=endpoint.name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1,
            )
            logger.info(f"{endpoint.name}: WORKS")
        except Exception as e:
            logger.warning(f"{endpoint.name}: BLOCKED - {str(e)[:80]}")

# COMMAND ----------

# Asking a real question
#model_name = "databricks-llama-4-maverick"
model_name ="databricks-gemma-3-12b"
# Ask a question to a Databricks-hosted Llama model.
response = client.chat.completions.create(
    model = model_name,
    messages=[
        {"role": "system", "content": "You are a comedian. Be funny."},
        {"role": "user", "content": "Tell me a joke about dutch people."},
    ],
    max_tokens=200,
         # Temperature ontrols randomness: 0.0 = deterministic, 1.0 = more creative/random
    temperature=0.7
)

logger.info("Response:")
logger.info(response.choices[0].message.content)
logger.info(f"Tokens used: {response.usage.total_tokens}")
logger.info(f"Input tokens: {response.usage.prompt_tokens}")
logger.info(f"Output tokens: {response.usage.completion_tokens}")

# COMMAND ----------
