import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import include_api
from common.app.core.config import config as cfg
from common.app.db import db_pool, create_db
from backend.app.api.web_socket import app_ws as websocket_app
from backend.app.api.web_socket_doc import router as websocket_docs

app = FastAPI()

# Монтирование приложения WebSocket как подприложения
app.mount("/ws", websocket_app)

api_router = APIRouter()
include_api(api_router)
app.include_router(api_router)
"""
Add CORS middleware support
The middleware responds to certain types of HTTP requests. It adds appropriate CORS headers to the response
CORS or "Cross-Origin Resource Sharing" refers to situations when a frontend running in a browser has JavaScript code
that communicates with a backend, and the backend is in a different "origin" than the frontend.
"""

origins = [
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["*"]

)


# Function to be called when the server starts
@app.on_event("startup")
async def open_pool():
    await db_pool.init_pool(cfg)
    await create_db.init_db()
    logging.debug(f'=> pool open:')


# Function to be called when the server shuts down
@app.on_event("shutdown")
async def close_pool():
    await db_pool.close_pool()
    logging.debug('=> pool close /)')
