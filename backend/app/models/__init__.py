"""SQLAlchemy models for the full Jee Edge schema (docs/database-schema.md).

Split by domain, all sharing app.database.Base, mirroring the layout suggested
in section 14 ("Suggested model layout") of the schema doc. Every class is
re-exported here so callers can keep doing `from app import models` and
`models.User`, as before the split.
"""

from app.models.admin import (
    AuditLog,
    ImportRun,
    IntegrityFlag,
    QuestionReport,
    QuestionRevision,
    QuestionReview,
    RegradeRun,
)
from app.models.content import Asset, Chapter, Passage, Question, QuestionOption, QuestionSubtopic, Subject, Subtopic
from app.models.identity import GuardianConsent, StudentProfile, User
from app.models.profile_avatar import ProfileAvatar
from app.models.learning import StudentChapterCoverage, StudentSubtopicStats
from app.models.predictor import (
    PredictorAdvancedMarksRankAnchor,
    PredictorAdvancedQualifyingCutoff,
    PredictorAttemptPrediction,
    PredictorImportRun,
    PredictorInstitute,
    PredictorJosaaCutoff,
    PredictorMainCohortMetric,
    PredictorMainMarksEstimate,
    PredictorMainPercentileAnchor,
    PredictorNirfRanking,
    PredictorProgram,
)
from app.models.publishing import Leaderboard, LeaderboardEntry, ShareCard
from app.models.ratings import QuestionRating, RatingEvent, StudentRating, StudentSubjectRating
from app.models.rewards import (
    DailyQuestionAssignment,
    EdgeCoinTransaction,
    RewardCatalogItem,
    RewardRedemption,
)
from app.models.scenarios import ScenarioRun
from app.models.tests import QuestionResponse, ResponseOption, Test, TestAttempt, TestQuestion

__all__ = [
    "User",
    "ProfileAvatar",
    "StudentProfile",
    "GuardianConsent",
    "Subject",
    "Chapter",
    "Subtopic",
    "Passage",
    "Question",
    "QuestionOption",
    "QuestionSubtopic",
    "Asset",
    "Test",
    "TestQuestion",
    "TestAttempt",
    "QuestionResponse",
    "ResponseOption",
    "StudentSubtopicStats",
    "StudentChapterCoverage",
    "StudentRating",
    "StudentSubjectRating",
    "QuestionRating",
    "RatingEvent",
    "Leaderboard",
    "LeaderboardEntry",
    "ShareCard",
    "ImportRun",
    "QuestionRevision",
    "QuestionReview",
    "QuestionReport",
    "RegradeRun",
    "IntegrityFlag",
    "AuditLog",
    "PredictorInstitute",
    "PredictorProgram",
    "PredictorJosaaCutoff",
    "PredictorMainPercentileAnchor",
    "PredictorMainMarksEstimate",
    "PredictorMainCohortMetric",
    "PredictorAdvancedMarksRankAnchor",
    "PredictorAdvancedQualifyingCutoff",
    "PredictorNirfRanking",
    "PredictorImportRun",
    "PredictorAttemptPrediction",
    "EdgeCoinTransaction",
    "RewardCatalogItem",
    "RewardRedemption",
    "DailyQuestionAssignment",
    "ScenarioRun",
]

from app.models.ranking import JeeXRating, RatedContest, ContestEntry

from app.models.public_profile import PublicProfile

from app.models.authentication import AuthAccount, AuthSession, AuthEmailToken, AuthRateLimit, GoogleIdentity
