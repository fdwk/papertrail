from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from backend"}

@app.get("/poo/")
def read_poo():
    return {"message": "Pee poo"}
