from pydantic import BaseModel

from .enums import C5ISRDomain, C5ISRDomainStatus


class C5ISRStatus(BaseModel):
    id: str
    operation_id: str
    domain: C5ISRDomain
    status: C5ISRDomainStatus
    health_pct: float                   # 0-100
    detail: str = ""
