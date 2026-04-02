from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .papers import router as papers_router
from .trails import router as trails_router

import logging
from rich.logging import RichHandler

import resend

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("backend")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://papertrail-frontend-production.up.railway.app",
        "https://www.papertrail.wiki",
        "https://papertrail.wiki",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from backend"}


@app.get("/poo/")
def read_poo():
    return {"message": "Pee poo"}

import os
resend.api_key = os.getenv("RESEND_API_KEY", "").strip()

@app.get("/send-email")
def send_mail():
    params: resend.Emails.SendParams = {
        "from": "Papertrail <no-reply@send.papertrail.wiki>",
        "to": ["fran.kahng@gmail.com"],
        "subject": "hello world",
        "html": "<strong>it works!</strong>",
    }
    email: resend.Emails.SendResponse = resend.Emails.send(params)
    return email

app.include_router(auth_router)
app.include_router(trails_router)
app.include_router(papers_router)
