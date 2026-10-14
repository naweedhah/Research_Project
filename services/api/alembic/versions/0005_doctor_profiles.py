"""Add clinician profile fields and replace demonstration doctor accounts."""

import bcrypt
from alembic import op
import sqlalchemy as sa

revision = "0006_doctor_profiles"
down_revision = "0005_dataset_research_fields"
branch_labels = None
depends_on = None

PASSWORD = "doctor123"

DOCTORS = {
    "doctor@demo.local": {
        "full_name": "Prof. Pujitha Wickramasinghe",
        "qualifications": "MBBS(Col), DCH(Col), MD(Paed), PhD(Col)",
        "experience": (
            "Senior Professor in Paediatrics, University of Colombo, and Honorary Consultant "
            "Paediatrician at Lady Ridgeway Hospital for Children. Trained in paediatric "
            "gastroenterology and clinical nutrition at the Royal Children's Hospital and "
            "Children's Nutrition Research Centre, Brisbane."
        ),
    },
    "doctor@gmail.com": {
        "full_name": "Prof. Shamya de Silva",
        "qualifications": "MBBS(Col), MD(Paed), DCH(Col), FSLCP, FCCP, FSLCE",
        "experience": (
            "Professor in Paediatrics, University of Colombo, and Honorary Consultant "
            "Paediatrician at the University Unit, Lady Ridgeway Hospital since 1991. "
            "Established the first Endocrine Clinic at Lady Ridgeway Hospital in 2001 and "
            "the Obesity and Diabetes Clinic in 2004."
        ),
    },
    "doctor.kandy@demo.local": {
        "full_name": "Prof. A.H.H.M. Jayaweera",
        "qualifications": "MBBS(SL), MD(Col), DCH(Col), FRCPCH(UK)",
        "experience": (
            "Professor in Paediatrics, University of Peradeniya, and Consultant Paediatrician "
            "at the Teaching Hospital, Peradeniya. Board certified in 2011, with a special "
            "interest in growth, nutrition, gastroenterology, and renal disorders."
        ),
    },
}


def upgrade() -> None:
    op.add_column("users", sa.Column("qualifications", sa.String(length=300), nullable=True))
    op.add_column("users", sa.Column("experience", sa.String(length=800), nullable=True))
    password_hash = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    for email, profile in DOCTORS.items():
        op.execute(
            sa.text(
                """
                UPDATE users
                SET full_name = :full_name,
                    qualifications = :qualifications,
                    experience = :experience,
                    password_hash = :password_hash,
                    failed_login_count = 0,
                    locked_until = NULL,
                    status = 'active'
                WHERE email = :email
                """
            ).bindparams(
                email=email,
                password_hash=password_hash,
                **profile,
            )
        )


def downgrade() -> None:
    op.drop_column("users", "experience")
    op.drop_column("users", "qualifications")
