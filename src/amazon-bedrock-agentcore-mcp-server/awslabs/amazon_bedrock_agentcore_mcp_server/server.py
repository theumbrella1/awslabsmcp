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

"""awslabs AWS Bedrock AgentCore MCP Server implementation."""

from .tools import agents, identity, logs, memory, session
from bedrock_agentcore_starter_toolkit.operations.runtime import configure, launch, invoke, status, destroy
from .utils import cache, text_processor
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional, Literal
from pathlib import Path


APP_NAME = 'amazon-bedrock-agentcore-mcp-server'
mcp = FastMCP(APP_NAME)

mcp.tool()(agents.manage_agentcore_agents)
mcp.tool()(session.manage_agentcore_session)
mcp.tool()(logs.access_agentcore_logs)
mcp.tool()(memory.manage_agentcore_memory)
mcp.tool()(identity.manage_agentcore_identity)
@mcp.tool(
    name="launch_agentcore_agent",
    description="""
    Launch Bedrock AgentCore agent - deploys your agent either locally for testing or to AWS cloud for production.
    
    The function is idempotent - it reuses existing AWS resources (ECR repos, IAM roles, memory)
    and updates the agent if it already exists (when auto_update_on_conflict=True).

    Args:
        config_path: Path to BedrockAgentCore configuration file (.bedrock_agentcore.yaml)
        agent_name: Name of agent to launch (required for multi-agent projects)
        local: Whether to run locally
        use_codebuild: Whether to use CodeBuild for ARM64 builds
        env_vars: Environment variables to pass to container (dict of key-value pairs)
        auto_update_on_conflict: Whether to automatically update when agent already exists (default: False)

    Returns:
        LaunchResult model with launch details including:
        - agent_arn: ARN of deployed agent
        - agent_id: ID of deployed agent
        - ecr_uri: ECR repository URI 
        - tag: Docker image tag
        - port: Local port (local mode)

    Raises:
        ValueError: If configuration is invalid, region not configured, or VPC resources validation fails
        RuntimeError: If Dockerfile not found, container runtime unavailable, or build fails
        RuntimeToolkitException: If launch fails after creating AWS resources
        ClientError: If AWS API calls fail (role validation, ECR, CodeBuild, AgentCore deployment)
        FileNotFoundError: If configuration file doesn't exist
    """
)
def launch_agentcore_agent_wrapper(
    config_path: Path,
    agent_name: Optional[str] = None,
    local: bool = False,
    use_codebuild: bool = True,
    env_vars: Optional[Dict[str, str]] = None,
    auto_update_on_conflict: bool = False,
):
    """Wrapper for launch_bedrock_agentcore"""
    result = launch.launch_bedrock_agentcore(
        config_path=config_path,
        agent_name=agent_name,
        local=local,
        use_codebuild=use_codebuild,
        env_vars=env_vars,
        auto_update_on_conflict=auto_update_on_conflict,
    )
    return result.model_dump(mode='json')
mcp.tool(
    name="invoke_agentcore_agent",
    description="""
    Invoke deployed Bedrock AgentCore endpoint with streaming support.
    
    Sends JSON payload to agent endpoint (cloud or local), handles session management with auto-generated
    session IDs, supports authentication (bearer token, user ID), and returns agent response with session context.

    Args:
        config_path: Path to BedrockAgentCore configuration file
        payload: JSON payload to send to agent (dict or JSON string)
        agent_name: Name of agent to invoke (for project configurations)
        session_id: Runtime session ID for conversation continuity (auto-generated if not provided)
        bearer_token: Optional bearer token for authentication
        user_id: Optional user ID for authorization flows
        local_mode: Whether to invoke local container (default: False, uses cloud endpoint)
        custom_headers: Optional custom headers as dict

    Returns:
        InvokeResult model with invocation details including:
        - response: Response from Bedrock AgentCore endpoint
        - session_id: Session ID used for invocation
        - agent_arn: BedrockAgentCore agent ARN

    Raises:
        ValueError: If agent not deployed or region not configured
        FileNotFoundError: If configuration file doesn't exist
    """
)(invoke.invoke_bedrock_agentcore)
mcp.tool(
    name="get_agentcore_agent_status",
    description="""
    Get Bedrock AgentCore agent status and runtime details.

    Args:
        config_path: Path to BedrockAgentCore configuration file
        agent_name: Name of agent to get status for (for project configurations)

    Returns:
        StatusResult model with status details including:
        - config: Configuration information (name, entrypoint, region, account, execution_role, ecr_repository, agent_id, agent_arn, network settings, memory settings)
        - agent: Agent runtime details or error
        - endpoint: Endpoint details or error

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If Bedrock AgentCore is not deployed or configuration is invalid
    """
)(status.get_status)
mcp.tool(
    name="destry_agentcore_agent",
    description="""
    Destroy Bedrock AgentCore resources from AWS.
    
    Removes AgentCore endpoint, agent runtime, ECR images/repository, CodeBuild project, memory resources,
    and IAM roles (execution and CodeBuild). Updates configuration file and handles multi-agent cleanup.

    Args:
        config_path: Path to the configuration file
        agent_name: Name of the agent to destroy (default: use default agent)
        dry_run: If True, only show what would be destroyed without actually doing it
        force: If True, skip confirmation prompts
        delete_ecr_repo: If True, also delete the ECR repository after removing images

    Returns:
        DestroyResult model with destruction details including:
        - agent_name: Name of the destroyed agent
        - resources_removed: List of removed AWS resources
        - warnings: List of warnings during destruction
        - errors: List of errors during destruction
        - dry_run: Whether this was a dry run

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If agent is not found or not deployed
        RuntimeError: If destruction fails
    """
)(destroy.destroy_bedrock_agentcore)

@mcp.tool(name="configure_agentcore_agent")
def configure_agentcore_agent_wrapper(
    agent_name: str,
    entrypoint_path: Path,
    current_working_directory: str,
    execution_role: Optional[str] = None,
    code_build_execution_role: Optional[str] = None,
    ecr_repository: Optional[str] = None,
    container_runtime: Optional[str] = None,
    auto_create_ecr: bool = True,
    auto_create_execution_role: bool = True,
    enable_observability: bool = True,
    memory_mode: Literal["NO_MEMORY", "STM_ONLY", "STM_AND_LTM"] = "STM_ONLY",
    requirements_file: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    request_header_configuration: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    region: Optional[str] = None,
    protocol: Optional[str] = None,
    source_path: Optional[str] = None,
):
    """Configure Bedrock AgentCore application with deployment settings.
    
    Creates .bedrock_agentcore.yaml configuration file and generates Dockerfile with .dockerignore.
    Handles agent naming, dependency detection, AWS resource setup (IAM roles, ECR), and memory configuration
    (STM/LTM).
    
    IMPORTANT: Only add the necessary arguments and the arguments when requested by a user.
    
    Args:
        agent_name: name of the agent (Use underscores, letter, numbers)
        entrypoint_path: Path to the entrypoint file
        current_working_directory: absolute path to the working directory
        execution_role: AWS execution role ARN or name (auto-created if not provided)
        code_build_execution_role: CodeBuild execution role ARN or name (uses execution_role if not provided)
        ecr_repository: ECR repository URI
        container_runtime: Container runtime to use for local builds - "auto" (default, auto-detects Docker/Finch/Podman), "docker", "finch", "podman", or "none" (CodeBuild only)
        auto_create_ecr: Whether to auto-create ECR repository
        auto_create_execution_role: Whether to auto-create execution role if not provided
        enable_observability: Whether to enable observability
        memory_mode: Memory configuration mode - "NO_MEMORY", "STM_ONLY" (default), or "STM_AND_LTM"
        requirements_file: Path to requirements file
        authorizer_configuration: JWT authorizer configuration dictionary
        request_header_configuration: Request header configuration dictionary
        verbose: Whether to provide verbose output during configuration
        region: AWS region for deployment
        protocol: agent server protocol, must be either HTTP or MCP or A2A
        source_path: Optional path to agent source code directory

    Returns:
        ConfigureResult model with configuration details including:
        - config_path: Path to configuration file
        - dockerfile_path: Path to generated Dockerfile
        - dockerignore_path: Path to generated .dockerignore
        - runtime: Container runtime name
        - region: AWS region
        - account_id: AWS account ID
        - execution_role: AWS execution role ARN
        - ecr_repository: ECR repository URI
        - auto_create_ecr: Whether ECR will be auto-created
        - memory_id: Memory resource ID if created
        - network_mode: Network mode (PUBLIC or VPC)
        - network_subnets: VPC subnet IDs
        - network_security_groups: VPC security group IDs
        - network_vpc_id: VPC ID
    """
    import os
    
    # Save the original working directory
    original_cwd = os.getcwd()
    
    try:
        # Change to the specified working directory if provided
        if current_working_directory:
            os.chdir(current_working_directory)
        
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
            verbose=verbose,
            region=region,
            protocol=protocol,
            non_interactive=True, # This tool will never use the interactive path
            source_path=source_path,
        )
        # converts the result from ConfigureResult to Dict (json serializable)
        return result.model_dump(mode='json')
    finally:
        # Restore the original working directory
        os.chdir(original_cwd)


@mcp.tool()
def search_agentcore_docs(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Search curated AgentCore documentation and return ranked results with snippets.

    This tool provides access to the complete Amazon Bedrock AgentCore documentation including:

    **Platform Overview:**
    - What is Bedrock AgentCore, security overview, quotas and limits

    **Platform Services:**
    - AgentCore Runtime (serverless deployment and scaling)
    - AgentCore Memory (persistent knowledge with event and semantic memory)
    - AgentCore Code Interpreter (secure code execution in isolated sandboxes)
    - AgentCore Browser (fast, secure cloud-based browser for web interaction)
    - AgentCore Gateway (transform existing APIs into agent tools)
    - AgentCore Observability (real-time monitoring and tracing)
    - AgentCore Identity (secure authentication and access management)

    **Getting Started:**
    - Prerequisites & environment setup
    - Building your first agent or transforming existing code
    - Local development & testing
    - Deployment to AgentCore using CLI
    - Troubleshooting & enhancement

    **Examples & Tutorials:**
    - Basic agent creation, memory integration, tool usage
    - Streaming responses, error handling, authentication
    - Customer service agents, code review assistants, data analysis
    - Multi-agent workflows and integrations

    **API Reference:**
    - Data plane and control API documentation

    Use this to find relevant AgentCore documentation for any development question.

    Args:
        query: Search query string (e.g., "bedrock agentcore", "memory integration", "deployment guide")
        k: Maximum number of results to return (default: 5)

    Returns:
        List of dictionaries containing:
        - url: Document URL
        - title: Display title
        - score: Relevance score (0-1, higher is better)
        - snippet: Contextual content preview

    """
    cache.ensure_ready()
    index = cache.get_index()
    results = index.search(query, k=k) if index else []
    url_cache = cache.get_url_cache()

    # Fetch content for all results to enable content-aware ranking
    for _, doc in results:
        cache.ensure_page(doc.uri)

    # Re-rank with content now available
    if index:
        results = index.search(query, k=k)

    # Build response with real content snippets when available
    return_docs: List[Dict[str, Any]] = []
    for score, doc in results:
        page = url_cache.get(doc.uri)
        snippet = text_processor.make_snippet(page, doc.display_title)
        return_docs.append(
            {
                'url': doc.uri,
                'title': doc.display_title,
                'score': round(score, 3),
                'snippet': snippet,
            }
        )
    return return_docs


@mcp.tool()
def fetch_agentcore_doc(uri: str) -> Dict[str, Any]:
    """Fetch full document content by URL.

    Retrieves complete AgentCore documentation content from URLs found via search_agentcore_docs
    or provided directly. Use this to get full documentation pages including:

    - Complete platform overview and service documentation
    - Detailed getting started guides with step-by-step instructions
    - Full API reference documentation
    - Comprehensive tutorial and example code
    - Complete deployment and configuration instructions
    - Integration guides for various frameworks (Strands, LangGraph, CrewAI, etc.)

    This provides the full content when search snippets aren't sufficient for
    understanding or implementing AgentCore features.

    Args:
        uri: Document URI (supports http/https URLs)

    Returns:
        Dictionary containing:
        - url: Canonical document URL
        - title: Document title
        - content: Full document text content
        - error: Error message (if fetch failed)

    """
    cache.ensure_ready()

    page = cache.ensure_page(uri)
    if page is None:
        return {'error': 'fetch failed', 'url': uri}

    return {
        'url': page.url,
        'title': page.title,
        'content': page.content,
    }


def main() -> None:
    """Main entry point for the MCP server.

    Initializes the document cache and starts the FastMCP server.
    The cache is loaded with document titles only for fast startup,
    with full content fetched on-demand.
    """
    cache.ensure_ready()
    mcp.run()


if __name__ == '__main__':
    main()
