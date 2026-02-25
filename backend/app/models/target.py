from pydantic import BaseModel


class Target(BaseModel):
    id: str
    hostname: str                       # "DC-01"
    ip_address: str                     # "10.0.1.5"
    os: str | None = None               # "Windows Server 2019"
    role: str                           # "Domain Controller"
    network_segment: str                # "10.0.1.0/24"
    is_compromised: bool = False
    privilege_level: str | None = None  # "SYSTEM" | "Admin" | "User"
    operation_id: str
