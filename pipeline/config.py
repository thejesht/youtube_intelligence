"""Pipeline configuration."""

import os

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Pipeline settings
TRANSCRIPT_DELAY_SECONDS = 2.0  # delay between transcript fetches
MAX_VIDEOS_PER_RUN = 20  # cap per pipeline run
