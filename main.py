import json
import os
import shutil
import tempfile
from fastapi import BackgroundTasks, FastAPI, Request, UploadFile, File, Depends, HTTPException, status
from fastapi.params import Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Dict, List
from psycopg2.extras import RealDictCursor
from fastapi.middleware.cors import CORSMiddleware
from service.db_service import connect_to_db
from service.process_audio_resemble import process_audio
from service.process_result_resemble import update_audio_data
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

USERNAME = os.getenv("Auth_USERNAME", "admin")
PASSWORD = os.getenv("Auth_PASSWORD", "password")
security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if not (credentials.username == USERNAME and credentials.password == PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

app = FastAPI(
    title="AI vs Human Voice Detective API",
    description="Accepts an audio file and returns details detection report per segment and more.",
    version="1.0.0"
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
# Allow cross-origin requests if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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

    # for file in files:
    #     suffix = os.path.splitext(file.filename)[-1]
    #     with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
    #         shutil.copyfileobj(file.file, temp_file)
    #         file_paths.append(temp_file.name)
    for file in files:
        safe_filename = file.filename.replace(" ", "_")   # replace spaces
        temp_path = os.path.join(tempfile.gettempdir(), safe_filename)
        with open(temp_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
        file_paths.append(temp_path)


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

@app.get("/get-results")
async def get_results(file_name: str = Query(..., description="File name to fetch results for"), user: str = Depends(authenticate)):
    cur, conn = connect_to_db()
    cur.execute("SELECT * FROM audio_data WHERE file_name = %s", (file_name,))
    rows = cur.fetchall()

    colnames = [desc[0] for desc in cur.description]  # get column names
    cur.close()
    conn.close()

    if not rows:
        return JSONResponse({"error": "No records found"}, status_code=404)

    # Extract original_file_url from first row
    first_row_dict = dict(zip(colnames, rows[0]))
    original_file_url = first_row_dict.get("original_file_url")

    response = {
        "file_name": file_name,
        "file_url": original_file_url,  # add at top-level
        "segments": []
    }

    for row in rows:
        row_dict = dict(zip(colnames, row))  # map tuple → dict

        transcriptions = row_dict["transcriptions"]
        label = row_dict["analysis_label"]
        scores = row_dict["analysis_scores"]
        consistency = row_dict["consistency"]
        aggregated_score = row_dict["aggregated_score"]

        for t in transcriptions:
            response["segments"].append({
                "end": t["end"],
                "text": t["text"],
                "start": t["start"],
                "metrics": {
                    "label": label,
                    "score": scores,
                    "consistency": consistency,
                    "aggregated_score": aggregated_score
                }
            })

    return response

@app.get("/get_files")
async def get_files(user: str = Depends(authenticate)):
    try:
        cur, conn = connect_to_db()
        cur.execute("SELECT DISTINCT(file_name) FROM audio_data")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return JSONResponse({"error": "No files found"}, status_code=404)

        # Extract file names and filter out None
        file_names = [row[0] for row in rows if row[0] is not None]

        return {"files": file_names}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/")
async def health_check():
    """
    Simple health check route to verify API is running.
    """
    return {"status": "ok", "message": "API is deployed and working"}



# async def get_results(file_name: str = Query(..., description="File name to fetch results for")):
#     cur, conn = connect_to_db()
#     cur.execute("SELECT * FROM audio_data WHERE file_name = %s", (file_name,))
#     rows = cur.fetchall()
#     cur.close()
#     conn.close()
#     if not rows:
#         return JSONResponse({"error": "No records found"}, status_code=404)

#     response = {"file_name": file_name, "segments": []}

#     for row in rows:
#         # Adapt to your table order: (id, speaker, url, uuid, transcriptions, ..., label, scores, consistency, aggregated_score, file_name, file_id, file_url)
#         transcriptions = row[4]
#         label = row[7]
#         scores = row[8]
#         consistency = row[9]
#         aggregated_score = row[10]

#         for t in transcriptions:
#             response["segments"].append({
#                 "end": t["end"],
#                 "text": t["text"],
#                 "start": t["start"],
#                 "metrics": {
#                     "label": label,
#                     "score": scores,
#                     "consistency": consistency,
#                     "aggregated_score": aggregated_score
#                 }
#             })

#     return response
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
#     safe_filename = file.filename.replace(" ", "_")   # replace spaces
#     temp_path = os.path.join(tempfile.gettempdir(), safe_filename)
#     with open(temp_path, "wb") as temp_file:
#         shutil.copyfileobj(file.file, temp_file)

#     # try:
#     #     # Call your function
#     #     results = process_audio(temp_path)
#     #     return results
#     # finally:
#     #     # Cleanup temp file
#     #     if os.path.exists(temp_path):
#     #         os.remove(temp_path)
#     try:
#         # Call your function
#         results = process_audio(temp_path)
#         return results
#     except Exception as e:
#         import traceback
#         error_message = str(e)
#         error_trace = traceback.format_exc()

#         # Print to logs (so you can see in console/Azure logs)
#         print("Error occurred while processing audio:")
#         print(error_trace)

#         # Return structured error response
#         return {
#             "status": "error",
#             "message": error_message,
#             "trace": error_trace
#         }
#     finally:
#         # Cleanup temp file
#         if os.path.exists(temp_path):
#             os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)