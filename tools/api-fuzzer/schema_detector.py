"""OpenAPI / GraphQL schema detection module for api-fuzzer.

Probes common well-known endpoint paths to discover API documentation
and introspection endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

# Well-known OpenAPI / Swagger paths
OPENAPI_PATHS = [
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/swagger.yaml",
    "/swagger/",
    "/api-docs",
    "/api-docs.json",
    "/v1/openapi.json",
    "/v2/openapi.json",
    "/v3/openapi.json",
    "/api/v1/docs",
    "/api/v2/docs",
    "/api/v3/docs",
    "/docs",
    "/redoc",
]

# Well-known GraphQL paths
GRAPHQL_PATHS = [
    "/graphql",
    "/graphiql",
    "/graphql/console",
    "/gql",
]

GRAPHQL_INTROSPECTION_QUERY = '{"query": "{ __schema { types { name } } }"}'


async def detect_openapi(
    base_url: str,
    timeout: float = 10.0,
) -> list[dict[str, str]]:
    """Probe common OpenAPI/Swagger paths and return discovered endpoints.

    Returns a list of fact dicts with trait ``api.schema.openapi``.
    """
    base = base_url.rstrip("/")
    facts: list[dict[str, str]] = []

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, verify=False,
    ) as client:
        for path in OPENAPI_PATHS:
            url = f"{base}{path}"
            try:
                resp = await client.get(url)
                if resp.status_code < 400:
                    facts.append({
                        "trait": "api.schema.openapi",
                        "value": f"{url}|{resp.status_code}",
                    })
            except httpx.ConnectError:
                raise
            except httpx.HTTPError:
                continue
            except Exception:
                continue

    return facts


async def detect_graphql(
    base_url: str,
    timeout: float = 10.0,
) -> list[dict[str, str]]:
    """Probe common GraphQL paths with an introspection query.

    Returns facts with trait ``api.schema.graphql``.
    If introspection is available, ``value`` includes ``introspection=enabled``.
    If the endpoint exists but introspection is disabled, value includes
    ``introspection=disabled``.
    """
    base = base_url.rstrip("/")
    facts: list[dict[str, str]] = []

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, verify=False,
    ) as client:
        for path in GRAPHQL_PATHS:
            url = f"{base}{path}"
            try:
                resp = await client.post(
                    url,
                    content=GRAPHQL_INTROSPECTION_QUERY,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code < 400:
                    body = resp.text
                    if "__schema" in body or "__type" in body:
                        facts.append({
                            "trait": "api.schema.graphql",
                            "value": f"{url}|introspection=enabled",
                        })
                    else:
                        # Endpoint exists but introspection may be disabled
                        facts.append({
                            "trait": "api.schema.graphql",
                            "value": f"{url}|introspection=disabled",
                        })
            except httpx.HTTPError:
                continue
            except Exception:
                continue

    return facts


def parse_openapi_spec(spec_text: str, content_type: str = "") -> list[str]:
    """Parse an OpenAPI spec (JSON or YAML) and extract endpoint paths.

    Returns a list of endpoint strings like ``GET /users/{id}``.
    """
    data: dict[str, Any] | None = None

    # Try JSON first, then YAML
    import json

    try:
        data = json.loads(spec_text)
    except (json.JSONDecodeError, ValueError):
        try:
            data = yaml.safe_load(spec_text)
        except yaml.YAMLError:
            return []

    if not isinstance(data, dict):
        return []

    paths: dict[str, Any] = data.get("paths", {})
    if not isinstance(paths, dict):
        return []

    endpoints: list[str] = []
    http_methods = {"get", "post", "put", "patch", "delete", "head", "options"}

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            if method.lower() in http_methods:
                endpoints.append(f"{method.upper()} {path}")

    return endpoints
