from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    role: str = Field(pattern="^(landowner|company)$")
    organization: Optional[str] = None
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    role: str
    full_name: str
    user_id: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    full_name: str
    organization: Optional[str]
    phone: Optional[str]

    class Config:
        from_attributes = True


class KYCSubmit(BaseModel):
    full_name: str
    phone: str
    address: str
    id_document_ref: str


class KYCReview(BaseModel):
    status: str = Field(pattern="^(VERIFIED|REJECTED|UNDER_REVIEW)$")
    admin_notes: Optional[str] = None


class LandListingFromParcel(BaseModel):
    parcel_id: int
    title: Optional[str] = None
    lease_duration_years: int = Field(ge=1, le=99)
    lease_type: str = "land_lease"
    notes: Optional[str] = None
    project_duration_years: int = 20


class LandVerificationReview(BaseModel):
    status: str = Field(pattern="^(VERIFIED|REJECTED|UNDER_REVIEW)$")
    admin_notes: Optional[str] = None


class LeaseInquiryCreate(BaseModel):
    listing_id: int
    message: str = Field(min_length=10, max_length=2000)
    proposed_lease_years: Optional[int] = Field(default=None, ge=1, le=99)


class LeaseInquiryRespond(BaseModel):
    status: str = Field(pattern="^(ACCEPTED|DECLINED)$")
    landowner_response: str = Field(min_length=5, max_length=2000)


class ContractSign(BaseModel):
    typed_name: str = Field(min_length=2, max_length=200)


class PaymentRecord(BaseModel):
    amount_inr: float = Field(gt=0)
    reference: str = Field(min_length=3, max_length=200)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class IssuanceSubmit(BaseModel):
    """Landowner request to move a listing into the Verra/Gold Standard-style verification pipeline."""
    registry: str = Field(pattern="^(VERRA|GOLD_STANDARD)$")
    methodology: str = Field(min_length=3, max_length=50)
    evidence_notes: Optional[str] = Field(default=None, max_length=4000)


class IssuanceReview(BaseModel):
    """Admin action advancing an issuance record through the verification workflow."""
    status: str = Field(pattern="^(UNDER_VERIFICATION|VERIFIED|ISSUED|REJECTED)$")
    verifier_name: Optional[str] = Field(default=None, max_length=200)
    verifier_notes: Optional[str] = Field(default=None, max_length=4000)
    verified_annual_tco2e: Optional[float] = Field(default=None, gt=0)
    issued_total_tco2e: Optional[float] = Field(default=None, gt=0)
    registry_serial_number: Optional[str] = Field(default=None, max_length=200)
