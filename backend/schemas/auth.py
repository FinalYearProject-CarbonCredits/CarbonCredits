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
    role: str
    full_name: str
    user_id: int


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

