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

"""AgentCore Status Tool - Get agent runtime and endpoint status.

Retrieves status information for deployed Bedrock AgentCore agents.
"""

import json
from typing import Any, Dict


def get_agentcore_status(
    agent_id: str,
    endpoint_name: str = 'DEFAULT',
    include_agent_details: bool = True,
    include_endpoint_details: bool = True,
    region: str = 'us-west-2',
) -> Dict[str, Any]:
    """Get status and health information for deployed Bedrock AgentCore agents.

    This tool provides complete visibility into AgentCore agent runtime status, endpoint health,
    deployment configuration, and operational state. It queries both the agent runtime and endpoint
    APIs to deliver a health check for production monitoring, debugging, and
    deployment verification.

    How It Works:
    ------------
    1. **Client Initialization**: Creates bedrock-agentcore-control plane client for the region
    2. **Agent Runtime Query**: Calls GetAgentRuntime API to retrieve agent details
    3. **Endpoint Query**: Calls GetAgentRuntimeEndpoint API to check endpoint health
    4. **Data Extraction**: Parses agent configuration, container URIs, network settings
    5. **Status Interpretation**: Translates status codes into actionable information
    6. **Response Formatting**: Structures data for easy reading and monitoring
    7. **Error Handling**: Provides detailed error messages for troubleshooting

    Status Check Process:
    --------------------
    1. **Validation**: Ensures agent_id is provided
    2. **Runtime Details** (if enabled):
       - Agent runtime ID and ARN
       - Agent name and creation timestamp
       - IAM role ARN for permissions
       - Container URI from ECR
       - Network configuration (PUBLIC/VPC)
       - Last updated timestamp
    3. **Endpoint Details** (if enabled):
       - Endpoint ARN and name
       - Current status (READY, CREATING, FAILED)
       - Creation and update timestamps
       - Failure reason (if applicable)
    4. **Health Interpretation**:
       - READY: Agent accepting invocations
       - CREATING/UPDATING: Deployment in progress
       - FAILED: Deployment error with reason

    Agent Status Values:
    -------------------
    **Runtime Status:**
    - `READY` - Agent runtime created successfully
    - `CREATING` - Agent being provisioned
    - `UPDATING` - Agent configuration being updated
    - `DELETING` - Agent being removed
    - `CREATE_FAILED` - Runtime creation failed
    - `UPDATE_FAILED` - Update failed

    **Endpoint Status:**
    - `READY` - Endpoint ready for invocations
    - `CREATING` - Endpoint being provisioned
    - `UPDATING` - Endpoint configuration updating
    - `DELETING` - Endpoint being removed
    - `CREATE_FAILED` - Endpoint creation failed
    - `UPDATE_FAILED` - Endpoint update failed

    Common Use Cases:
    ---------------

    ### 1. Post-Deployment Verification
    ```python
    # After launch, verify agent is ready
    launch(agent_name='my-agent')

    # Wait a moment, then check status
    result = status(agent_id='my-agent-abc123')
    # Look for: status = "READY"
    ```

    ### 2. Health Monitoring
    ```python
    # Periodic health checks in production
    result = status(agent_id='prod-agent-xyz789')

    # Parse status
    if 'READY' in str(result):
        print('Agent healthy')
    else:
        print('Agent unhealthy - investigate')
    ```

    ### 3. Multi-Endpoint Monitoring
    ```python
    # Check default endpoint
    status(agent_id='my-agent-abc123', endpoint_name='DEFAULT')
    ```

    ### 4. Configuration Audit
    ```python
    # Get full agent configuration details
    result = status(agent_id='my-agent-abc123')

    # Review:
    # - Container URI (which image is deployed)
    # - IAM role (permissions)
    # - Network mode (PUBLIC vs VPC)
    # - Creation timestamp (when deployed)
    ```

    ### 5. Troubleshooting Failed Deployments
    ```python
    # Check why deployment failed
    result = status(agent_id='my-agent-abc123')

    # Look for:
    # - "failureReason" field
    # - Status = "CREATE_FAILED" or "UPDATE_FAILED"
    # - Error messages in response
    ```

    ### 6. Container URI Verification
    ```python
    # Verify correct container image is deployed
    result = status(agent_id='my-agent-abc123')
    ```

    ### 7. Cross-Region Status Check
    ```python
    # Check agent in different region
    status(agent_id='global-agent-abc123', region='eu-west-1')
    ```

    Status Interpretation Guide:
    ---------------------------
    **READY Status:**
    - Agent is fully operational
    - Endpoint accepting invocations
    - Safe to call invoke()
    - All systems nominal

    **⏳ CREATING/UPDATING Status:**
    - Deployment in progress
    - Wait 30-120 seconds typically
    - Poll status() until READY
    - Normal during deployment

    **CREATE_FAILED/UPDATE_FAILED Status:**
    - Deployment error occurred
    - Check "failureReason" field
    - Common issues:
      - IAM role permissions missing
      - Container image pull failed
      - Invalid configuration
      - Resource limits exceeded
    - Review CloudWatch logs for details

    Args:
        agent_id: Agent runtime ID (required)
            Format: {agent-name}-{random-suffix}
            Example: "my-agent-abc123", "strands_agentcore_tools-EXFG4UEqye"
            Get from: launch() output, agents() list, or .bedrock_agentcore.yaml
            Note: This is NOT the agent name, it's the runtime ID with suffix

        endpoint_name: Endpoint name to check (default: "DEFAULT")
            Default endpoint: "DEFAULT" (created automatically)
            Custom endpoints: Use custom endpoint names
            Multi-environment: "dev", "staging", "production"
            Qualifier: Must match endpoint created in launch
            Use case: Check specific environment endpoints

        include_agent_details: Include agent runtime details (default: True)
            True: Returns full agent configuration (container URI, IAM role, network)
            False: Skip agent details (faster response)
            Use False for: Quick endpoint health checks
            Use True for: Configuration audits, troubleshooting

        include_endpoint_details: Include endpoint details (default: True)
            True: Returns endpoint status, ARN, timestamps
            False: Skip endpoint details
            Use False for: Agent configuration review only
            Use True for: Health monitoring, deployment verification

        region: AWS region where agent is deployed (default: us-west-2)
            Must match agent deployment region
            Cross-region status checks not supported
            Multi-region: Call separately for each region
            Common regions: us-west-2, us-east-1, eu-west-1

    Returns:
        Dict containing status and response content in the format:
        {
            "status": "success|error",
            "content": [
                {"text": "**Agent Runtime Details:**"},
                {"text": "{JSON with agent info}"},
                {"text": "**Endpoint Details:**"},
                {"text": "{JSON with endpoint info}"},
                {"text": "**Agent is ready for invocation**"}
            ]
        }

        Success case: Returns comprehensive agent and endpoint information
        Error case: Returns error details with agent ID and region context

        **Agent Runtime Information:**
        - agentRuntimeId: Runtime identifier
        - agentRuntimeArn: Full ARN for invocation
        - agentRuntimeName: Friendly agent name
        - status: Runtime status (READY, CREATING, etc.)
        - roleArn: IAM execution role
        - containerUri: ECR container image URI
        - networkMode: Network configuration (PUBLIC/VPC)
        - createdAt: Initial deployment timestamp
        - lastUpdatedAt: Last update timestamp

        **Endpoint Information:**
        - agentRuntimeEndpointArn: Endpoint ARN
        - name: Endpoint name (DEFAULT or custom)
        - status: Endpoint status (READY, CREATING, etc.)
        - createdAt: Endpoint creation timestamp
        - lastUpdatedAt: Last endpoint update
        - failureReason: Error details (if status is FAILED)

    Notes:
        - **Prerequisites**: Agent must be deployed via launch tool first
        - **Agent ID Format**: Runtime ID with suffix, not just agent name
        - **Fast Checks**: Use include_agent_details=False for quick health checks
        - **Polling**: Poll status after launch until endpoint becomes READY
        - **Typical Time**: 30-120 seconds from CREATING to READY
        - **Idempotent**: Safe to call repeatedly for monitoring
        - **No Side Effects**: Read-only operation, doesn't modify agent
        - **Permissions**: Requires `bedrock-agentcore:GetAgentRuntime`, `bedrock-agentcore:GetAgentRuntimeEndpoint`
        - **Rate Limits**: AWS API rate limits apply (typically high enough for monitoring)
        - **Cost**: No direct cost - uses AWS SDK API calls
        - **Best Practice**: Check status before invoke() to ensure READY state
        - **Debugging**: Combine with logs() for comprehensive troubleshooting
        - **Multi-Endpoint**: Each endpoint has independent status
        - **Failure Reasons**: Always check failureReason field when status is FAILED
        - **Container Updates**: Status shows which container image is currently deployed
        - **IAM Audit**: Use status to verify execution role ARN
        - **Network Config**: Verify PUBLIC vs VPC network mode
        - **Timestamps**: Use createdAt/lastUpdatedAt for deployment tracking
        - **Integration**: Essential tool in deployment pipelines for verification
        - **Monitoring**: Ideal for health check dashboards and alerts
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        return {
            'status': 'error',
            'content': [{'text': 'boto3 required. Install: pip install boto3'}],
        }

    try:
        # Initialize control plane client
        client = boto3.client('bedrock-agentcore-control', region_name=region)

        results = []

        # Get agent runtime details
        if include_agent_details:
            try:
                agent_response = client.get_agent_runtime(agentRuntimeId=agent_id)

                agent_info = {
                    'agentRuntimeId': agent_response.get('agentRuntimeId'),
                    'agentRuntimeArn': agent_response.get('agentRuntimeArn'),
                    'agentRuntimeName': agent_response.get('agentRuntimeName'),
                    'status': agent_response.get('status'),
                    'roleArn': agent_response.get('roleArn'),
                    'createdAt': str(agent_response.get('createdAt')),
                    'lastUpdatedAt': str(agent_response.get('lastUpdatedAt')),
                }

                # Add container info if available
                if 'agentRuntimeArtifact' in agent_response:
                    container_config = agent_response['agentRuntimeArtifact'].get(
                        'containerConfiguration', {}
                    )
                    if container_config:
                        agent_info['containerUri'] = container_config.get('containerUri')

                # Add network config if available
                if 'networkConfiguration' in agent_response:
                    agent_info['networkMode'] = agent_response['networkConfiguration'].get(
                        'networkMode'
                    )

                results.append({'text': '**Agent Runtime Details:**'})
                results.append({'text': json.dumps(agent_info, indent=2)})

            except ClientError as e:
                results.append(
                    {
                        'text': f'**Agent Error:** {e.response.get("Error", {}).get("Message", str(e))}'
                    }
                )

        # Get endpoint details
        if include_endpoint_details:
            try:
                endpoint_response = client.get_agent_runtime_endpoint(
                    agentRuntimeId=agent_id, endpointName=endpoint_name
                )

                endpoint_info = {
                    'agentRuntimeEndpointArn': endpoint_response.get('agentRuntimeEndpointArn'),
                    'name': endpoint_response.get('name'),
                    'status': endpoint_response.get('status'),
                    'createdAt': str(endpoint_response.get('createdAt')),
                    'lastUpdatedAt': str(endpoint_response.get('lastUpdatedAt')),
                }

                # Add failure reason if present
                if 'failureReason' in endpoint_response:
                    endpoint_info['failureReason'] = endpoint_response['failureReason']

                results.append({'text': '\n**Endpoint Details:**'})
                results.append({'text': json.dumps(endpoint_info, indent=2)})

                # Add status interpretation
                status = endpoint_info['status']
                if status == 'READY':
                    results.append({'text': '\n**Agent is ready for invocation**'})
                elif status in ['CREATING', 'UPDATING']:
                    results.append({'text': f'\n**Agent is {status.lower()}...**'})
                elif status in ['CREATE_FAILED', 'UPDATE_FAILED']:
                    results.append({'text': f'\n**Agent {status.lower().replace("_", " ")}**'})

            except ClientError as e:
                results.append(
                    {
                        'text': f'**Endpoint Error:** {e.response.get("Error", {}).get("Message", str(e))}'
                    }
                )

        return {'status': 'success', 'content': results}

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        return {
            'status': 'error',
            'content': [
                {'text': f'**AWS Error ({error_code}):** {error_message}'},
                {'text': f'**Agent ID:** {agent_id}'},
                {'text': f'**Region:** {region}'},
            ],
        }

    except Exception as e:
        return {
            'status': 'error',
            'content': [
                {'text': f'**Unexpected Error:** {str(e)}'},
                {'text': f'**Agent ID:** {agent_id}'},
            ],
        }
