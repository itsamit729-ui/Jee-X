from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from app.models.authentication import AuthTerms

TERMS_VERSION = '2026-10-11'


class TermsAcceptance(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Literal['2026-10-11']
    age_band: Literal['under_18', '18_plus']
    accepted: Literal[True]
    guardian_declared: bool = False

    @model_validator(mode='after')
    def require_guardian(self):
        if self.age_band == 'under_18' and not self.guardian_declared:
            raise ValueError('Ask your parent or legal guardian to review and accept before continuing.')
        return self


def accept_terms(account, body, now):
    if account.terms is None:
        account.terms = AuthTerms(version=TERMS_VERSION)
    account.terms.version = TERMS_VERSION
    account.terms.age_band = body.age_band
    account.terms.accepted_by = 'guardian_declaration' if body.age_band == 'under_18' else 'adult_self'
    account.terms.accepted_at = now
