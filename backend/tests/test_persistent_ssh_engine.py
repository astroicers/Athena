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

"""Tests for Phase D — PersistentSSHChannelEngine."""
import pytest


def test_ssh_common_exports_technique_executors():
    from app.clients._ssh_common import TECHNIQUE_EXECUTORS
    assert "T1592" in TECHNIQUE_EXECUTORS
    assert "T1003.001" in TECHNIQUE_EXECUTORS
    assert len(TECHNIQUE_EXECUTORS) >= 13


def test_ssh_common_exports_parse_credential():
    from app.clients._ssh_common import _parse_credential
    user, password, host, port = _parse_credential("root:toor@192.168.1.1:22")
    assert user == "root"
    assert password == "toor"
    assert host == "192.168.1.1"
    assert port == 22


def test_ssh_common_parse_credential_default_port():
    from app.clients._ssh_common import _parse_credential
    user, password, host, port = _parse_credential("admin:pass@10.0.0.1")
    assert port == 22
    assert host == "10.0.0.1"


def test_ssh_common_exports_parse_stdout_to_facts():
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "Linux kali 5.10\nroot\n")
    assert len(facts) >= 1
    assert facts[0]["trait"] in ("host.os", "host.user")
    assert "value" in facts[0]
    assert facts[0]["source"] == "direct_ssh"


def test_ssh_common_parse_stdout_empty_returns_no_facts():
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "")
    assert facts == []

def test_ssh_common_parse_stdout_custom_source():
    from app.clients._ssh_common import _parse_stdout_to_facts
    facts = _parse_stdout_to_facts("T1592", "Linux kali 5.10\n", source="persistent_ssh")
    assert facts[0]["source"] == "persistent_ssh"
