# Minimal FastAPI app for Vercel routing
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
	return {"message": "Docs endpoint is alive."}