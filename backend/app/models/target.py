# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
