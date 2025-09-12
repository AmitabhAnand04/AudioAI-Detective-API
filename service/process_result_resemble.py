import json
from psycopg2 import sql

from service.db_service import connect_to_db

def update_audio_data(file_uuid: str, metrics: dict):
    """
    Update the audio_data table with analysis results.

    Args:
        file_uuid (str): UUID of the audio file
        metrics (dict): metrics dict from callback
    """
    # Extract values from metrics
    analysis_label = metrics.get("label")
    analysis_scores = metrics.get("score", [])
    consistency = metrics.get("consistency")
    aggregated_score = metrics.get("aggregated_score")

    # Convert scores list to JSON string for JSONB column
    analysis_scores_json = json.dumps(analysis_scores)

    # Get DB connection and cursor
    cur, conn = connect_to_db()  # your existing function

    try:
        update_query = """
            UPDATE audio_data
            SET
                analysis_label = %s,
                analysis_scores = %s,
                consistency = %s,
                aggregated_score = %s
            WHERE file_uuid = %s;
        """

        cur.execute(
            update_query,
            (analysis_label, analysis_scores_json, consistency, aggregated_score, file_uuid)
        )
        conn.commit()
        print(f"✅ Updated audio_data for UUID: {file_uuid}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to update audio_data for UUID {file_uuid}: {e}")
    finally:
        cur.close()
        conn.close()
