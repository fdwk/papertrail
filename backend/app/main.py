from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from backend"}

@app.get("/pook")
def read_root():
    return {"message": "Pee poo"}