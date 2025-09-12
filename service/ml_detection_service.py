import os
import joblib
import librosa
import numpy as np

def extract_mfcc_features(audio_path, n_mfcc=13, n_fft=2048, hop_length=512):
    try:
        audio_data, sr = librosa.load(audio_path, sr=None)
    except Exception as e:
        print(f"Error loading audio file {audio_path}: {e}")
        return None

    mfccs = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop_length)
    return np.mean(mfccs.T, axis=0)
def analyze_audio(input_audio_path):
    model_filename = "model/magic_model.pkl"
    scaler_filename = "model/magic_scaler.pkl"
    svm_classifier = joblib.load(model_filename)
    scaler = joblib.load(scaler_filename)

    if not os.path.exists(input_audio_path):
        print("Error: The specified file does not exist.")
    # elif not input_audio_path.lower().endswith(".wav"):
    #     print("Error: The specified file is not a .wav file.")

    mfcc_features = extract_mfcc_features(input_audio_path)

    if mfcc_features is not None:
        mfcc_features_scaled = scaler.transform(mfcc_features.reshape(1, -1))
        prediction = svm_classifier.predict(mfcc_features_scaled)
        os.remove(input_audio_path)
        if prediction[0] == 0:
            return "real"
        else:
            return "fake"
    else:
        return "Error: Unable to process the input audio."