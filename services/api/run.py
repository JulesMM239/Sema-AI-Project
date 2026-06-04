# run.py
from main import app


if __name__ == '__main__':
    import uvicorn
    # Bind to 0.0.0.0 for Docker/Nginx reverse proxy
    uvicorn.run(app, host="0.0.0.0", port=8000)