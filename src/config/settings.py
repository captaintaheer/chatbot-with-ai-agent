import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# API Configuration
API_TITLE = "Production Chatbot API"
API_DESCRIPTION = "A production-ready async chatbot API"
API_VERSION = "1.0.0"

# Model Configuration
MODEL_NAME =  "llama3-8b-8192" #"deepseek-reasoner"    
RATE_LIMIT_CALLS = 50
RATE_LIMIT_PERIOD = 60
BASE_URL="https://api.deepseek.com"

# Environment Variables
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") 

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO"
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO"
    }
}