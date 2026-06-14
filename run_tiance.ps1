$ErrorActionPreference = "Stop"
python -m uvicorn tiance.main:create_app --factory --host 127.0.0.1 --port 8000
