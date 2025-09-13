import os
import uuid
from dotenv import load_dotenv, find_dotenv
import psycopg2
import json

from service.db_service import connect_to_db
from service.resemble_detection_service import analyze_audio, analyze_result
from service.speech_service import recognize_from_file
import traceback
import logging
import sys

from opencensus.ext.azure.log_exporter import AzureLogHandler
load_dotenv(find_dotenv())

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Always log to console (local + Azure Log Stream)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console_handler)

# Add Azure Application Insights handler only if connection string is present
app_insights_conn = os.getenv("APP_INSIGHTS_CONNECTION_STRING")
if app_insights_conn:
    azure_handler = AzureLogHandler(connection_string=app_insights_conn)
    azure_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(azure_handler)

# def process_audio(file_path):
#     file_name = os.path.basename(file_path)   # original filename
#     file_id = str(uuid.uuid4())
#     # Step 1: Get transcriptions and uploaded files
#     transcriptions, uploaded_files, original_file = recognize_from_file(file_path)

#     results = []

#     # Step 2: Process each speaker
#     for speaker, url in uploaded_files.items():
#         # Call second function to get uuid
#         file_uuid = analyze_audio(url)

#         # Collect all transcription segments for this speaker
#         speaker_transcripts = [
#             {"text": text, "start": start, "end": end}
#             for spk, text, start, end in transcriptions if spk == speaker
#         ]

#         # Step 3: Store in PostgreSQL
#         cur, conn = connect_to_db()
#         # cur = conn.cursor()

#         insert_query = """
#             INSERT INTO audio_data (speaker_name, file_url, file_uuid, transcriptions, file_name, file_id, original_file_url)
#             VALUES (%s, %s, %s, %s, %s, %s, %s)
#             RETURNING id;
#         """
#         cur.execute(insert_query, (
#             speaker,
#             url,
#             file_uuid,
#             json.dumps(speaker_transcripts),
#             file_name,
#             file_id,
#             original_file
#         ))

#         inserted_id = cur.fetchone()[0]
#         conn.commit()
#         cur.close()
#         conn.close()

#         results.append({
#             "id": inserted_id,
#             "speaker": speaker,
#             "url": url,
#             "uuid": file_uuid,
#             "file_name": file_name,
#             "file_id": file_id,
#             "file_url": original_file,
#             "transcriptions": speaker_transcripts
#         })

#     return results

# import os
# import uuid
# import json


def process_audio(file_path):
    results = []
    file_name = os.path.basename(file_path)   # original filename
    file_id = str(uuid.uuid4())

    try:
        # Step 1: Get transcriptions and uploaded files
        transcriptions, uploaded_files, original_file = recognize_from_file(file_path)
        # test_tuple = recognize_from_file(file_path)

        # Step 2: Process each speaker
        for speaker, url in uploaded_files.items():
            try:
                # Call second function to get uuid
                file_uuid = analyze_audio(url)
                result = analyze_result(file_uuid)  
                analysis_label = result.get("analysis_label")
                analysis_scores = result.get("analysis_scores")
                consistency = result.get("consistency")
                aggregated_score = result.get("aggregated_score")
                # Collect all transcription segments for this speaker
                speaker_transcripts = [
                    {"text": text, "start": start, "end": end}
                    for spk, text, start, end in transcriptions if spk == speaker
                ]

                # Step 3: Store in PostgreSQL
                cur, conn = connect_to_db()
                try:
                    insert_query = """
                        INSERT INTO audio_data (
                            speaker_name, file_url, file_uuid,
                            transcriptions, file_name, file_id, original_file_url,
                            analysis_label, analysis_scores, consistency, aggregated_score
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """

                    cur.execute(insert_query, (
                        speaker,
                        url,
                        file_uuid,
                        json.dumps(speaker_transcripts),
                        file_name,
                        file_id,
                        original_file,
                        analysis_label,
                        json.dumps(analysis_scores),
                        consistency,
                        aggregated_score
                    ))


                    inserted_id = cur.fetchone()[0]
                    conn.commit()

                    results.append({
                        "id": inserted_id,
                        "speaker": speaker,
                        "url": url,
                        "uuid": file_uuid,
                        "file_name": file_name,
                        "file_id": file_id,
                        "file_url": original_file,
                        "transcriptions": speaker_transcripts
                    })

                except Exception as db_err:
                    conn.rollback()
                    logger.error("Database error:", db_err)
                    logger.error(traceback.format_exc())
                    raise
                finally:
                    cur.close()
                    conn.close()

            except Exception as speaker_err:
                logger.error(f"Error processing speaker {speaker}: {speaker_err}")
                logger.error(traceback.format_exc())
                continue  # move on to next speaker

    except Exception as main_err:
        logger.error("Fatal error in process_audio:", main_err)
        logger.error(traceback.format_exc())
        raise  # re-raise so caller sees the actual error

    return results
    # return test_tuple
