import json
import smtplib

from datetime import datetime, timezone
from email.message import EmailMessage

from app.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    SENT_EMAIL_LOG,
)

from app.services.pdf_report_service import (
    generate_warning_pdf,
)

from app.services.warning_service import (
    get_warning_summary,
)


def load_sent_log():
    if not SENT_EMAIL_LOG.exists():
        SENT_EMAIL_LOG.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            SENT_EMAIL_LOG,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump([], file)

    with open(
        SENT_EMAIL_LOG,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_sent_log(log):
    with open(
        SENT_EMAIL_LOG,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            log,
            file,
            indent=2,
        )


def already_sent(
    user_id: str,
    forecast_origin: str,
):
    log = load_sent_log()

    return any(
        item.get("user_id") == user_id
        and item.get("forecast_origin") == forecast_origin
        for item in log
    )


def mark_as_sent(
    user_id: str,
    email: str,
    forecast_origin: str,
):
    log = load_sent_log()

    log.append(
        {
            "user_id": user_id,
            "email": email,
            "forecast_origin": forecast_origin,
            "sent_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
    )

    save_sent_log(log)


def send_warning_report(
    user_id: str,
    recipient_email: str,
):
    summary = get_warning_summary()

    forecast_origin = summary[
        "forecast_origin"
    ]

    if already_sent(
        user_id=user_id,
        forecast_origin=forecast_origin,
    ):
        return {
            "status": "already_sent",
            "message": (
                "Warning report was already sent "
                "for this forecast cycle."
            ),
            "forecast_origin": forecast_origin,
        }

    if not SMTP_HOST:
        raise ValueError(
            "SMTP_HOST is missing."
        )

    if not SMTP_USER:
        raise ValueError(
            "SMTP_USER is missing."
        )

    if not SMTP_PASSWORD:
        raise ValueError(
            "SMTP_PASSWORD is missing."
        )

    if not SMTP_FROM_EMAIL:
        raise ValueError(
            "SMTP_FROM_EMAIL is missing."
        )

    pdf_path = generate_warning_pdf()

    warning_count = summary.get(
        "warning_count",
        0,
    )

    critical_count = summary.get(
        "critical_count",
        0,
    )

    high_count = summary.get(
        "high_count",
        0,
    )

    message = EmailMessage()

    message["Subject"] = (
        "Childhood Malnutrition Early Warning Report "
        f"- {forecast_origin[:7]}"
    )

    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient_email

    body = f"""
Dear User,

The latest district-level childhood malnutrition early warning report is attached.

Forecast Origin: {forecast_origin}

Active Warning Districts: {warning_count}
Critical Districts: {critical_count}
High Districts: {high_count}

The attached PDF contains district-wise H1, H3 and H6 warning details,
predicted malnutrition burden, Triposha planning demand,
uncertainty and confidence information, and recommended planning actions.

Please use the forecasting dashboard for full explainability,
district trends and GIS-based planning information.

Regards,
Malnutrition Forecasting Decision Support System
""".strip()

    message.set_content(body)

    with open(
        pdf_path,
        "rb",
    ) as file:
        pdf_data = file.read()

    message.add_attachment(
        pdf_data,
        maintype="application",
        subtype="pdf",
        filename=pdf_path.name,
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=30,
    ) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        smtp.login(
            SMTP_USER,
            SMTP_PASSWORD,
        )

        smtp.send_message(
            message
        )

    mark_as_sent(
        user_id=user_id,
        email=recipient_email,
        forecast_origin=forecast_origin,
    )

    return {
        "status": "sent",
        "recipient": recipient_email,
        "forecast_origin": forecast_origin,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "high_count": high_count,
        "pdf_file": pdf_path.name,
    }