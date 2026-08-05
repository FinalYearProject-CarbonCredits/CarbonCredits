# CarbonCredits

## Requirements
- Python 3.11+ (or compatible Python 3.x)
- pip

## Install dependencies
From the project root:

```bash
pip install -r backend/requirements.txt
```

If you need the dependencies individually:

```bash
pip install fastapi uvicorn sqlalchemy requests python-multipart
```

## Backend
Start the backend from the project root:

```bash
python backend/main.py
```

This will seed the database if needed and start the API server on:

- http://localhost:8000
- API docs: http://localhost:8000/docs

## Frontend
The frontend files live in `frontend/`.

Option 1: Use a static file server

```bash
cd frontend
python -m http.server 8080
```

Then open:

- http://127.0.0.1:8080

Option 2: Use VS Code Live Server
- Open `frontend/index.html`
- Start Live Server

> Note: the frontend talks to the backend API at `http://localhost:8000/api`, so make sure the backend is running first.



