from fastapi import FastAPI, Path, Request
from fastapi.responses import JSONResponse
import json
import os
import uvicorn
from urllib.parse import unquote

app = FastAPI()

@app.middleware("http")
async def decode_path(request: Request, call_next):
    path = request.url.path
    if path.startswith("//ivcap.local"):
        p = path[len('//ivcap.local'):]
        request.scope["path"] = p
    response = await call_next(request)
    return response

TEST_LOAD_PATH = os.path.join(os.path.dirname(__file__), "test-batch/tests/load_1.json")

from fastapi import Header

@app.get("/next_job")
async def next_job():
    try:
        with open(TEST_LOAD_PATH, "r") as f:
            content = json.load(f)
        headers = {"job-id": "0000-0000", "Authorization": "Bearer xxxxx"}
        return JSONResponse(content, headers=headers)
    except FileNotFoundError:
        return JSONResponse({"error": "test_load.json not found"}, status_code=404)

@app.post("/results/{job_id}")
async def results(job_id: str, request: Request):
    data = await request.json()
    print(f"Received results for job_id: {job_id}")
    print("Headers:")
    for key, value in request.headers.items():
        print(f"  {key}: {value}")
    print("Data:")
    print(json.dumps(data, indent=4))
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)
