from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from app.models.authentication import AuthTerms

TERMS_VERSION = '2026-10-13'


class TermsAcceptance(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Literal['2026-10-11', '2026-10-13']
    age_band: Literal['under_18', '18_plus'] | None = None
    accepted: Literal[True]
    guardian_declared: bool = False

    @model_validator(mode='after')
    def require_guardian(self):
        if self.version == TERMS_VERSION:
            if self.age_band is not None or self.guardian_declared:
                raise ValueError('The current acceptance does not collect an age group or separate guardian declaration.')
            return self
        if self.age_band is None:
            raise ValueError('Reload signup to use the current acceptance form.')
        if self.age_band == 'under_18' and not self.guardian_declared:
            raise ValueError('Ask your parent or legal guardian to review and accept before continuing.')
        return self


def accept_terms(account, body, now):
    if account.terms is None:
        account.terms = AuthTerms(version=TERMS_VERSION)
    account.terms.version = body.version
    account.terms.age_band = body.age_band
    account.terms.accepted_by = ('adult_or_guardian_declaration' if body.version == TERMS_VERSION
                                 else 'guardian_declaration' if body.age_band == 'under_18' else 'adult_self')
    account.terms.accepted_at = now
