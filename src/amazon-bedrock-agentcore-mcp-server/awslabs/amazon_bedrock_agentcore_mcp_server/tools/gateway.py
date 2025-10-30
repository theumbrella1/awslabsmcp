# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""AgentCore Gateway Tool - Manage AgentCore Gateway resources."""

import boto3
import json
import logging
import threading
from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    logger.propagate = False


def create_mcp_gateway(
    region: str = None,
    name: Optional[str] = None,
    role_arn: Optional[str] = None,
    authorizer_config: Optional[str] = None,
    enable_semantic_search: Optional[bool] = True,
) -> dict:
    """Create a new MCP Gateway asynchronously.

    Always runs in the background to avoid MCP timeouts. This uses the helper
    client which can auto-provision a role and authorizer if not provided.
    Check progress with the list tool afterwards.
    """
    logger = logging.getLogger('agentcore.mcp.gateway.background')
    logger.setLevel(logging.INFO)

    def _worker() -> None:
        try:
            toolkit_client = GatewayClient(region_name=region)
            json_authorizer_config_inner = ''
            if authorizer_config:
                json_authorizer_config_inner = json.loads(authorizer_config)
            toolkit_client.create_mcp_gateway(
                name,
                role_arn,
                json_authorizer_config_inner,
                enable_semantic_search,
            )
        except Exception as e:
            logger.warning('Background gateway creation error: %s', str(e))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return {
        'status': 'accepted',
        'message': 'Gateway creation started in background. Use list action to check status.',
        'name': name,
        'region': region,
    }


def create_mcp_gateway_target(
    gateway_arn: str = None,
    gateway_url: str = None,
    role_arn: str = None,
    region: str = None,
    name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_payload: Optional[Any] = None,
    credentials: Optional[Any] = None,
) -> dict:
    """Create a new MCP Gateway Target.

    target_type must be one of: openApiSchema | smithyModel | lambda | mcpServer.
    For openApiSchema and mcpServer, provide target_payload as a JSON string or object.
    For lambda and smithyModel, target_payload can be omitted to use sensible defaults.
    """
    client = GatewayClient(region_name=region)
    json_credentials = None
    json_target_payload = None
    if credentials is not None:
        if isinstance(credentials, str):
            json_credentials = json.loads(credentials)
        else:
            json_credentials = credentials
    if target_payload is not None:
        if isinstance(target_payload, str):
            json_target_payload = json.loads(target_payload)
        else:
            json_target_payload = target_payload
    # Validate target_type
    allowed_types = {'openApiSchema', 'smithyModel', 'lambda', 'mcpServer'}
    if target_type and target_type not in allowed_types:
        return {
            'status': 'error',
            'message': f"Invalid target_type '{target_type}'. Must be one of: {', '.join(sorted(allowed_types))}",
        }
    # Ensure a valid default for target_type so we don't override the client's default with None
    if not target_type:
        target_type = 'lambda'
    target = client.create_mcp_gateway_target(
        gateway={
            'gatewayArn': gateway_arn,
            'gatewayUrl': gateway_url,
            'gatewayId': gateway_arn.split('/')[-1],
            'roleArn': role_arn,
        },
        name=name,
        target_type=target_type,
        target_payload=json_target_payload,
        credentials=json_credentials,
    )
    return target


def list_mcp_gateways(
    region: str = None, name: Optional[str] = None, max_results: int = 50
) -> dict:
    """List gateways (optionally filter by exact name)."""
    client = boto3.client('bedrock-agentcore-control', region_name=region)

    next_token = None
    items = []
    while True:
        kwargs: Dict[str, Any] = {'maxResults': max_results}
        if next_token:
            kwargs['nextToken'] = next_token
        resp = client.list_gateways(**kwargs)
        batch = resp.get('items', [])
        if name:
            batch = [g for g in batch if g.get('name') == name]
        items.extend(batch)
        next_token = resp.get('nextToken')
        if not next_token or (name and items):
            break
    return {'items': items}


def get_mcp_gateway(
    region: str = None,
    gateway_identifier: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Get a single MCP Gateway by ID or by exact name.

    Provide either ``gateway_identifier`` (preferred) or ``name``. If ``name`` is
    provided, the function will list gateways and return the first exact match.
    """
    client = boto3.client('bedrock-agentcore-control', region_name=region)

    # Prefer explicit identifier when provided
    if gateway_identifier:
        try:
            return client.get_gateway(gatewayIdentifier=gateway_identifier)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    # Fallback to lookup by name
    if name:
        listed = list_mcp_gateways(region=region, name=name)
        items = listed.get('items', [])
        if not items:
            return {'status': 'not_found', 'message': 'No gateway found with that name'}
        gateway_id = items[0].get('gatewayId')
        if not gateway_id:
            return {'status': 'error', 'message': 'Listed gateway missing gatewayId'}
        try:
            return client.get_gateway(gatewayIdentifier=gateway_id)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    return {'status': 'error', 'message': 'Provide gateway_identifier or name'}


def delete_mcp_gateway(
    region: str = None,
    gateway_identifier: Optional[str] = None,
    name: Optional[str] = None,
    gateway_arn: Optional[str] = None,
) -> dict:
    """Delete a Gateway by id/arn or exact name.

    Ensures there are no targets before deletion.
    """
    client = boto3.client('bedrock-agentcore-control', region_name=region)

    resolved_id: Optional[str] = None
    if gateway_identifier:
        resolved_id = gateway_identifier.split('/')[-1]
    elif gateway_arn:
        resolved_id = gateway_arn.split('/')[-1]
    elif name:
        listed = list_mcp_gateways(region=region, name=name)
        items = listed.get('items', [])
        if not items:
            return {'status': 'error', 'message': 'No gateway found with that name'}
        resolved_id = items[0].get('gatewayId')
        if not resolved_id:
            return {'status': 'error', 'message': 'Listed gateway missing gatewayId'}
    else:
        return {'status': 'error', 'message': 'Provide gateway_identifier, gateway_arn, or name'}

    # Must have zero targets to delete
    targets_resp = client.list_gateway_targets(gatewayIdentifier=resolved_id)
    targets = targets_resp.get('items', [])
    if targets:
        return {
            'status': 'error',
            'message': f'Gateway has {len(targets)} target(s). Delete them first.',
        }

    client.delete_gateway(gatewayIdentifier=resolved_id)
    return {'status': 'success', 'gatewayId': resolved_id}


def delete_mcp_gateway_target(
    region: str = None,
    gateway_identifier: Optional[str] = None,
    name: Optional[str] = None,
    gateway_arn: Optional[str] = None,
    target_id: Optional[str] = None,
    target_name: Optional[str] = None,
) -> dict:
    """Delete a Gateway Target by id or exact name on a given gateway."""
    client = boto3.client('bedrock-agentcore-control', region_name=region)

    resolved_id: Optional[str] = None
    if gateway_identifier:
        resolved_id = gateway_identifier.split('/')[-1]
    elif gateway_arn:
        resolved_id = gateway_arn.split('/')[-1]
    elif name:
        listed = list_mcp_gateways(region=region, name=name)
        items = listed.get('items', [])
        if not items:
            return {'status': 'error', 'message': 'No gateway found with that name'}
        resolved_id = items[0].get('gatewayId')
        if not resolved_id:
            return {'status': 'error', 'message': 'Listed gateway missing gatewayId'}
    else:
        return {'status': 'error', 'message': 'Provide gateway_identifier, gateway_arn, or name'}

    resolved_target_id = target_id
    if not resolved_target_id and target_name:
        targets_resp = client.list_gateway_targets(gatewayIdentifier=resolved_id)
        for t in targets_resp.get('items', []):
            if t.get('name') == target_name:
                resolved_target_id = t.get('targetId')
                break
        if not resolved_target_id:
            return {'status': 'error', 'message': f'Target named {target_name} not found'}

    if not resolved_target_id:
        return {'status': 'error', 'message': 'Provide target_id or target_name'}

    client.delete_gateway_target(gatewayIdentifier=resolved_id, targetId=resolved_target_id)
    return {'status': 'success', 'gatewayId': resolved_id, 'targetId': resolved_target_id}


def list_mcp_gateway_targets(
    region: str = None,
    gateway_identifier: Optional[str] = None,
    name: Optional[str] = None,
    gateway_arn: Optional[str] = None,
    max_results: int = 50,
) -> dict:
    """List targets for a given gateway by id/arn or exact name."""
    client = boto3.client('bedrock-agentcore-control', region_name=region)

    resolved_id: Optional[str] = None
    if gateway_identifier:
        resolved_id = gateway_identifier.split('/')[-1]
    elif gateway_arn:
        resolved_id = gateway_arn.split('/')[-1]
    elif name:
        listed = list_mcp_gateways(region=region, name=name)
        items = listed.get('items', [])
        if not items:
            return {'status': 'error', 'message': 'No gateway found with that name'}
        resolved_id = items[0].get('gatewayId')
        if not resolved_id:
            return {'status': 'error', 'message': 'Listed gateway missing gatewayId'}
    else:
        return {'status': 'error', 'message': 'Provide gateway_identifier, gateway_arn, or name'}

    # Basic pagination loop
    next_token = None
    items = []
    while True:
        kwargs: Dict[str, Any] = {'gatewayIdentifier': resolved_id}
        if next_token:
            kwargs['nextToken'] = next_token
        resp = client.list_gateway_targets(**kwargs)
        batch = resp.get('items', [])
        items.extend(batch)
        next_token = resp.get('nextToken')
        if not next_token or len(items) >= max_results:
            break
    if len(items) > max_results:
        items = items[:max_results]
    return {'status': 'success', 'items': items, 'gatewayId': resolved_id}


def manage_agentcore_gateway(
    action: str,
    region: str = 'us-west-2',
    # Gateway fields
    name: Optional[str] = None,
    role_arn: Optional[str] = None,
    authorizer_config: Optional[Any] = None,
    enable_semantic_search: bool = True,
    gateway_identifier: Optional[str] = None,
    gateway_arn: Optional[str] = None,
    # Target fields
    gateway_url: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,  # openApiSchema|smithyModel|lambda|mcpServer
    target_payload: Optional[Any] = None,
    credentials: Optional[Any] = None,
    target_id: Optional[str] = None,
    # Common
    max_results: int = 50,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Manage Bedrock AgentCore Gateway resources.

    Args:
        action: Operation to perform:
            - "create_gateway": Create a new MCP Gateway
            - "create_target": Create a new Gateway Target for a gateway
            - "list_gateways": List Gateways
            - "get_gateway": Get Gateway by id or by exact name
            - "delete_gateway": Delete a Gateway (requires 0 targets)
            - "delete_gateway_target": Delete a specific Target by id or name
            - "list_gateway_targets": List Targets for a Gateway

        region: AWS region (default: us-west-2)

        name: Gateway name (create/list filter)
        role_arn: IAM role ARN for gateway runtime
        authorizer_config: Authorizer config as dict or JSON string
        enable_semantic_search: Enable semantic search in gateway
        gateway_identifier: Gateway id or arn for get/delete/list_targets
        gateway_arn: Gateway arn alternative to identifier for get/delete/list_targets

        gateway_arn: Gateway arn for creating targets
        gateway_url: Gateway URL as alternative to arn for target creation
        target_name: Target resource name (create/delete_target)
        target_id: Target id (delete_target)
        target_type: One of: openApiSchema | smithyModel | lambda | mcpServer
        target_payload: JSON string or dict payload (schema/server details)
        credentials: JSON string or dict credentials payload

        max_results: Max list results (default 50)
        verbose: Print progress for debugging

    Returns:
        Dict with status and content messages

    Examples:
        manage_agentcore_gateway(action="create_gateway", name="my-gw")
        manage_agentcore_gateway(action="list", name="my-gw")
        manage_agentcore_gateway(action="get", gateway_identifier="gw-123")
        manage_agentcore_gateway(
            action="create_target",
            gateway_arn="arn:aws:...:gateway/my-gw-abc",
            target_name="pets-api",
            target_type="openApiSchema",
            target_payload={"openapi": "3.0.0", ...},
        )
    """
    if verbose:
        print(f'🔧 Starting gateway operation: {action}', flush=True)

    try:
        if action == 'create_gateway':
            if not name:
                return {
                    'status': 'error',
                    'content': [{'text': 'name is required for create_gateway'}],
                }

            # Normalize authorizer_config to JSON string if dict provided
            auth_cfg_json: Optional[str] = None
            if isinstance(authorizer_config, dict):
                auth_cfg_json = json.dumps(authorizer_config)
            else:
                auth_cfg_json = authorizer_config

            if verbose:
                print(f'Creating gateway: {name}', flush=True)

            result = create_mcp_gateway(
                region=region,
                name=name,
                role_arn=role_arn,
                authorizer_config=auth_cfg_json,
                enable_semantic_search=enable_semantic_search,
            )

            return {
                'status': result.get('status', 'accepted'),
                'content': [
                    {'text': '**Gateway Create Requested** (asynchronous)'},
                    {'text': f'Message: {result.get("message", "")}'},
                    {'text': f'Name: {result.get("name", name)}'},
                    {'text': f'Region: {result.get("region", region)}'},
                ],
            }

        elif action == 'create_target':
            if not any([gateway_arn, gateway_url]):
                return {
                    'status': 'error',
                    'content': [{'text': 'gateway_arn or gateway_url required for create_target'}],
                }

            if verbose:
                print(f'Creating gateway target: {target_name or "(unnamed)"}', flush=True)

            parsed_payload = target_payload
            if isinstance(parsed_payload, str):
                try:
                    parsed_payload = json.loads(parsed_payload)
                except Exception:
                    return {
                        'status': 'error',
                        'content': [
                            {'text': 'target_payload must be valid JSON when provided as string'}
                        ],
                    }

            parsed_credentials = credentials
            if isinstance(parsed_credentials, str):
                try:
                    parsed_credentials = json.loads(parsed_credentials)
                except Exception:
                    return {
                        'status': 'error',
                        'content': [
                            {'text': 'credentials must be valid JSON when provided as string'}
                        ],
                    }

            # Validate requirements for specific target types
            if (target_type or 'lambda') == 'openApiSchema':
                if not parsed_payload:
                    return {
                        'status': 'error',
                        'content': [
                            {'text': 'openApiSchema requires target_payload (OpenAPI spec)'}
                        ],
                    }
                if not parsed_credentials or not isinstance(parsed_credentials, dict):
                    return {
                        'status': 'error',
                        'content': [
                            {
                                'text': (
                                    'openApiSchema requires credentials with either "api_key" or '
                                    '"oauth2_provider_config"'
                                )
                            }
                        ],
                    }

            result = create_mcp_gateway_target(
                gateway_arn=gateway_arn,
                gateway_url=gateway_url,
                role_arn=role_arn,
                region=region,
                name=target_name,
                target_type=target_type,
                target_payload=parsed_payload,
                credentials=parsed_credentials,
            )

            return {
                'status': 'success',
                'content': [
                    {'text': '**Gateway Target Created**'},
                    {'text': json.dumps(result, indent=2, default=str)},
                ],
            }

        elif action == 'list_gateways':
            if verbose:
                print(f'Listing gateways (max {max_results})...', flush=True)

            listed = list_mcp_gateways(region=region, name=name, max_results=max_results)
            items = listed.get('items', [])
            return {
                'status': 'success',
                'content': [
                    {'text': f'**Found {len(items)} gateways:**'},
                    {'text': json.dumps(items, indent=2, default=str)},
                ],
            }

        elif action == 'list_gateway_targets':
            if verbose:
                print('Listing gateway targets...', flush=True)

            result = list_mcp_gateway_targets(
                region=region,
                gateway_identifier=gateway_identifier,
                name=name,
                gateway_arn=gateway_arn,
                max_results=max_results,
            )
            if result.get('status') == 'error':
                return {
                    'status': 'error',
                    'content': [{'text': result.get('message', 'List failed')}],
                }
            items = result.get('items', [])
            return {
                'status': 'success',
                'content': [
                    {
                        'text': f'**Found {len(items)} targets for gateway {result.get("gatewayId")}**'
                    },
                    {'text': json.dumps(items, indent=2, default=str)},
                ],
            }

        elif action == 'get_gateway':
            if not any([gateway_identifier, name]):
                return {
                    'status': 'error',
                    'content': [{'text': 'gateway_identifier or name required for get'}],
                }

            got = get_mcp_gateway(region=region, gateway_identifier=gateway_identifier, name=name)

            if got.get('status') == 'error':
                return {
                    'status': 'error',
                    'content': [{'text': got.get('message', 'Unknown error')}],
                }
            if got.get('status') == 'not_found':
                return {'status': 'error', 'content': [{'text': got.get('message', 'Not found')}]}

            return {
                'status': 'success',
                'content': [
                    {'text': '**Gateway Details:**'},
                    {'text': json.dumps(got, indent=2, default=str)},
                ],
            }

        elif action == 'delete_gateway':
            result = delete_mcp_gateway(
                region=region,
                gateway_identifier=gateway_identifier,
                name=name,
                gateway_arn=gateway_arn,
            )
            if result.get('status') == 'error':
                return {
                    'status': 'error',
                    'content': [{'text': result.get('message', 'Delete failed')}],
                }
            return {
                'status': 'success',
                'content': [
                    {'text': '**Gateway Deleted Successfully**'},
                    {'text': f'Gateway ID: {result.get("gatewayId")}'},
                ],
            }

        elif action == 'delete_gateway_target':
            result = delete_mcp_gateway_target(
                region=region,
                gateway_identifier=gateway_identifier,
                name=name,
                gateway_arn=gateway_arn,
                target_id=target_id,
                target_name=target_name,
            )
            if result.get('status') == 'error':
                return {
                    'status': 'error',
                    'content': [{'text': result.get('message', 'Delete failed')}],
                }
            return {
                'status': 'success',
                'content': [
                    {'text': '**Gateway Target Deleted Successfully**'},
                    {'text': f'Gateway ID: {result.get("gatewayId")}'},
                    {'text': f'Target ID: {result.get("targetId")}'},
                ],
            }

        else:
            return {
                'status': 'error',
                'content': [
                    {
                        'text': (
                            f'Unknown action: {action}. Valid: create_gateway, create_target, list, get, '
                            'delete_gateway, delete_gateway_target, list_gateway_targets'
                        )
                    }
                ],
            }

    except Exception as e:
        if verbose:
            print(f'Unexpected Error: {str(e)}', flush=True)
        return {
            'status': 'error',
            'content': [
                {'text': f'**Unexpected Error:** {str(e)}'},
                {'text': f'**Action:** {action}'},
            ],
        }
