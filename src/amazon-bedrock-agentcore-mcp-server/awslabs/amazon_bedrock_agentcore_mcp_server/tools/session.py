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

"""AgentCore Session Tool - Manage runtime sessions.

Stop active runtime sessions to free up resources.
"""

from typing import Any, Dict


def manage_agentcore_session(
    action: str,
    agent_arn: str,
    session_id: str,
    qualifier: str = 'DEFAULT',
    region: str = 'us-west-2',
) -> Dict[str, Any]:
    """Manage active Bedrock AgentCore runtime sessions with graceful termination and resource cleanup.

    This tool provides comprehensive session lifecycle management for AgentCore agents, enabling
    you to stop active runtime sessions to free resources, handle cleanup during maintenance,
    and manage session lifecycles in production environments. It gracefully handles session
    termination with proper error handling and status reporting.

    How It Works:
    ------------
    1. **Client Initialization**: Creates bedrock-agentcore data plane client with retry configuration
    2. **Action Routing**: Directs request to appropriate session management method
    3. **Session Termination**: Calls StopRuntimeSession API to gracefully stop the session
    4. **Resource Cleanup**: AgentCore automatically frees compute and memory resources
    5. **Status Verification**: Captures HTTP status code and response details
    6. **Error Handling**: Handles session not found gracefully (may already be stopped)
    7. **Response Formatting**: Returns confirmation with session and agent details

    Session Management Process:
    --------------------------
    1. **Validation**: Ensures agent_arn and session_id are provided
    2. **Client Setup**: Configures boto3 with timeouts and retry logic
    3. **API Call**: Executes StopRuntimeSession on bedrock-agentcore data plane
    4. **Response Processing**: Parses status code and confirmation
    5. **Error Handling**: Gracefully handles "already stopped" scenarios
    6. **Result Return**: Provides clear success/error status with context

    Session Lifecycle:
    -----------------
    **Active Session States:**
    ```
    Created → Active → Processing → Idle → Stopped/Expired
    ```

    **Session Creation:**
    - Automatically created on first invoke() call
    - Session ID returned in invoke() response
    - Tracked in .bedrock_agentcore.yaml (agent_session_id)

    **Session Termination:**
    - Manual: Via session(action="stop", ...)
    - Automatic: After idle_timeout expires (if configured)
    - Automatic: After max_lifetime reached (if configured)
    - On disconnect: When client closes connection

    **Resource Impact:**
    - Active sessions consume compute resources
    - Stopping sessions immediately frees resources
    - Stopped sessions cannot be resumed (create new session)
    - Memory persists (if STM/LTM enabled)

    Session Best Practices:
    ----------------------
    **1. Resource Management:**
    - Stop sessions after testing to free resources
    - Don't keep idle sessions active
    - Use idle_timeout in configure for automatic cleanup

    **2. Cost Optimization:**
    - Active sessions consume compute resources
    - Stop long-running idle sessions
    - Configure max_lifetime for automatic termination

    **3. Memory Preservation:**
    - Stopping session doesn't delete memory
    - STM/LTM data persists across sessions
    - New sessions can access historical memory

    **4. Error Handling:**
    - Always handle "session not found" gracefully
    - Session may have already expired
    - Don't fail application if session stop fails

    **5. Session Tracking:**
    - Track active session IDs in application state
    - Use .bedrock_agentcore.yaml for persistence
    - Log session creation/termination events

    Args:
        action: Session operation to perform:
            - "stop": Stop an active runtime session
            Currently only "stop" action is supported
            Future actions: "list", "get", "pause", "resume"

        agent_arn: Agent ARN (required)
            Format: arn:aws:bedrock-agentcore:region:account:runtime/agent-name-id
            Example: "arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-agent-abc123"
            Get from: launch() output, status() response, or .bedrock_agentcore.yaml
            Full ARN required (not just agent ID)

        session_id: Runtime session ID to manage (required)
            Format: UUID string (e.g., "abc-123-def-456")
            Obtained from: invoke() calls, logs, or .bedrock_agentcore.yaml
            Must be an active session for the specified agent
            Cannot reuse stopped session IDs

        qualifier: Endpoint qualifier (default: "DEFAULT")
            Default endpoint: "DEFAULT"
            Custom endpoints: Use custom endpoint name
            Must match endpoint used in invoke()
            Multi-environment: "dev", "staging", "production"

        region: AWS region where agent is deployed (default: us-west-2)
            Must match agent deployment region
            Cross-region session management not supported
            Common regions: us-west-2, us-east-1, eu-west-1

    Returns:
        Dict containing status and response content in the format:
        {
            "status": "success|error",
            "content": [
                {"text": "**Session Stopped Successfully**"},
                {"text": "**Session ID:** abc-123-def-456"},
                {"text": "**Agent ARN:** arn:aws:..."},
                {"text": "**Status Code:** 200"}
            ]
        }

        Success case: Returns confirmation with session details and HTTP status
        Error case: Returns AWS error details with session and agent context
        Not found: Returns warning (session may have already terminated)

    Notes:
        - **Prerequisites**: Agent must be deployed and session must be active
        - **Resource Cleanup**: Stopping session immediately frees compute resources
        - **Memory Persistence**: STM/LTM data persists after session stop
        - **Session Reuse**: Cannot reuse stopped session IDs (create new)
        - **Graceful Handling**: Tool handles "already stopped" scenarios without error
        - **No Resume**: Stopped sessions cannot be resumed (start new session)
        - **Permissions**: Requires `bedrock-agentcore:StopRuntimeSession` permission
        - **Rate Limits**: AWS API rate limits apply (typically sufficient)
        - **Cost**: No direct cost - uses AWS SDK API calls
        - **Best Practice**: Always stop test sessions after use
        - **Timeout Config**: Uses 60s read timeout, 30s connect timeout, 3 retries
        - **HTTP Status**: 200 = success, 404 = not found, 403 = no permission
        - **Idempotent**: Safe to call multiple times (already stopped returns success)
        - **No Side Effects**: Only stops specified session, doesn't affect other sessions
        - **Memory Safe**: Stopping session doesn't delete memory data
        - **Automatic Cleanup**: idle_timeout and max_lifetime auto-stop sessions
        - **Session Tracking**: track session IDs in .bedrock_agentcore.yaml
        - **Multi-Environment**: Each endpoint has independent sessions
        - **Debugging**: Check CloudWatch logs before stopping for troubleshooting
        - **Integration**: Works with launch, invoke, status, and logs tools
    """
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
    except ImportError:
        return {
            'status': 'error',
            'content': [{'text': 'boto3 required. Install: pip install boto3'}],
        }

    try:
        if action == 'stop':
            # Configure boto3 client with retry logic
            config = Config(
                retries={'max_attempts': 3, 'mode': 'standard'},
                read_timeout=60,
                connect_timeout=30,
            )

            # Create data plane client
            client = boto3.client('bedrock-agentcore', region_name=region, config=config)

            # Stop the runtime session
            response = client.stop_runtime_session(
                agentRuntimeArn=agent_arn,
                runtimeSessionId=session_id,
                qualifier=qualifier,
            )

            # Get HTTP status code
            status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'N/A')

            return {
                'status': 'success',
                'content': [
                    {'text': '**Session Stopped Successfully**'},
                    {'text': f'**Session ID:** {session_id}'},
                    {'text': f'**Agent ARN:** {agent_arn}'},
                    {'text': f'**Status Code:** {status_code}'},
                ],
            }

        else:
            return {
                'status': 'error',
                'content': [{'text': f'Unknown action: {action}. Valid actions: stop'}],
            }

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))

        # Handle session not found gracefully
        if error_code in ['ResourceNotFoundException', 'NotFound']:
            return {
                'status': 'success',
                'content': [
                    {'text': '**Session Not Found** (may have already been terminated)'},
                    {'text': f'**Session ID:** {session_id}'},
                ],
            }

        return {
            'status': 'error',
            'content': [
                {'text': f'**AWS Error ({error_code}):** {error_message}'},
                {'text': f'**Session ID:** {session_id}'},
                {'text': f'**Agent ARN:** {agent_arn}'},
            ],
        }

    except Exception as e:
        return {
            'status': 'error',
            'content': [
                {'text': f'**Unexpected Error:** {str(e)}'},
                {'text': f'**Session ID:** {session_id}'},
            ],
        }
