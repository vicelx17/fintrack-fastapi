from fastapi import FastAPI

app = FastAPI(title="FinTrack API")

@app.get("/")
def root():
    return {"message": "FinTrack API funcionando 🚀"}
