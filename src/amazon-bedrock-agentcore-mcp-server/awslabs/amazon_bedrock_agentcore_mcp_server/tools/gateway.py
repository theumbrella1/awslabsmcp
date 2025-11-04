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

"""AgentCore Gateway Tool - Manage AgentCore Gateway resources.

Comprehensive gateway operations including create, list, get, delete, and target management.
"""

import json
import threading
from typing import Any, Dict, Optional

import boto3
from bedrock_agentcore_starter_toolkit.operations.gateway import GatewayClient
from botocore.exceptions import ClientError


def _create_gateway(
    name: str,
    role_arn: Optional[str],
    authorizer_config: Optional[str],
    enable_semantic_search: bool,
    region: str,
) -> Dict[str, Any]:
    """Create new gateway resource."""
    if not name:
        return {
            'status': 'error',
            'content': [{'text': 'name is required for create_gateway action'}],
        }

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
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    return {
        'status': 'success',
        'content': [
            {'text': '**Gateway Create Requested** (asynchronous)'},
            {'text': 'Gateway creation started in background. Use list action to check status. It will take ~1 min'},
            {'text': f'**Name:** {name}'},
            {'text': f'**Region:** {region}'},
        ],
    }


def _create_target(
    gateway_arn: Optional[str],
    gateway_url: Optional[str],
    role_arn: Optional[str],
    target_name: Optional[str],
    target_type: Optional[str],
    target_payload: Optional[Any],
    credentials: Optional[Any],
    region: str,
) -> Dict[str, Any]:
    """Create gateway target."""
    if not any([gateway_arn, gateway_url]):
        return {
            'status': 'error',
            'content': [{'text': 'gateway_arn or gateway_url required for create_target'}],
        }

    # Validate target_type
    allowed_types = {'openApiSchema', 'smithyModel', 'lambda', 'mcpServer'}
    if target_type and target_type not in allowed_types:
        return {
            'status': 'error',
            'content': [
                {
                    'text': f"Invalid target_type '{target_type}'. Must be one of: {', '.join(sorted(allowed_types))}"
                }
            ],
        }

    # Parse JSON strings
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

    # Validate requirements for specific target types
    if (target_type or 'lambda') == 'openApiSchema':
        if not json_target_payload:
            return {
                'status': 'error',
                'content': [{'text': 'openApiSchema requires target_payload (OpenAPI spec)'}],
            }
        if not json_credentials or not isinstance(json_credentials, dict):
            return {
                'status': 'error',
                'content': [
                    {
                        'text': 'openApiSchema requires credentials with either "api_key" or "oauth2_provider_config"'
                    }
                ],
            }

    if not target_type:
        target_type = 'lambda'

    client = GatewayClient(region_name=region)
    target = client.create_mcp_gateway_target(
        gateway={
            'gatewayArn': gateway_arn,
            'gatewayUrl': gateway_url,
            'gatewayId': gateway_arn.split('/')[-1] if gateway_arn else None,
            'roleArn': role_arn,
        },
        name=target_name,
        target_type=target_type,
        target_payload=json_target_payload,
        credentials=json_credentials,
    )

    return {
        'status': 'success',
        'content': [
            {'text': '**Gateway Target Created**'},
            {'target': target},
        ],
    }


def _list_gateways(
    name: Optional[str],
    max_results: int,
    region: str,
    control_client: Any,
) -> Dict[str, Any]:
    """List all gateways."""
    next_token = None
    items = []
    while True:
        kwargs: Dict[str, Any] = {'maxResults': min(max_results - len(items), 100)}
        if next_token:
            kwargs['nextToken'] = next_token
        resp = control_client.list_gateways(**kwargs)
        batch = resp.get('items', [])
        if name:
            batch = [g for g in batch if g.get('name') == name]
        items.extend(batch)
        next_token = resp.get('nextToken')
        if not next_token or (name and items) or len(items) >= max_results:
            break

    return {
        'status': 'success',
        'content': [
            {'text': f'**Found {len(items)} gateways:**'},
            {'items': items},
        ],
    }


def _get_gateway(
    gateway_identifier: Optional[str],
    name: Optional[str],
    region: str,
    control_client: Any,
) -> Dict[str, Any]:
    """Get gateway details."""
    if not any([gateway_identifier, name]):
        return {
            'status': 'error',
            'content': [{'text': 'gateway_identifier or name required for get_gateway'}],
        }

    # Prefer explicit identifier
    if gateway_identifier:
        try:
            result = control_client.get_gateway(gatewayIdentifier=gateway_identifier)
            return {
                'status': 'success',
                'content': [
                    {'text': '**Gateway Details:**'},
                    {'result': result},
                ],
            }
        except Exception as e:
            return {'status': 'error', 'content': [{'text': str(e)}]}

    # Lookup by name
    if name:
        next_token = None
        while True:
            kwargs: Dict[str, Any] = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = control_client.list_gateways(**kwargs)
            items = [g for g in resp.get('items', []) if g.get('name') == name]
            if items:
                gateway_id = items[0].get('gatewayId')
                if not gateway_id:
                    return {
                        'status': 'error',
                        'content': [{'text': 'Listed gateway missing gatewayId'}],
                    }
                try:
                    result = control_client.get_gateway(gatewayIdentifier=gateway_id)
                    return {
                        'status': 'success',
                        'content': [
                            {'text': '**Gateway Details:**'},
                            {'result': result},
                        ],
                    }
                except Exception as e:
                    return {'status': 'error', 'content': [{'text': str(e)}]}
            next_token = resp.get('nextToken')
            if not next_token:
                break

        return {'status': 'error', 'content': [{'text': 'No gateway found with that name'}]}


def _delete_gateway(
    gateway_identifier: Optional[str],
    name: Optional[str],
    gateway_arn: Optional[str],
    region: str,
    control_client: Any,
) -> Dict[str, Any]:
    """Delete gateway resource."""
    resolved_id: Optional[str] = None
    if gateway_identifier:
        resolved_id = gateway_identifier.split('/')[-1]
    elif gateway_arn:
        resolved_id = gateway_arn.split('/')[-1]
    elif name:
        next_token = None
        while True:
            kwargs: Dict[str, Any] = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = control_client.list_gateways(**kwargs)
            items = [g for g in resp.get('items', []) if g.get('name') == name]
            if items:
                resolved_id = items[0].get('gatewayId')
                break
            next_token = resp.get('nextToken')
            if not next_token:
                break
        if not resolved_id:
            return {'status': 'error', 'content': [{'text': 'No gateway found with that name'}]}
    else:
        return {
            'status': 'error',
            'content': [{'text': 'gateway_identifier, gateway_arn, or name required'}],
        }

    # Must have zero targets to delete
    targets_resp = control_client.list_gateway_targets(gatewayIdentifier=resolved_id)
    targets = targets_resp.get('items', [])
    if targets:
        return {
            'status': 'error',
            'content': [{'text': f'Gateway has {len(targets)} target(s). Delete them first.'}],
        }

    control_client.delete_gateway(gatewayIdentifier=resolved_id)

    return {
        'status': 'success',
        'content': [
            {'text': '**Gateway Deleted Successfully**'},
            {'text': f'**Gateway ID:** {resolved_id}'},
        ],
    }


def _list_targets(
    gateway_identifier: Optional[str],
    name: Optional[str],
    gateway_arn: Optional[str],
    max_results: int,
    region: str,
    control_client: Any,
) -> Dict[str, Any]:
    """List gateway targets."""
    resolved_id: Optional[str] = None
    if gateway_identifier:
        resolved_id = gateway_identifier.split('/')[-1]
    elif gateway_arn:
        resolved_id = gateway_arn.split('/')[-1]
    elif name:
        next_token = None
        while True:
            kwargs: Dict[str, Any] = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = control_client.list_gateways(**kwargs)
            items = [g for g in resp.get('items', []) if g.get('name') == name]
            if items:
                resolved_id = items[0].get('gatewayId')
                break
            next_token = resp.get('nextToken')
            if not next_token:
                break
        if not resolved_id:
            return {'status': 'error', 'content': [{'text': 'No gateway found with that name'}]}
    else:
        return {
            'status': 'error',
            'content': [{'text': 'gateway_identifier, gateway_arn, or name required'}],
        }

    next_token = None
    items = []
    while True:
        kwargs: Dict[str, Any] = {'gatewayIdentifier': resolved_id}
        if next_token:
            kwargs['nextToken'] = next_token
        resp = control_client.list_gateway_targets(**kwargs)
        batch = resp.get('items', [])
        items.extend(batch)
        next_token = resp.get('nextToken')
        if not next_token or len(items) >= max_results:
            break
    if len(items) > max_results:
        items = items[:max_results]

    return {
        'status': 'success',
        'content': [
            {'text': f'**Found {len(items)} targets for gateway {resolved_id}:**'},
            {'items': items},
        ],
    }


def _delete_target(
    gateway_identifier: Optional[str],
    name: Optional[str],
    gateway_arn: Optional[str],
    target_id: Optional[str],
    target_name: Optional[str],
    region: str,
    control_client: Any,
) -> Dict[str, Any]:
    """Delete gateway target."""
    resolved_id: Optional[str] = None
    if gateway_identifier:
        resolved_id = gateway_identifier.split('/')[-1]
    elif gateway_arn:
        resolved_id = gateway_arn.split('/')[-1]
    elif name:
        next_token = None
        while True:
            kwargs: Dict[str, Any] = {'maxResults': 100}
            if next_token:
                kwargs['nextToken'] = next_token
            resp = control_client.list_gateways(**kwargs)
            items = [g for g in resp.get('items', []) if g.get('name') == name]
            if items:
                resolved_id = items[0].get('gatewayId')
                break
            next_token = resp.get('nextToken')
            if not next_token:
                break
        if not resolved_id:
            return {'status': 'error', 'content': [{'text': 'No gateway found with that name'}]}
    else:
        return {
            'status': 'error',
            'content': [{'text': 'gateway_identifier, gateway_arn, or name required'}],
        }

    resolved_target_id = target_id
    if not resolved_target_id and target_name:
        targets_resp = control_client.list_gateway_targets(gatewayIdentifier=resolved_id)
        for t in targets_resp.get('items', []):
            if t.get('name') == target_name:
                resolved_target_id = t.get('targetId')
                break
        if not resolved_target_id:
            return {
                'status': 'error',
                'content': [{'text': f'Target named {target_name} not found'}],
            }

    if not resolved_target_id:
        return {'status': 'error', 'content': [{'text': 'target_id or target_name required'}]}

    control_client.delete_gateway_target(gatewayIdentifier=resolved_id, targetId=resolved_target_id)

    return {
        'status': 'success',
        'content': [
            {'text': '**Gateway Target Deleted Successfully**'},
            {'text': f'**Gateway ID:** {resolved_id}'},
            {'text': f'**Target ID:** {resolved_target_id}'},
        ],
    }


def manage_agentcore_gateway(
    action: str,
    region: str = 'us-west-2',
    name: Optional[str] = None,
    role_arn: Optional[str] = None,
    authorizer_config: Optional[Any] = None,
    enable_semantic_search: bool = True,
    gateway_identifier: Optional[str] = None,
    gateway_arn: Optional[str] = None,
    gateway_url: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_payload: Optional[Any] = None,
    credentials: Optional[Any] = None,
    target_id: Optional[str] = None,
    max_results: int = 50,
) -> Dict[str, Any]:
    """Manage Bedrock AgentCore Gateway resources.

    Args:
        action: Gateway operation to perform:
            - "create_gateway": Create new MCP Gateway
            - "create_target": Create new Gateway Target
            - "list_gateways": List all Gateways
            - "get_gateway": Get Gateway details by id or name
            - "delete_gateway": Delete Gateway (requires 0 targets)
            - "list_gateway_targets": List Targets for a Gateway
            - "delete_gateway_target": Delete specific Target

        region: AWS region (default: us-west-2)
        name: Gateway name (required for create_gateway, optional filter for list)
        role_arn: IAM role ARN for gateway runtime
        authorizer_config: Authorizer config as dict or JSON string
        enable_semantic_search: Enable semantic search in gateway (default: True)
        gateway_identifier: Gateway id or arn for operations
        gateway_arn: Gateway arn (alternative to identifier)
        gateway_url: Gateway URL for target creation
        target_name: Target resource name
        target_type: One of: openApiSchema | smithyModel | lambda | mcpServer
        target_payload: JSON string or dict payload (schema/server details)
        credentials: JSON string or dict credentials payload
        target_id: Target id for delete operations
        max_results: Maximum results for list operations (default: 50)

    Returns:
        Dict with status and operation results

    Examples:
        # Create gateway
        gateway(action="create_gateway", name="my-gateway")

        # List gateways
        gateway(action="list_gateways")

        # Get gateway details
        gateway(action="get_gateway", gateway_identifier="gw-123")

        # Create target
        gateway(
            action="create_target",
            gateway_arn="arn:aws:...:gateway/my-gw-abc",
            target_name="pets-api",
            target_type="openApiSchema",
            target_payload={"openapi": "3.0.0", ...},
            credentials={"api_key": "..."}
        )

        # List targets
        gateway(action="list_gateway_targets", gateway_identifier="gw-123")

        # Delete target
        gateway(
            action="delete_gateway_target",
            gateway_identifier="gw-123",
            target_id="target-456"
        )

        # Delete gateway
        gateway(action="delete_gateway", gateway_identifier="gw-123")
    """
    try:
        # Initialize client
        control_client = boto3.client('bedrock-agentcore-control', region_name=region)

        # Normalize authorizer_config to JSON string if dict
        auth_cfg_json: Optional[str] = None
        if isinstance(authorizer_config, dict):
            auth_cfg_json = json.dumps(authorizer_config)
        else:
            auth_cfg_json = authorizer_config

        # Action dispatch registry
        action_handlers: Dict[str, Any] = {
            'create_gateway': lambda: _create_gateway(
                name=name,
                role_arn=role_arn,
                authorizer_config=auth_cfg_json,
                enable_semantic_search=enable_semantic_search,
                region=region,
            ),
            'create_target': lambda: _create_target(
                gateway_arn=gateway_arn,
                gateway_url=gateway_url,
                role_arn=role_arn,
                target_name=target_name,
                target_type=target_type,
                target_payload=target_payload,
                credentials=credentials,
                region=region,
            ),
            'list_gateways': lambda: _list_gateways(
                name=name,
                max_results=max_results,
                region=region,
                control_client=control_client,
            ),
            'get_gateway': lambda: _get_gateway(
                gateway_identifier=gateway_identifier,
                name=name,
                region=region,
                control_client=control_client,
            ),
            'delete_gateway': lambda: _delete_gateway(
                gateway_identifier=gateway_identifier,
                name=name,
                gateway_arn=gateway_arn,
                region=region,
                control_client=control_client,
            ),
            'list_gateway_targets': lambda: _list_targets(
                gateway_identifier=gateway_identifier,
                name=name,
                gateway_arn=gateway_arn,
                max_results=max_results,
                region=region,
                control_client=control_client,
            ),
            'delete_gateway_target': lambda: _delete_target(
                gateway_identifier=gateway_identifier,
                name=name,
                gateway_arn=gateway_arn,
                target_id=target_id,
                target_name=target_name,
                region=region,
                control_client=control_client,
            ),
        }

        # Dispatch to appropriate handler
        handler = action_handlers.get(action)
        if not handler:
            return {
                'status': 'error',
                'content': [
                    {
                        'text': f'Unknown action: {action}. Valid: {", ".join(action_handlers.keys())}'
                    }
                ],
            }

        result = handler()
        return result

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        return {
            'status': 'error',
            'content': [
                {'text': f'**AWS Error ({error_code}):** {error_message}'},
                {'text': f'**Action:** {action}'},
                {'text': f'**Region:** {region}'},
            ],
        }

    except Exception as e:
        return {
            'status': 'error',
            'content': [
                {'text': f'**Unexpected Error:** {str(e)}'},
                {'text': f'**Action:** {action}'},
            ],
        }
