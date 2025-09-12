import traceback

from service.ml_detection_service import analyze_audio
from service.speech_service import recognize_from_file

def process_audio(file_path: str):
    """
    Process audio file:
    - Recognize speakers + transcriptions
    - Analyze audio authenticity (per speaker file)
    - Attach analysis result to each utterance
    """

    try:
        # Step 1: Get transcriptions + saved audio files per speaker
        transcriptions, saved_files = recognize_from_file(file_path)

        # Step 2: Run analysis ONCE per speaker file
        analysis_results = {}
        for speaker, file in saved_files.items():
            if speaker != "Unknown":
                try:
                    analysis_results[speaker] = analyze_audio(file)
                except Exception as e:
                    analysis_results[speaker] = f"Error analyzing audio: {str(e)}"
            else:
                analysis_results[speaker] = "Not applicable"

        # Step 3: Build response JSON
        response = {
            "utterances": [
                {
                    "speaker": speaker,
                    "text": text,
                    "start": start,
                    "end": end,
                    "analysis": analysis_results.get(speaker, "Unknown")
                }
                for speaker, text, start, end in transcriptions
            ]
        }

        return response

    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }