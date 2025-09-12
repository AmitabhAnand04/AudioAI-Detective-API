import os
import shutil
import tempfile
from fastapi import BackgroundTasks, FastAPI, Request, UploadFile, File, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Dict, List


from service.process_audio_resemble import process_audio
from service.process_result_resemble import update_audio_data

app = FastAPI()

security = HTTPBasic()

# Hard-coded credentials (replace with env variables in production)
USERNAME = "admin"
PASSWORD = "secret123"

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if not (credentials.username == USERNAME and credentials.password == PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def background_task(file_path: str):
    try:
        results = process_audio(file_path)
        # Here you can save results to DB instead of just printing
        print(f"✅ Finished processing {file_path}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Deleted temp file {file_path}")


@app.post("/analyze-audio")
async def analyze_audio(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user: str = Depends(authenticate),
):
    file_paths = []

    for file in files:
        suffix = os.path.splitext(file.filename)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            file_paths.append(temp_file.name)

    # Schedule each file for background processing
    for path in file_paths:
        background_tasks.add_task(background_task, path)

    return {
        "message": f"Processing started for {len(file_paths)} file(s).",
        "files": [os.path.basename(p) for p in file_paths],
    }

@app.post("/resemble-callback")
async def resemble_callback(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()  # get raw JSON as dict

        # Extract uuid and metrics
        item = payload.get("item", {})
        file_uuid = item.get("uuid")
        metrics = item.get("metrics", {})

        print(f"Received callback for UUID: {file_uuid}")
        print(f"Metrics: {metrics}")

        # Run DB update in the background
        if file_uuid and metrics:
            background_tasks.add_task(update_audio_data, file_uuid, metrics)

        # Respond immediately
        return {"message": "Callback received, processing started in background"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process callback: {e}"
        )

# @app.post("/resemble-callback")
# async def resemble_callback(request: Request):
#     try:
#         payload = await request.json()  # get raw JSON as dict

#         # Extract uuid and metrics
#         item = payload.get("item", {})
#         file_uuid = item.get("uuid")
#         metrics = item.get("metrics", {})

#         print(f"Received callback for UUID: {file_uuid}")
#         print(f"Metrics: {metrics}")

#         # TODO: do further processing (DB update, aggregation, etc.)
#         update_audio_data(file_uuid, metrics)

#         return {"message": "Callback received successfully"}

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to process callback: {e}"
#         )

# @app.post("/analyze-audio")
# async def analyze_audio(file: UploadFile = File(...), user: str = Depends(authenticate)):
#     # Create a temporary file
#     suffix = os.path.splitext(file.filename)[-1]
#     with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
#         shutil.copyfileobj(file.file, temp_file)
#         temp_file_path = temp_file.name

#     try:
#         # Call your function
#         results = process_audio(temp_file_path)
#         return results
#     finally:
#         # Cleanup temp file
#         if os.path.exists(temp_file_path):
#             os.remove(temp_file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)