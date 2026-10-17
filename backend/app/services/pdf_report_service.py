import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.config import (
    WARNINGS_FILE,
    WARNING_SUMMARY_FILE,
    WARNING_PDF_DIR,
)


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def generate_warning_pdf():
    warnings = load_json(WARNINGS_FILE)
    summary = load_json(WARNING_SUMMARY_FILE)

    WARNING_PDF_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    forecast_origin = summary["forecast_origin"]
    origin_label = forecast_origin[:7]

    output_file = (
        WARNING_PDF_DIR
        / f"malnutrition_warning_report_{origin_label}.pdf"
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=8,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
    )

    document = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Childhood Malnutrition Early Warning Report",
        author="Malnutrition Forecasting Decision Support System",
    )

    story = []

    # ---------------------------------------------------------
    # REPORT TITLE
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "Childhood Malnutrition Early Warning Report",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"Forecast Origin: {forecast_origin}",
            body_style,
        )
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    # ---------------------------------------------------------
    # OVERALL WARNING SUMMARY
    # ---------------------------------------------------------

    summary_data = [
        [
            "Indicator",
            "Value",
        ],
        [
            "Active Warning Districts",
            str(
                summary.get(
                    "warning_count",
                    0,
                )
            ),
        ],
        [
            "Critical Districts",
            str(
                summary.get(
                    "critical_count",
                    0,
                )
            ),
        ],
        [
            "High Districts",
            str(
                summary.get(
                    "high_count",
                    0,
                )
            ),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            80 * mm,
            70 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(
        summary_table
    )

    story.append(
        Spacer(
            1,
            12,
        )
    )

    story.append(
        Paragraph(
            (
                "This report summarizes district-level HIGH and "
                "CRITICAL future malnutrition planning warnings. "
                "H1, H3 and H6 forecasts are precomputed model "
                "outputs and are not recalculated during report generation."
            ),
            small_style,
        )
    )

    story.append(
        Spacer(
            1,
            10,
        )
    )

    # ---------------------------------------------------------
    # DISTRICT WARNING SECTIONS
    # ---------------------------------------------------------

    for index, warning in enumerate(
        warnings,
        start=1,
    ):
        district = warning["district"]

        story.append(
            Paragraph(
                f"{index}. {district}",
                heading_style,
            )
        )

        overview = [
            [
                "Overall Severity",
                warning["overall_severity"],
            ],
            [
                "Nearest Warning",
                (
                    f'H{warning["nearest_warning_horizon"]} - '
                    f'{warning["nearest_warning_month_display"]}'
                ),
            ],
            [
                "Message",
                warning["message"],
            ],
            [
                "Recommended Action",
                warning["action"],
            ],
        ]

        overview_table = Table(
            overview,
            colWidths=[
                42 * mm,
                108 * mm,
            ],
        )

        overview_table.setStyle(
            TableStyle(
                [
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.grey,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (0, -1),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(
            overview_table
        )

        story.append(
            Spacer(
                1,
                6,
            )
        )

        # -----------------------------------------------------
        # H1 / H3 / H6 TABLE
        # -----------------------------------------------------

        horizon_rows = [
            [
                "Horizon",
                "Target Month",
                "Priority",
                "Cases",
                "Triposha",
                "Confidence",
            ]
        ]

        for key in [
            "h1",
            "h3",
            "h6",
        ]:
            h = warning["horizons"].get(
                key
            )

            if not h:
                continue

            horizon_rows.append(
                [
                    f'H{h["horizon"]}',
                    h["target_month_display"],
                    h["priority"],
                    str(
                        h["predicted_cases"]
                    ),
                    str(
                        h["triposha_packets"]
                    ),
                    h["confidence_label"],
                ]
            )

        horizon_table = Table(
            horizon_rows,
            colWidths=[
                16 * mm,
                30 * mm,
                24 * mm,
                18 * mm,
                22 * mm,
                40 * mm,
            ],
            repeatRows=1,
        )

        horizon_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.grey,
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        7.5,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                ]
            )
        )

        story.append(
            horizon_table
        )

        story.append(
            Spacer(
                1,
                10,
            )
        )

    # ---------------------------------------------------------
    # FINAL INTERPRETATION NOTE
    # ---------------------------------------------------------

    story.append(
        Spacer(
            1,
            6,
        )
    )

    story.append(
        Paragraph(
            (
                "Interpretation note: Priority levels represent relative "
                "forecast-based district planning priority and should not "
                "be interpreted as clinical emergency classifications. "
                "Prediction intervals are produced by the NGBoost "
                "uncertainty layer."
            ),
            small_style,
        )
    )

    document.build(
        story
    )

    return output_file