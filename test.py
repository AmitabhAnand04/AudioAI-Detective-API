# from service.speech_service import recognize_from_file


# try:
#     transcriptions, files = recognize_from_file(file_path="C:/Users/AmitabhAnand/Downloads/Human_to_AI_Call_8.mp3")
    
#     print("\nFinal Transcriptions with Files:")
#     print(transcriptions)
#     print(files)

# except Exception as err:
#     print("Error:", err)

# from utils.predict import analyze_audio


# if __name__ == "__main__":
#     while True:
#         user_input_file = input("Enter the path of the file to analyze (or type 'end' to quit): ")
        
#         if user_input_file.lower() == "end":
#             print("Exiting program...")
#             break
        
#         try:
#             result = analyze_audio(user_input_file)
#             print("Result:", result)
#         except Exception as e:
#             print(f"Error analyzing {user_input_file}: {e}")

# import traceback

# from service.ml_detection_service import analyze_audio
# from service.speech_service import recognize_from_file

# def process_audio(file_path: str):
#     """
#     Process audio file:
#     - Recognize speakers + transcriptions
#     - Analyze audio authenticity (per speaker file)
#     - Attach analysis result to each utterance
#     """

#     try:
#         # Step 1: Get transcriptions + saved audio files per speaker
#         transcriptions, saved_files = recognize_from_file(file_path)

#         # Step 2: Run analysis ONCE per speaker file
#         analysis_results = {}
#         for speaker, file in saved_files.items():
#             if speaker != "Unknown":
#                 try:
#                     analysis_results[speaker] = analyze_audio(file)
#                 except Exception as e:
#                     analysis_results[speaker] = f"Error analyzing audio: {str(e)}"
#             else:
#                 analysis_results[speaker] = "Not applicable"

#         # Step 3: Build response JSON
#         response = {
#             "utterances": [
#                 {
#                     "speaker": speaker,
#                     "text": text,
#                     "start": start,
#                     "end": end,
#                     "analysis": analysis_results.get(speaker, "Unknown")
#                 }
#                 for speaker, text, start, end in transcriptions
#             ]
#         }

#         return response

#     except Exception as e:
#         return {
#             "error": str(e),
#             "traceback": traceback.format_exc()
#         }
# # Example usage
# if __name__ == "__main__":
#     file_path = "C:/Projects/Speech Analysis/Integration/voice_samples/Human to AI Call 8.mp3"
#     result = process_audio(file_path)
#     print(result)

from service.process_audio_resemble import process_audio


if __name__ == "__main__":
    file_path = "C:/Users/AmitabhAnand/Downloads/Human_to_AI_Call_8.mp3"
    results = process_audio(file_path)
    print("Stored Results:", results)