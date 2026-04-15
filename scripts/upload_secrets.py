"""Upload secrets to Databricks secret scope.

Usage:
    1. Copy scripts/.env.example to scripts/.env and fill in your keys
    2. Run: uv run python scripts/upload_secrets.py
"""

import os

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ResourceAlreadyExists
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SCOPE = "llmops_course"

w = WorkspaceClient()

try:
    w.secrets.create_scope(scope=SCOPE)
    print(f"Created secret scope '{SCOPE}'")
except ResourceAlreadyExists:
    print(f"Secret scope '{SCOPE}' already exists")

openai_key = os.environ["OPENAI_KEY"]
w.secrets.put_secret(scope=SCOPE, key="openai_key", string_value=openai_key)
print("Uploaded openai_key (created or updated)")
