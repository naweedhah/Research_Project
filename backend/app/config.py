from pathlib import Path
import os

from dotenv import load_dotenv


# ======================================================================================
# PATH CONFIGURATION
# ======================================================================================

# Current file:
# research git version/backend/app/config.py

# backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# research git version/
PROJECT_ROOT = BACKEND_ROOT.parent

# Load environment variables from backend/.env
ENV_FILE = BACKEND_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE)


# ======================================================================================
# RESEARCH COMPONENT PATH
# ======================================================================================

FORECASTING_ROOT = (
    PROJECT_ROOT
    / "components"
    / "c4_spatiotemporal_forecasting"
    / "Forecasting_Research"
)

DASHBOARD_DIR = FORECASTING_ROOT / "outputs" / "dashboard"
REPORT_DIR = FORECASTING_ROOT / "outputs" / "reports"


# ======================================================================================
# DASHBOARD / RESEARCH OUTPUT FILES
# ======================================================================================

METADATA_FILE = DASHBOARD_DIR / "metadata.json"

FORECAST_LOOKUP_FILE = DASHBOARD_DIR / "forecast_lookup.json"
FORECAST_RECORDS_FILE = DASHBOARD_DIR / "forecast_records.csv"

WARNINGS_FILE = DASHBOARD_DIR / "warnings.json"
WARNING_SUMMARY_FILE = DASHBOARD_DIR / "warning_summary.json"

SHAP_FILE = DASHBOARD_DIR / "shap_explanations.json"
RESOURCE_FILE = DASHBOARD_DIR / "resource_planning.csv"

GIS_PRIORITY_FILE = DASHBOARD_DIR / "gis_priority.csv"
DISTRICT_BOUNDARIES_FILE = DASHBOARD_DIR / "district_boundaries.geojson"

ANNUAL_TRENDS_FILE = DASHBOARD_DIR / "annual_trends.json"
DATASET_FILE = DASHBOARD_DIR / "dataset_dashboard.csv"

MANIFEST_FILE = DASHBOARD_DIR / "dashboard_manifest.json"


# ======================================================================================
# AUTHENTICATION DATA
# ======================================================================================

AUTH_DATA_DIR = BACKEND_ROOT / "data"

USERS_FILE = AUTH_DATA_DIR / "users.json"
SENT_EMAIL_LOG = AUTH_DATA_DIR / "sent_warning_emails.json"


# ======================================================================================
# JWT CONFIGURATION
# ======================================================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "development-secret-key-change-me",
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "120",
    )
)


# ======================================================================================
# PDF REPORT CONFIGURATION
# ======================================================================================

WARNING_PDF_DIR = BACKEND_ROOT / "generated_reports"


# ======================================================================================
# EMAIL / SMTP CONFIGURATION
# ======================================================================================

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

SMTP_FROM_EMAIL = os.getenv(
    "SMTP_FROM_EMAIL",
    SMTP_USER,
)

SMTP_FROM_NAME = os.getenv(
    "SMTP_FROM_NAME",
    "Malnutrition Early Warning System",
)