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

"""AgentCore Identity Tool - Manage OAuth2, API Keys, and Workload Identities.

Comprehensive identity management for AgentCore agents.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    logger.propagate = False


def _format_success_response(title: str, *content_items: Dict[str, Any]) -> Dict[str, Any]:
    """Format a successful operation response."""
    return {
        'status': 'success',
        'content': [
            {'text': title},
            *content_items,
        ],
    }


def _create_oauth2_provider(
    client: Any,
    name: str,
    vendor: Optional[str],
    client_id: Optional[str],
    client_secret: Optional[str],
    discovery_url: Optional[str],
    verbose: bool,
) -> Dict[str, Any]:
    """Create OAuth2 credential provider."""
    if not all([vendor, client_id, client_secret]):
        return {
            'status': 'error',
            'content': [{'text': 'vendor, client_id, and client_secret required for OAuth2'}],
        }

    if verbose:
        print(f'Creating OAuth2 provider: {name} ({vendor})', flush=True)

    oauth2_config = {}
    if vendor == 'SlackOauth2':
        oauth2_config['slackOauth2ProviderConfig'] = {
            'clientId': client_id,
            'clientSecret': client_secret,
        }
    elif vendor == 'GithubOauth2':
        oauth2_config['githubOauth2ProviderConfig'] = {
            'clientId': client_id,
            'clientSecret': client_secret,
        }
    elif vendor == 'GoogleOauth2':
        oauth2_config['googleOauth2ProviderConfig'] = {
            'clientId': client_id,
            'clientSecret': client_secret,
        }
    elif vendor == 'CustomOauth2':
        if not discovery_url:
            return {
                'status': 'error',
                'content': [{'text': 'discovery_url required for CustomOauth2'}],
            }
        oauth2_config['customOauth2ProviderConfig'] = {
            'oauthDiscovery': {'discoveryUrl': discovery_url},
            'clientId': client_id,
            'clientSecret': client_secret,
        }
    else:
        return {
            'status': 'error',
            'content': [
                {
                    'text': f'Unknown vendor: {vendor}. Valid: SlackOauth2, GitHubOauth2, GoogleOauth2, CustomOauth2'
                }
            ],
        }

    params = {
        'name': name,
        'credentialProviderVendor': vendor,
        'oauth2ProviderConfigInput': oauth2_config,
    }

    response = client.create_oauth2_credential_provider(**params)

    return _format_success_response(
        '**OAuth2 Credential Provider Created**',
        {'text': f'**Name:** {name}'},
        {'text': f'**Vendor:** {vendor}'},
        {'text': f'**Callback URL:** {response.get("callbackUrl", "Not available")}'},
        {'text': f'**ARN:** {response.get("credentialProviderArn")}'},
    )


def _create_api_key_provider(
    client: Any,
    name: str,
    api_key: Optional[str],
    verbose: bool,
) -> Dict[str, Any]:
    """Create API key credential provider."""
    if not api_key:
        return {
            'status': 'error',
            'content': [{'text': 'api_key required for API key provider'}],
        }

    if verbose:
        print(f'Creating API key provider: {name}', flush=True)

    response = client.create_api_key_credential_provider(name=name, apiKey=api_key)

    return _format_success_response(
        '**API Key Credential Provider Created**',
        {'text': f'**Name:** {name}'},
        {'text': f'**ARN:** {response.get("credentialProviderArn")}'},
    )


def _get(
    client: Any,
    name: str,
    provider_type: str,
    verbose: bool,
) -> Dict[str, Any]:
    """Get provider details."""
    if verbose:
        print(f'Getting {provider_type} provider: {name}', flush=True)

    if provider_type == 'oauth2':
        response = client.get_oauth2_credential_provider(name=name)
    elif provider_type == 'api_key':
        response = client.get_api_key_credential_provider(name=name)
    else:
        return {
            'status': 'error',
            'content': [{'text': f'Unknown provider_type: {provider_type}'}],
        }

    return {
        'status': 'success',
        'content': [
            {'text': f'**{provider_type.upper()} Provider Details:**'},
            {'provider': response},
        ],
    }


def _list(
    client: Any,
    provider_type: str,
    max_results: int,
    verbose: bool,
) -> Dict[str, Any]:
    """List providers."""
    if verbose:
        print(f'Listing {provider_type} providers (max {max_results})...', flush=True)

    if provider_type == 'oauth2':
        response = client.list_oauth2_credential_providers(maxResults=min(max_results, 100))
        items = response.get('credentialProviders', [])
    elif provider_type == 'api_key':
        response = client.list_api_key_credential_providers(maxResults=min(max_results, 100))
        items = response.get('credentialProviders', [])
    else:
        return {
            'status': 'error',
            'content': [{'text': f'Unknown provider_type: {provider_type}'}],
        }

    return {
        'status': 'success',
        'content': [
            {'text': f'**Found {len(items)} {provider_type} providers:**'},
            {'providers': items},
        ],
    }


def _delete(
    client: Any,
    name: str,
    provider_type: str,
    verbose: bool,
) -> Dict[str, Any]:
    """Delete provider."""
    if verbose:
        print(f'Deleting {provider_type} provider: {name}', flush=True)

    if provider_type == 'oauth2':
        client.delete_oauth2_credential_provider(name=name)
    elif provider_type == 'api_key':
        client.delete_api_key_credential_provider(name=name)
    else:
        return {
            'status': 'error',
            'content': [{'text': f'Unknown provider_type: {provider_type}'}],
        }

    return _format_success_response(
        f'**{provider_type.upper()} Provider Deleted**',
        {'text': f'**Name:** {name}'},
    )


def manage_agentcore_identity(
    action: str,
    name: Optional[str] = None,
    provider_type: str = 'oauth2',
    # OAuth2 specific
    vendor: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    discovery_url: Optional[str] = None,
    # API Key specific
    api_key: Optional[str] = None,
    # Common
    max_results: int = 20,
    region: str = 'us-west-2',
    verbose: bool = False,
) -> Dict[str, Any]:
    """Manage OAuth2 and API key credentials for AgentCore agents.

    Args:
        action: Operation to perform:
            - "create": Create new credential provider
            - "get": Get provider details
            - "list": List all providers
            - "delete": Delete provider

        name: Provider name (required for most operations)
        provider_type: oauth2 (default) or api_key

        # OAuth2 specific
        vendor: SlackOauth2, GithubOauth2, GoogleOauth2, or CustomOauth2
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret (stored encrypted)
        discovery_url: OAuth2 discovery URL (for CustomOauth2)

        # API Key specific
        api_key: API key value (stored encrypted)

        # Common
        max_results: Max results for list (1-100, default: 20)
        region: AWS region (default: us-west-2)
        verbose: Enable verbose logging (default: False)

    Returns:
        Dict with status and operation results

    Examples:
        # Create OAuth2 provider
        identity(
            action="create",
            name="slack-oauth",
            provider_type="oauth2",
            vendor="SlackOauth2",
            client_id="your-client-id",
            client_secret="your-client-secret"
        )

        # Create API key provider
        identity(
            action="create",
            name="api-provider",
            provider_type="api_key",
            api_key="your-api-key"
        )

        # List providers
        identity(action="list", provider_type="oauth2")

        # Delete provider
        identity(action="delete", name="slack-oauth", provider_type="oauth2")
    """

    if verbose:
        print(f'Starting identity operation: {action} ({provider_type})', flush=True)

    try:
        client = boto3.client('bedrock-agentcore-control', region_name=region)

        if verbose:
            print(f'Initialized client for region: {region}', flush=True)

        # Action dispatch registry
        action_handlers: Dict[str, Any] = {
            'create': lambda: (
                _create_oauth2_provider(
                    client=client,
                    name=name,
                    vendor=vendor,
                    client_id=client_id,
                    client_secret=client_secret,
                    discovery_url=discovery_url,
                    verbose=verbose,
                )
                if provider_type == 'oauth2'
                else _create_api_key_provider(
                    client=client,
                    name=name,
                    api_key=api_key,
                    verbose=verbose,
                )
            ),
            'get': lambda: _get(
                client=client,
                name=name,
                provider_type=provider_type,
                verbose=verbose,
            ),
            'list': lambda: _list(
                client=client,
                provider_type=provider_type,
                max_results=max_results,
                verbose=verbose,
            ),
            'delete': lambda: _delete(
                client=client,
                name=name,
                provider_type=provider_type,
                verbose=verbose,
            ),
        }

        # Validate required parameters
        if action in ['create', 'get', 'delete'] and not name:
            return {
                'status': 'error',
                'content': [{'text': f'name is required for {action} action'}],
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

        if verbose:
            print(f'AWS Error: {error_code} - {error_message}', flush=True)

        return {
            'status': 'error',
            'content': [
                {'text': f'**AWS Error ({error_code}):** {error_message}'},
                {'text': f'**Action:** {action}'},
                {'text': f'**Provider Type:** {provider_type}'},
                {'text': f'**Region:** {region}'},
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
