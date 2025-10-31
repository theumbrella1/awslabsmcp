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

"""AgentCore Runtime Tool - Manage agent runtime lifecycle and operations.

Comprehensive runtime operations including configure, launch, invoke, status, and destroy.
"""

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Literal, Optional

from bedrock_agentcore_starter_toolkit.operations.runtime import (
    configure,
    destroy,
    invoke,
    launch,
    status,
)


def _format_success_response(title: str, result: Any) -> Dict[str, Any]:
    """Format a successful operation response."""
    return {
        'status': 'success',
        'content': [
            {'text': title},
            result.model_dump(mode='json'),
        ],
    }


def _configure(
    agent_name: str,
    entrypoint_path: Path,
    execution_role: Optional[str],
    code_build_execution_role: Optional[str],
    ecr_repository: Optional[str],
    container_runtime: Optional[str],
    auto_create_ecr: bool,
    auto_create_execution_role: bool,
    enable_observability: bool,
    memory_mode: str,
    requirements_file: Optional[str],
    authorizer_configuration: Optional[Dict[str, Any]],
    request_header_configuration: Optional[Dict[str, Any]],
    region: Optional[str],
    protocol: Optional[str],
    source_path: Optional[str],
) -> Dict[str, Any]:
    """Configure agent with deployment settings."""
    if not all([agent_name, entrypoint_path]):
        return {
            'status': 'error',
            'content': [
                {
                    'text': 'agent_name and entrypoint_path'
                    'required for configure'
                }
            ],
        }

    result = configure.configure_bedrock_agentcore(
        agent_name=agent_name,
        entrypoint_path=entrypoint_path,
        execution_role=execution_role,
        code_build_execution_role=code_build_execution_role,
        ecr_repository=ecr_repository,
        container_runtime=container_runtime,
        auto_create_ecr=auto_create_ecr,
        auto_create_execution_role=auto_create_execution_role,
        enable_observability=enable_observability,
        memory_mode=memory_mode,
        requirements_file=requirements_file,
        authorizer_configuration=authorizer_configuration,
        request_header_configuration=request_header_configuration,
        region=region,
        protocol=protocol,
        non_interactive=True,
        source_path=source_path,
    )

    return _format_success_response('**Agent Configured Successfully**', result)


def _launch(
    config_path: Path,
    agent_name: Optional[str],
    local: bool,
    use_codebuild: bool,
    env_vars: Optional[Dict[str, str]],
    auto_update_on_conflict: bool,
) -> Dict[str, Any]:
    """Deploy agent locally or to AWS."""
    if not config_path:
        return {
            'status': 'error',
            'content': [{'text': 'config_path required for launch'}],
        }

    result = launch.launch_bedrock_agentcore(
        config_path=config_path,
        agent_name=agent_name,
        local=local,
        use_codebuild=use_codebuild,
        env_vars=env_vars,
        auto_update_on_conflict=auto_update_on_conflict,
    )

    return _format_success_response('**Agent Launched Successfully**', result)


def _invoke(
    config_path: Path,
    payload: Any,
    agent_name: Optional[str],
    session_id: Optional[str],
    bearer_token: Optional[str],
    user_id: Optional[str],
    local_mode: Optional[bool],
    custom_headers: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Invoke deployed agent endpoint."""
    if not config_path or payload is None:
        return {
            'status': 'error',
            'content': [{'text': 'config_path and payload required for invoke'}],
        }

    result = invoke.invoke_bedrock_agentcore(
        config_path=config_path,
        payload=payload,
        agent_name=agent_name,
        session_id=session_id,
        bearer_token=bearer_token,
        user_id=user_id,
        local_mode=local_mode,
        custom_headers=custom_headers,
    )

    return _format_success_response('**Agent Invoked Successfully**', result)


def _get_status(
    config_path: Path,
    agent_name: Optional[str],
) -> Dict[str, Any]:
    """Get agent status and runtime details."""
    if not config_path:
        return {
            'status': 'error',
            'content': [{'text': 'config_path required for get_status'}],
        }

    result = status.get_status(config_path=config_path, agent_name=agent_name)

    return _format_success_response('**Agent Status:**', result)


def _destroy(
    config_path: Path,
    agent_name: Optional[str],
    dry_run: bool,
    force: bool,
    delete_ecr_repo: bool,
) -> Dict[str, Any]:
    """Destroy agent and AWS resources."""
    if not config_path:
        return {
            'status': 'error',
            'content': [{'text': 'config_path required for destroy'}],
        }

    result = destroy.destroy_bedrock_agentcore(
        config_path=config_path,
        agent_name=agent_name,
        dry_run=dry_run,
        force=force,
        delete_ecr_repo=delete_ecr_repo,
    )

    return _format_success_response('**Agent Destroy Operation:**', result)


def _list(
    region: Optional[str],
    max_results: int,
) -> Dict[str, Any]:
    """List all agent runtimes in the region."""
    try:
        import boto3
    except ImportError:
        return {
            'status': 'error',
            'content': [{'text': 'boto3 required. Install: pip install boto3'}],
        }

    client = boto3.client('bedrock-agentcore-control', region_name=region or 'us-west-2')

    all_agents: list[Dict[str, Any]] = []
    next_token = None

    # Handle pagination
    while True:
        params = {'maxResults': min(max_results - len(all_agents), 100)}
        if next_token:
            params['nextToken'] = next_token

        response = client.list_agent_runtimes(**params)
        agents = response.get('agentRuntimes', [])
        all_agents.extend(agents)

        # Check if we've reached max_results or no more pages
        if len(all_agents) >= max_results:
            all_agents = all_agents[:max_results]
            break

        next_token = response.get('nextToken')
        if not next_token:
            break

    return {
        'status': 'success',
        'content': [
            {'text': f'**Found {len(all_agents)} agent runtimes:**'},
            {'text': json.dumps(all_agents, indent=2, default=str)},
        ],
    }


def manage_agentcore_runtime(
    action: str,
    current_working_directory: str,
    config_path: Optional[Path] = None,
    agent_name: Optional[str] = None,
    entrypoint_path: Optional[Path] = None,
    execution_role: Optional[str] = None,
    code_build_execution_role: Optional[str] = None,
    ecr_repository: Optional[str] = None,
    container_runtime: Optional[str] = None,
    auto_create_ecr: bool = True,
    auto_create_execution_role: bool = True,
    enable_observability: bool = True,
    memory_mode: Literal['NO_MEMORY', 'STM_ONLY', 'STM_AND_LTM'] = 'STM_ONLY',
    requirements_file: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    request_header_configuration: Optional[Dict[str, Any]] = None,
    region: Optional[str] = None,
    protocol: Optional[str] = None,
    source_path: Optional[str] = None,
    local: bool = False,
    use_codebuild: bool = True,
    env_vars: Optional[Dict[str, str]] = None,
    auto_update_on_conflict: bool = False,
    payload: Optional[Any] = None,
    session_id: Optional[str] = None,
    bearer_token: Optional[str] = None,
    user_id: Optional[str] = None,
    local_mode: Optional[bool] = False,
    custom_headers: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
    force: bool = False,
    delete_ecr_repo: bool = False,
    max_results: int = 100,
) -> Dict[str, Any]:
    """Manage Bedrock AgentCore agent runtime lifecycle and operations.

    Args:
        action: Runtime operation to perform:
            - "configure": Configure agent with deployment settings
            - "launch": Deploy agent locally or to AWS
            - "invoke": Invoke deployed agent endpoint
            - "get_status": Get agent status and runtime details
            - "destroy": Destroy agent and AWS resources
            - "list": List all agent runtimes in the region

        config_path: Path to BedrockAgentCore configuration file (.bedrock_agentcore.yaml)
        agent_name: Name of agent use letters, underscores, numbers, NO HYPHENS (required for configure, or multi-agent projects)
        entrypoint_path: Path to entrypoint file (required for configure and launch)
        current_working_directory: Absolute path to working directory (required)
        execution_role: AWS execution role ARN or name
        code_build_execution_role: CodeBuild execution role ARN or name
        ecr_repository: ECR repository URI
        container_runtime: Container runtime (auto/docker/finch/podman/none)
        auto_create_ecr: Whether to auto-create ECR repository
        auto_create_execution_role: Whether to auto-create execution role
        enable_observability: Whether to enable observability
        memory_mode: Memory configuration (NO_MEMORY/STM_ONLY/STM_AND_LTM)
        requirements_file: Path to requirements file
        authorizer_configuration: JWT authorizer configuration
        request_header_configuration: Request header configuration
        region: AWS region (default: us-west-2)
        protocol: Agent server protocol (HTTP/MCP/A2A)
        source_path: Path to agent source code directory
        local: Whether to run locally (for launch)
        use_codebuild: Whether to use CodeBuild for ARM64 builds
        env_vars: Environment variables for container
        auto_update_on_conflict: Auto-update when agent exists
        payload: JSON payload to send to agent (for invoke)
        session_id: Runtime session ID for conversation continuity
        bearer_token: Bearer token for authentication
        user_id: User ID for authorization
        local_mode: Whether to invoke local container
        custom_headers: Custom headers for invoke
        dry_run: Show what would be destroyed without doing it
        force: Skip confirmation prompts
        delete_ecr_repo: Delete ECR repository after removing images
        max_results: Maximum results for list operation (default: 100)

    Returns:
        Dict with status and operation results

    Examples:
        # Configure agent
        runtime(
            action="configure",
            agent_name="my_agent",
            entrypoint_path="agent.py",
            current_working_directory="/path/to/project"
        )

        # Launch agent to AWS
        runtime(
            action="launch",
            config_path=".bedrock_agentcore.yaml",
            current_working_directory="/path/to/project"
        )

        # Invoke agent
        runtime(
            action="invoke",
            config_path=".bedrock_agentcore.yaml",
            payload={"input": "Hello"},
            current_working_directory="/path/to/project"
        )

        # Get agent status
        runtime(
            action="get_status",
            config_path=".bedrock_agentcore.yaml",
            current_working_directory="/path/to/project"
        )

        # Destroy agent
        runtime(
            action="destroy",
            config_path=".bedrock_agentcore.yaml",
            force=True,
            current_working_directory="/path/to/project"
        )

        # List all agents
        runtime(
            action="list",
            region="us-west-2",
            current_working_directory="/path/to/project"
        )
    """
    # Change to working directory if provided
    original_cwd = os.getcwd()
    if current_working_directory:
        os.chdir(current_working_directory)

    # Action dispatch registry
    action_handlers: Dict[str, Callable[..., Dict[str, Any]]] = {
        'configure': lambda: _configure(
            agent_name=agent_name,
            entrypoint_path=entrypoint_path,
            execution_role=execution_role,
            code_build_execution_role=code_build_execution_role,
            ecr_repository=ecr_repository,
            container_runtime=container_runtime,
            auto_create_ecr=auto_create_ecr,
            auto_create_execution_role=auto_create_execution_role,
            enable_observability=enable_observability,
            memory_mode=memory_mode,
            requirements_file=requirements_file,
            authorizer_configuration=authorizer_configuration,
            request_header_configuration=request_header_configuration,
            region=region,
            protocol=protocol,
            source_path=source_path,
        ),
        'launch': lambda: _launch(
            config_path=config_path,
            agent_name=agent_name,
            local=local,
            use_codebuild=use_codebuild,
            env_vars=env_vars,
            auto_update_on_conflict=auto_update_on_conflict,
        ),
        'invoke': lambda: _invoke(
            config_path=config_path,
            payload=payload,
            agent_name=agent_name,
            session_id=session_id,
            bearer_token=bearer_token,
            user_id=user_id,
            local_mode=local_mode,
            custom_headers=custom_headers,
        ),
        'get_status': lambda: _get_status(
            config_path=config_path,
            agent_name=agent_name,
        ),
        'destroy': lambda: _destroy(
            config_path=config_path,
            agent_name=agent_name,
            dry_run=dry_run,
            force=force,
            delete_ecr_repo=delete_ecr_repo,
        ),
        'list': lambda: _list(
            region=region,
            max_results=max_results,
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

    try:
        result = handler()
        return result

    except Exception as e:
        # Try to provide detailed AWS error if it's a ClientError
        try:
            from botocore.exceptions import ClientError

            if isinstance(e, ClientError):
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                return {
                    'status': 'error',
                    'content': [
                        {'text': f'**AWS Error ({error_code}):** {error_message}'},
                        {'text': f'**Action:** {action}'},
                        {'text': f'**Region:** {region or "us-west-2"}'},
                    ],
                }
        except ImportError:
            # botocore not available, fall through to generic error
            pass

        # Generic error response
        return {
            'status': 'error',
            'content': [
                {'text': f'**Error:** {str(e)}'},
                {'text': f'**Action:** {action}'},
            ],
        }

    finally:
        # Restore original working directory
        if current_working_directory:
            os.chdir(original_cwd)
