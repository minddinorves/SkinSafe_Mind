import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()
app = FastAPI()

@app.post("/callback")
async def callback(request: Request):
    return "OK"