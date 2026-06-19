import os

SITE_NAME = "Divario Italia"
SITE_URL = os.getenv("SITE_URL", "https://divarioitalia.it").rstrip("/")

GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")
ADSENSE_CLIENT = os.getenv("ADSENSE_CLIENT", "")
ADSENSE_SLOT_BANNER = os.getenv("ADSENSE_SLOT_BANNER", "")
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "")
BING_SITE_VERIFICATION = os.getenv("BING_SITE_VERIFICATION", "")

# Attivo solo se ci sono servizi terzi configurati, quindi in locale resta invisibile.
ENABLE_CONSENT_BANNER = os.getenv("ENABLE_CONSENT_BANNER", "true").lower() == "true"
