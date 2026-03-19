# wsgi.py

from src.core.health_server import app  # change if your Flask/FastAPI entry file is different

if __name__ == "__main__":
    app.run()