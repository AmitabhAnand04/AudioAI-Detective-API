import os
import time
import requests
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import logging
import sys

# Configure logging once in your app startup
logging.basicConfig(
    level=logging.INFO,  # you can use DEBUG, WARNING, ERROR too
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # works for local + Azure
    ]
)

logger = logging.getLogger(__name__)

def analyze_audio(file_url: str) -> str:
    """
    Calls the Resemble AI detect API with the given file URL
    and returns the UUID from the response if successful.
    """
    api_url = "https://app.resemble.ai/api/v2/detect"
    token = os.getenv("RESEMBLE_API_TOKEN")  # Get token from env
    
    if not token:
        raise RuntimeError("Missing RESEMBLE_API_TOKEN environment variable.")

    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {"url": file_url}

    callback_url = os.getenv("RESEMBLE_CALLBACK_URL")
    if callback_url:
        params["callback_url"] = callback_url


    try:
        response = requests.post(api_url, headers=headers, params=params, data={})
        response.raise_for_status()
        data = response.json()

        if data.get("success") and "item" in data and "uuid" in data["item"]:
            logger.info("-------------> New UUID from Resemble AI <-----------------"+data["item"]["uuid"])
            return data["item"]["uuid"]
        else:
            raise ValueError(f"API call failed or UUID missing. Response: {data}")

    except Exception as e:
        raise RuntimeError(f"Error analyzing audio: {e}")

def analyze_result(uuid: str) -> dict:
    """
    Polls the Resemble AI detect API with the given UUID until metrics are available.
    Returns analysis_label, analysis_scores, consistency, aggregated_score.
    """
    api_url = f"https://app.resemble.ai/api/v2/detect/{uuid}"
    token = os.getenv("RESEMBLE_API_TOKEN")  # Get token from env
    
    if not token:
        raise RuntimeError("Missing RESEMBLE_API_TOKEN environment variable.")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    while True:
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "item" in data:
                metrics = data["item"].get("metrics", {})

                if metrics:  # ✅ Got metrics, extract and return
                    analysis_label = metrics.get("label")
                    analysis_scores = metrics.get("score", [])
                    consistency = metrics.get("consistency")
                    aggregated_score = metrics.get("aggregated_score")

                    return {
                        "analysis_label": analysis_label,
                        "analysis_scores": analysis_scores,
                        "consistency": consistency,
                        "aggregated_score": aggregated_score
                    }

            # If no metrics yet, wait and retry
            time.sleep(5)

        except Exception as e:
            raise RuntimeError(f"Error analyzing result: {e}")
# def analyze_result(uuid: str) -> dict:
#     """
#     Calls the Resemble AI detect API with the given UUID
#     and returns the 'metrics' field from the response if successful.
#     """
#     api_url = f"https://app.resemble.ai/api/v2/detect/{uuid}"
#     token = os.getenv("RESEMBLE_API_TOKEN")  # Get token from env
    
#     if not token:
#         raise RuntimeError("Missing RESEMBLE_API_TOKEN environment variable.")

#     headers = {
#         "Authorization": f"Bearer {token}"
#     }

#     try:
#         response = requests.get(api_url, headers=headers)
#         response.raise_for_status()
#         data = response.json()

#         if data.get("success") and "item" in data and "metrics" in data["item"]:
#             return data["item"]["metrics"]
#         else:
#             raise ValueError(f"API call failed or metrics missing. Response: {data}")

#     except Exception as e:
#         raise RuntimeError(f"Error analyzing result: {e}")


# if __name__ == "__main__":
# #     # test_url = "https://savoicedetector.blob.core.windows.net/bc-test-samples-segregated/savedbycode/Human_to_AI_Call_8.mp3"
    
# #     # # Step 1: Analyze audio and get UUID
# #     # uuid = analyze_audio(test_url)
# #     # logger.info("Extracted UUID:", uuid)

#     # Step 2: Use UUID to fetch results
#     metrics = analyze_result("bbeed9db3e1b9b82df7fb9ec715c7a15")
#     logger.info("Extracted Metrics:", metrics)
