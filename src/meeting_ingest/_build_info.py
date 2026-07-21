"""Embedded runtime build identity.

Approved builds replace this file in their isolated staging tree. A source checkout
must remain visibly development-only.
"""

from __future__ import annotations


BUILD_INFO = {
    "schema_version": "1.0",
    "semantic_version": "0.1.0",
    "build_id": "development",
    "source_commit": None,
    "source_tree_sha256": None,
    "workflow_contract_version": "claude-code-session-v1",
    "build_kind": "development",
}
