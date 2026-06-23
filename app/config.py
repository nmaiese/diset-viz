import os

SITE_NAME = "Divario Italia"
SITE_URL = os.getenv("SITE_URL", "https://divarioitalia.it").rstrip("/")

GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")
GOOGLE_TAG_MANAGER_ID = os.getenv("GOOGLE_TAG_MANAGER_ID", "")
ADSENSE_CLIENT = os.getenv("ADSENSE_CLIENT", "")
ADSENSE_SLOT_BANNER = os.getenv("ADSENSE_SLOT_BANNER", "")
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "")
BING_SITE_VERIFICATION = os.getenv("BING_SITE_VERIFICATION", "")

# Deprecated: consent is managed by the CMP loaded in Google Tag Manager.
FORCE_FUNDING_CHOICES_CMP = False
ENABLE_CONSENT_BANNER = False
