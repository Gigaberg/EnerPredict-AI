from fastapi import FastAPI
from routes import household_routes, prediction_routes, solar_routes

# --- create app ---
app = FastAPI(title="AIRES Backend API")

# --- CORS middleware (allow your frontend origins during development) ---
from fastapi.middleware.cors import CORSMiddleware

from fastapi.middleware.cors import CORSMiddleware

# ... after app = FastAPI(...) ...

# Development-friendly CORS: allow your frontend origin(s)
# Replace or extend this list with any other dev origins you use.
# main.py (CORS middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",     # <-- add this
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- include routers ---
app.include_router(household_routes.router)
app.include_router(prediction_routes.router)
app.include_router(solar_routes.router)


@app.get("/")
async def root():
    return {"message": "AIRES Backend running"}

