import os

SITE_NAME = "Divario Italia"
SITE_URL = os.getenv("SITE_URL", "https://divarioitalia.it").rstrip("/")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.getenv("SECRET_KEY", "")
# In produzione punta al filesystem locale del container (vedi Dockerfile):
# Litestream lo ripristina da GCS all'avvio e lo replica in continuo, così il
# file resta locale (WAL pieno supportato) senza bisogno di un volume condiviso.
LEADERBOARD_DB = os.getenv("LEADERBOARD_DB", os.path.join(_REPO_ROOT, "data", "leaderboard.sqlite3"))

GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")
GOOGLE_TAG_MANAGER_ID = os.getenv("GOOGLE_TAG_MANAGER_ID", "")
ADSENSE_CLIENT = os.getenv("ADSENSE_CLIENT", "")
ADSENSE_SLOT_BANNER = os.getenv("ADSENSE_SLOT_BANNER", "")
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "")
BING_SITE_VERIFICATION = os.getenv("BING_SITE_VERIFICATION", "")

# Deprecated: consent is managed by the CMP loaded in Google Tag Manager.
FORCE_FUNDING_CHOICES_CMP = False
ENABLE_CONSENT_BANNER = False
