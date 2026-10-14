from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    FACILITY_ADMIN = "facility_admin"
    DOCTOR = "doctor"
    HEALTH_WORKER = "health_worker"
    NUTRITIONIST = "nutritionist"
    RESEARCHER = "researcher"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"


class OrganizationType(str, enum.Enum):
    GOVERNMENT = "government"
    RESEARCH = "research"
    HOSPITAL = "hospital"
    NGO = "ngo"


class FacilityType(str, enum.Enum):
    CLINIC = "clinic"
    HOSPITAL = "hospital"
    COMMUNITY_UNIT = "community_unit"


class EntityStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Sex(str, enum.Enum):
    FEMALE = "female"
    MALE = "male"
    INTERSEX = "intersex"
    UNKNOWN = "unknown"


class VisitType(str, enum.Enum):
    ROUTINE = "routine"
    FOLLOW_UP = "follow_up"
    REFERRAL = "referral"
    UNSCHEDULED = "unscheduled"


class VisitStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PREDICTED = "predicted"
    CANCELLED = "cancelled"


class ProgressState(str, enum.Enum):
    BASELINE = "baseline"
    IMPROVING = "improving"
    STABLE = "stable"
    STAGNATING = "stagnating"
    DETERIORATING = "deteriorating"
    UNKNOWN = "unknown"
    INCOMPATIBLE_MODEL = "incompatible_model"


class AlertType(str, enum.Enum):
    STAGNATION = "STAGNATION"
    DETERIORATION = "DETERIORATION"
    RELAPSE = "RELAPSE"
    MISSED_FOLLOW_UP = "MISSED_FOLLOW_UP"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED_WITH_REASON = "DISMISSED_WITH_REASON"


class FollowUpStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"


class ClinicianReviewState(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class ClinicianAssessment(str, enum.Enum):
    AGREE = "AGREE"
    DISAGREE = "DISAGREE"
    FURTHER_ASSESSMENT_REQUIRED = "FURTHER_ASSESSMENT_REQUIRED"


class ClinicianWorkflowAction(str, enum.Enum):
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    NUTRITION_REVIEW = "NUTRITION_REVIEW"
    FURTHER_INVESTIGATION = "FURTHER_INVESTIGATION"
    REFER = "REFER"
    REQUEST_INTERVENTION_REASSESSMENT = "REQUEST_INTERVENTION_REASSESSMENT"
    NO_ACTION_RECORDED = "NO_ACTION_RECORDED"


class ModelStatus(str, enum.Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    VALIDATED_RESEARCH = "VALIDATED_RESEARCH"
    STAGING = "STAGING"
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class IntegrationDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"


class C3RequestStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PredictionMode(str, enum.Enum):
    DEMO = "DEMO"
    PYTORCH = "PYTORCH"
    SKLEARN = "SKLEARN"
    ONNX = "ONNX"


class DataQualityFlag(str, enum.Enum):
    MISSING_OPTIONAL_DATA = "MISSING_OPTIONAL_DATA"
    OUTLIER_REVIEW_REQUIRED = "OUTLIER_REVIEW_REQUIRED"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    STALE_SOCIOECONOMIC_PROFILE = "STALE_SOCIOECONOMIC_PROFILE"
    MODEL_INPUT_INCOMPLETE = "MODEL_INPUT_INCOMPLETE"


class IntegrationEventType(str, enum.Enum):
    PREDICTION_COMPLETED = "prediction.completed"
    CLINICIAN_REVIEW_COMPLETED = "clinician_review.completed"
    MODEL_ACTIVATED = "model.activated"
    TRAJECTORY_UPDATED = "trajectory.updated"
    ALERT_CREATED = "alert.created"
    PROGRESS_STAGNATING = "progress.stagnating"
    PROGRESS_DETERIORATING = "progress.deteriorating"
    FOLLOWUP_OVERDUE = "followup.overdue"
    COUNTERFACTUAL_REQUESTED = "counterfactual.requested"
    EXPLAINABILITY_REQUESTED = "explainability.requested"
    DRIFT_OBSERVATION = "drift.observation"
    MODEL_UPDATE_PROPOSED = "model.update_proposed"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    CHILD_VIEWED = "child_viewed"
    CHILD_CREATED = "child_created"
    CHILD_CHANGED = "child_changed"
    CHILD_REMOVED = "child_removed"
    VISIT_CREATED = "visit_created"
    VISIT_CHANGED = "visit_changed"
    VISIT_REMOVED = "visit_removed"
    PREDICTION_GENERATED = "prediction_generated"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_DISMISSED = "alert_dismissed"
    ALERT_IN_REVIEW = "alert_in_review"
    CLINICIAN_REVIEW_CREATED = "clinician_review_created"
    CLINICIAN_REVIEW_UPDATED = "clinician_review_updated"
    CLINICAL_NOTE_CREATED = "clinical_note_created"
    CLINICAL_NOTE_UPDATED = "clinical_note_updated"
    CLINICAL_NOTE_DELETED = "clinical_note_deleted"
    REPORT_EXPORTED = "report_exported"
    MODEL_VERSION_ACTIVATED = "model_version_activated"
    USER_CHANGED = "user_changed"
    FOLLOW_UP_CHANGED = "follow_up_changed"
    REASSESSMENT_REQUESTED = "reassessment_requested"
    C3_REASSESSMENT_REQUESTED = "c3_reassessment_requested"
    C3_REASSESSMENT_DELIVERED = "c3_reassessment_delivered"
    C4_PREDICTION_OBSERVATION_QUEUED = "c4_prediction_observation_queued"
    C4_MODEL_UPDATE_RECEIVED = "c4_model_update_received"
    MODEL_CANDIDATE_REGISTERED = "model_candidate_registered"
