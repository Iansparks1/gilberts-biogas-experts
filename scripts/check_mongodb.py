import os
import sys
from urllib.parse import unquote, urlsplit

from pymongo import MongoClient


uri = os.environ["MONGODB_URI"]
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    client.close()
    print("ATLAS_PING_OK")
except Exception as error:
    message = str(error)
    parsed_uri = urlsplit(uri)
    for secret in (uri, parsed_uri.password, unquote(parsed_uri.password or "")):
        if secret:
            message = message.replace(secret, "<redacted>")
    print(f"ATLAS_PING_FAILED: {type(error).__name__}: {message}")
    sys.exit(1)
