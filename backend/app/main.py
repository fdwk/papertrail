from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .papers import router as papers_router
from .trails import router as trails_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
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


app.include_router(auth_router)
app.include_router(trails_router)
app.include_router(papers_router)
