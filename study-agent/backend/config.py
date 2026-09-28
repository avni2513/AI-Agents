import os

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5001"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
