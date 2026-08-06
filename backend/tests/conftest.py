import os

# Settings() requires these to be set; provide harmless test values before
# any app module is imported so get_settings() doesn't blow up.
os.environ.setdefault("APP_ENCRYPTION_KEY", "zQ8vN2k9K0e3m1B7p6R4s5T8u9V0w1X2y3Z4a5B6c7D=")
os.environ.setdefault("SETUP_TOKEN", "test-setup-token")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://leads:leads@localhost:5432/leads_test"
)
