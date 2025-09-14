import os
import tempfile
import time
from collections import defaultdict
import uuid

import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment

import io
from azure.storage.blob import BlobServiceClient, ContentSettings
import mimetypes
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import logging
import sys

from opencensus.ext.azure.log_exporter import AzureLogHandler

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

# def convert_mp3_to_pcm_tempfile(mp3_path):
#     if not os.path.exists(mp3_path):
#         raise FileNotFoundError(f"File not found: {mp3_path}")
    
#     logger.info("Conversion Process Started!!")
    
#     audio = AudioSegment.from_mp3(mp3_path)
#     audio = audio.set_channels(1)
#     audio = audio.set_frame_rate(16000)
    
#     temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
#     temp_wav_path = temp_wav_file.name
#     temp_wav_file.close()
    
#     audio.export(temp_wav_path, format="wav")
#     return temp_wav_path

def convert_audio_to_pcm_tempfile(input_path):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    
    logger.info("Conversion Process Started!! for file: " + input_path)

    # Detect extension and load accordingly
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".mp3":
        audio = AudioSegment.from_mp3(input_path)
    elif ext == ".m4a":
        audio = AudioSegment.from_file(input_path, format="m4a")
    else:
        raise ValueError("Unsupported file format. Only MP3, M4A, and WAV are supported.")

    # Convert to mono, 16kHz PCM WAV
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(16000)

    temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav_path = temp_wav_file.name
    temp_wav_file.close()

    audio.export(temp_wav_path, format="wav")
    logger.info(f"Conversion completed. Temporary WAV file created at: {temp_wav_path}")
    return temp_wav_path

# def recognize_from_file(file_path, output_dir="clips"):
#     try:
#         # Create output folder if not exists
#         os.makedirs(output_dir, exist_ok=True)

#         # Configure speech service for English only
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv("SPEECH_KEY"),
#             region=os.getenv("SPEECH_REGION")
#         )
#         speech_config.speech_recognition_language = "en-US"
#         speech_config.set_property(
#             property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults,
#             value='true'
#         )

#         # Handle file extension
#         ext = file_path.lower().split(".")[-1]
#         if ext in ["mp3", "m4a"]:
#             wav_path = convert_audio_to_pcm_tempfile(file_path)
#         elif ext == "wav":
#             wav_path = file_path
#         else:
#             raise ValueError("Unsupported file format. Only MP3, M4A, and WAV are supported.")

#         audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
#         conversation_transcriber = speechsdk.transcription.ConversationTranscriber(
#             speech_config=speech_config,
#             audio_config=audio_config
#         )

#         # Load original audio for slicing
#         try:
#             original_audio = AudioSegment.from_file(file_path)
#         except Exception as e:
#             raise RuntimeError(f"Failed to load audio file: {file_path}, error: {e}")

#         speaker_clips = defaultdict(list)  # store list of clips per speaker
#         transcriptions = []               # (speaker, text, start, end)
#         saved_files = {}                  # speaker -> file path
#         transcribing_stop = False

#         def conversation_transcriber_transcribed_cb(evt):
#             try:
#                 if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
#                     speaker = evt.result.speaker_id or "Unknown"
#                     text = evt.result.text.strip()

#                     # Get utterance start/end times
#                     start_time = evt.result.offset / 10_000_000   # seconds
#                     end_time = (evt.result.offset + evt.result.duration) / 10_000_000

#                     # Slice the utterance from original audio
#                     clip = original_audio[start_time*1000:end_time*1000]

#                     # Buffer clips per speaker
#                     speaker_clips[speaker].append(clip)

#                     # Append transcription with timestamps
#                     transcriptions.append((speaker, text, start_time, end_time))
#                     logger.info(f"Buffered clip for {speaker}: '{text}' ({start_time}-{end_time})")
#             except Exception as e:
#                 logger.info(f"Error in transcription callback: {e}")

#         def stop_cb(evt):
#             nonlocal transcribing_stop
#             transcribing_stop = True

#         # Hook up events
#         conversation_transcriber.transcribed.connect(conversation_transcriber_transcribed_cb)
#         conversation_transcriber.session_stopped.connect(stop_cb)
#         conversation_transcriber.canceled.connect(stop_cb)

#         # Start transcription
#         try:
#             conversation_transcriber.start_transcribing_async()
#             while not transcribing_stop:
#                 time.sleep(0.5)
#             conversation_transcriber.stop_transcribing_async()
#         except Exception as e:
#             raise RuntimeError(f"Error during transcription: {e}")

#         for speaker, clips in speaker_clips.items():
#             try:
#                 if speaker == "Unknown":
#                     logger.info(f"Skipping export for speaker: {speaker}")
#                     continue

#                 if clips:
#                     combined = sum(clips)  # concatenate all clips
#                     filename = os.path.join(output_dir, f"{speaker}.mp3")
#                     combined.export(filename, format="mp3")
#                     saved_files[speaker] = filename
#                     logger.info(f"Saved full clip for {speaker}: {filename}")
#             except Exception as e:
#                 logger.info(f"Error exporting clips for {speaker}: {e}")

#         # Cleanup
#         audio_config = None
#         conversation_transcriber = None

#         if file_path.lower().endswith(".mp3") and os.path.exists(wav_path):
#             try:
#                 os.remove(wav_path)
#                 logger.info(f"Temporary file {wav_path} deleted.")
#             except PermissionError:
#                 logger.info(f"Warning: Could not delete {wav_path}, file still in use.")
#             except Exception as e:
#                 logger.info(f"Error deleting temporary file {wav_path}: {e}")

#         return transcriptions, saved_files
#         # return {
#         #     "utterances": [
#         #         {"speaker": s, "text": t, "start": st, "end": et}
#         #         for (s, t, st, et) in transcriptions
#         #     ],
#         #     "saved_files": saved_files
#         # }

#     except Exception as e:
#         logger.info(f"Fatal error in recognize_from_file: {e}")
#         return [], {}


# def recognize_from_file(file_path, container_name="bc-test-samples-segregated", folder_name="savedbycode"):
#     try:
#         # Initialize Blob Service Client
#         blob_service_client = BlobServiceClient.from_connection_string(
#             os.getenv("AZURE_STORAGE_CONNECTION_STRING")
#         )
#         container_client = blob_service_client.get_container_client(container_name)
#         # container_client.create_container()

#         # Upload original file
#         with open(file_path, "rb") as data:
#             original_blob_name = f"{folder_name}/{os.path.basename(file_path)}"
#             blob_client = container_client.get_blob_client(original_blob_name)
#             blob_client.upload_blob(data, overwrite=True)
#             original_file = blob_client.url
#             logger.info(f"Uploaded original file: {original_file}")

#         # Configure Azure Speech
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv("SPEECH_KEY"),
#             region=os.getenv("SPEECH_REGION")
#         )
#         speech_config.speech_recognition_language = "en-US"
#         speech_config.set_property(
#             property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults,
#             value="true"
#         )

#         # Handle file extension
#         ext = file_path.lower().split(".")[-1]
#         if ext in ["mp3", "m4a"]:
#             wav_path = convert_audio_to_pcm_tempfile(file_path)
#         elif ext == "wav":
#             wav_path = file_path
#         else:
#             raise ValueError("Unsupported file format. Only MP3, M4A, and WAV are supported.")

#         audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
#         conversation_transcriber = speechsdk.transcription.ConversationTranscriber(
#             speech_config=speech_config,
#             audio_config=audio_config
#         )

#         # Load original audio
#         try:
#             original_audio = AudioSegment.from_file(file_path)
#         except Exception as e:
#             raise RuntimeError(f"Failed to load audio file: {file_path}, error: {e}")


#         speaker_clips = defaultdict(list)
#         transcriptions = []
#         uploaded_files = {}
#         transcribing_stop = False

#         def conversation_transcriber_transcribed_cb(evt):
#             nonlocal speaker_clips, transcriptions
#             try:
#                 if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
#                     speaker = evt.result.speaker_id or "Unknown"
#                     text = evt.result.text.strip()
#                     start_time = evt.result.offset / 10_000_000
#                     end_time = (evt.result.offset + evt.result.duration) / 10_000_000

#                     clip = original_audio[start_time * 1000:end_time * 1000]
#                     speaker_clips[speaker].append(clip)
#                     transcriptions.append((speaker, text, start_time, end_time))
#                     logger.info(f"Buffered clip for {speaker}: '{text}' ({start_time}-{end_time})")
#             except Exception as e:
#                 logger.info(f"Error in transcription callback: {e}")

#         def stop_cb(evt):
#             nonlocal transcribing_stop
#             transcribing_stop = True

#         conversation_transcriber.transcribed.connect(conversation_transcriber_transcribed_cb)
#         conversation_transcriber.session_stopped.connect(stop_cb)
#         conversation_transcriber.canceled.connect(stop_cb)

#         # Start transcription
#         conversation_transcriber.start_transcribing_async()
#         while not transcribing_stop:
#             time.sleep(0.5)
#         conversation_transcriber.stop_transcribing_async()

#         # Upload to blob storage
#         for speaker, clips in speaker_clips.items():
#             if speaker == "Unknown":
#                 logger.info("Skipping export for speaker: Unknown")
#                 continue
#             if clips:
#                 combined = sum(clips)
#                 buffer = io.BytesIO()
#                 combined.export(buffer, format="mp3")
#                 buffer.seek(0)
                
#                 blob_name = f"{folder_name}/{str(uuid.uuid4())}{speaker}.mp3"
#                 blob_client = container_client.get_blob_client(blob_name)
#                 blob_client.upload_blob(buffer, overwrite=True)

#                 blob_url = blob_client.url
#                 uploaded_files[speaker] = blob_url
#                 logger.info(f"Uploaded clip for {speaker}: {blob_url}")

#         # Cleanup
#         audio_config = None
#         conversation_transcriber = None
#         if file_path.lower().endswith(".mp3") and os.path.exists(wav_path):
#             try:
#                 os.remove(wav_path)
#             except Exception as e:
#                 logger.info(f"Error deleting temp file {wav_path}: {e}")

#         return transcriptions, uploaded_files, original_file

#     except Exception as e:
#         logger.info(f"Fatal error in recognize_from_file: {e}")
#         raise

# 🔹 Retry helper
def retry_operation(func, retries=5, *args, **kwargs):
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"[Retry {attempt}/{retries}] Attempting {func.__name__}...")
            return func(*args, **kwargs)
        except Exception as e:
            logger.info(f"[Retry {attempt}/{retries}] {func.__name__} failed: {e}")
            last_exception = e
    raise last_exception


# # 🔹 File upload wrapped for retry
# def upload_blob_with_retry(container_client, blob_name, data, overwrite=True):
#     def _upload():
#         blob_client = container_client.get_blob_client(blob_name)
#         blob_client.upload_blob(data, overwrite=overwrite)
#         return blob_client.url
#     return retry_operation(_upload, retries=5)


# 🔹 File upload wrapped for retry
def upload_blob_with_retry(container_client, blob_name, data, overwrite=True):
    def _upload():
        blob_client = container_client.get_blob_client(blob_name)
        logger.info(f"Uploading blob: {blob_name}")
        # Detect MIME type from filename extension (fallback to audio/mpeg)
        content_type, _ = mimetypes.guess_type(blob_name)
        if not content_type:
            content_type = "audio/mpeg"

        blob_client.upload_blob(
            data,
            overwrite=overwrite,
            content_settings=ContentSettings(
                content_type=content_type,
                cache_control="public, max-age=3600"  # allow browsers/CDNs to cache for 1 hour
            )
        )
        logger.info(f"Upload completed: {blob_name}")
        return blob_client.url

    return retry_operation(_upload, retries=5)

# 🔹 Transcription wrapped for retry
def run_transcription_with_retry(conversation_transcriber, original_audio, speaker_clips, transcriptions):
    transcribing_stop = False

    def conversation_transcriber_transcribed_cb(evt):
        logger.info("Transcription event received.")
        try:
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                speaker = evt.result.speaker_id or "Unknown"
                text = evt.result.text.strip()
                start_time = evt.result.offset / 10_000_000
                end_time = (evt.result.offset + evt.result.duration) / 10_000_000

                clip = original_audio[start_time * 1000:end_time * 1000]
                speaker_clips[speaker].append(clip)
                transcriptions.append((speaker, text, start_time, end_time))
                logger.info(f"Buffered clip for {speaker}: '{text}' ({start_time}-{end_time})")
        except Exception as e:
            logger.info(f"Error in transcription callback: {e}")
            raise

    def stop_cb(evt):
        nonlocal transcribing_stop
        logger.info(f"Transcription session stopped. Reason: {evt}, reason: {evt.reason}, error={evt.error_details}")

        transcribing_stop = True

    def canceled_cb(evt):
        nonlocal transcribing_stop        
        logger.error(f"Transcription canceled: {evt.reason}, error={evt.error_details}")
        transcribing_stop = True

    conversation_transcriber.transcribed.connect(conversation_transcriber_transcribed_cb)
    conversation_transcriber.session_stopped.connect(stop_cb)
    # conversation_transcriber.canceled.connect(stop_cb)
    conversation_transcriber.canceled.connect(canceled_cb)

    def _transcribe():
        nonlocal transcribing_stop
        transcribing_stop = False

        conversation_transcriber.start_transcribing_async()
        while not transcribing_stop:
            time.sleep(0.5)
        conversation_transcriber.stop_transcribing_async()

        if not transcriptions:  # nothing captured
            raise RuntimeError("No transcription results, retrying...")

        return True

    return retry_operation(_transcribe, retries=5)


# 🔹 Main function
def recognize_from_file(file_path, container_name="bc-test-samples-segregated", folder_name="savedbycode"):
    try:
        # Initialize Blob Service Client
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        container_client = blob_service_client.get_container_client(container_name)

        # ✅ Upload original file with retry
        with open(file_path, "rb") as data:
            original_blob_name = f"{folder_name}/{os.path.basename(file_path)}"
            original_file = upload_blob_with_retry(container_client, original_blob_name, data)
            logger.info(f"Uploaded original file: {original_file}")

        # Configure Azure Speech
        speech_config = speechsdk.SpeechConfig(
            subscription=os.getenv("SPEECH_KEY"),
            region=os.getenv("SPEECH_REGION")
        )
        speech_config.speech_recognition_language = "en-US"
        speech_config.set_property(
            property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults,
            value="true"
        )

        # Handle file extension
        ext = file_path.lower().split(".")[-1]
        if ext in ["mp3", "m4a"]:
            wav_path = convert_audio_to_pcm_tempfile(file_path)
        elif ext == "wav":
            wav_path = file_path
        else:
            raise ValueError("Unsupported file format. Only MP3, M4A, and WAV are supported.")

        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        conversation_transcriber = speechsdk.transcription.ConversationTranscriber(
            speech_config=speech_config,
            audio_config=audio_config
        )

        # Load original audio
        try:
            original_audio = AudioSegment.from_file(file_path)
        except Exception as e:
            logger.info(f"Error loading audio file: {e}")
            raise RuntimeError(f"Failed to load audio file: {file_path}, error: {e}")

        speaker_clips = defaultdict(list)
        transcriptions = []
        uploaded_files = {}

        # ✅ Run transcription with retry
        logger.info(f"Starting transcription with retry for file {original_file}...")
        run_transcription_with_retry(conversation_transcriber, original_audio, speaker_clips, transcriptions)
        logger.info(f"Transcription completed for file {original_file}.")

        # ✅ Upload speaker clips with retry
        for speaker, clips in speaker_clips.items():
            if speaker == "Unknown":
                logger.info("Skipping export for speaker: Unknown")
                continue
            if clips:
                logger.info(f"combining {len(clips)} clips for speaker: {speaker} for file {original_file}")
                combined = sum(clips)
                buffer = io.BytesIO()
                combined.export(buffer, format="mp3")
                buffer.seek(0)

                blob_name = f"{folder_name}/{str(uuid.uuid4())}{speaker}.mp3"
                blob_url = upload_blob_with_retry(container_client, blob_name, buffer)
                uploaded_files[speaker] = blob_url
                logger.info(f"Uploaded clip for {original_file}-{speaker}: {blob_url}")

        # Cleanup
        audio_config = None
        conversation_transcriber = None
        if file_path.lower().endswith(".mp3") and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception as e:
                logger.info(f"Error deleting temp file {wav_path}: {e}")

        return transcriptions, uploaded_files, original_file

    except Exception as e:
        logger.info(f"Fatal error in recognize_from_file: {e}")
        raise


# ------------------ Run Example ------------------



# ------------------ Run Mutiple Files Example ------------------

# import os

# # Assuming recognize_from_file is already defined in your code
# # from your_module import recognize_from_file  

# def process_all_files(input_dir, output_dir):
#     # Ensure output base dir exists
#     os.makedirs(output_dir, exist_ok=True)

#     for file_name in os.listdir(input_dir):
#         file_path = os.path.join(input_dir, file_name)

#         # Skip non-audio files
#         if not os.path.isfile(file_path):
#             continue
#         if not file_name.lower().endswith((".wav", ".mp3", ".m4a")):
#             continue

#         # Create output folder based on input file name (without extension)
#         base_name = os.path.splitext(file_name)[0]
#         file_output_dir = os.path.join(output_dir, base_name)
#         os.makedirs(file_output_dir, exist_ok=True)

#         try:
#             transcriptions = recognize_from_file(
#                 file_path=file_path,
#                 output_dir=file_output_dir
#             )

#             logger.info(f"\nFinal Transcriptions for {file_name}:")
#             for speaker, text, filename in transcriptions:
#                 logger.info(f"{speaker}: {text}  -> saved in {filename}")

#         except Exception as err:
#             logger.info(f"Error processing {file_name}: {err}")


# if __name__ == "__main__":
#     input_dir = r"C:/Projects/Speech Analysis/Integration/clips/test_samples_combined"
#     output_dir = r"C:/Projects/Speech Analysis/Integration/clips/test_samples_segregated"

#     process_all_files(input_dir, output_dir)

