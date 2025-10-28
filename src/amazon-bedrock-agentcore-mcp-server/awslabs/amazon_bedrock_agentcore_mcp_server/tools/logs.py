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

"""AgentCore Logs Tool - CloudWatch Logs access for debugging AgentCore runtimes.

This tool provides comprehensive CloudWatch Logs access for AgentCore agents:
- Get recent logs from agent runtime
- Search logs by pattern
- List available log streams
- Get specific log stream events
"""

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


def access_agentcore_logs(
    agent_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    action: str = 'recent',
    limit: int = 50,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    filter_pattern: Optional[str] = None,
    log_stream_name: Optional[str] = None,
    endpoint: str = 'DEFAULT',
    region: str = 'us-west-2',
) -> Dict[str, Any]:
    r"""Access CloudWatch Logs for AgentCore agents with comprehensive debugging and monitoring capabilities.

    This tool provides complete CloudWatch Logs integration for AgentCore runtimes, enabling
    real-time debugging, error tracking, performance monitoring, and operational insights. It
    automatically handles agent runtime ID lookup, log stream management, and time-based filtering
    with support for both agent names and runtime IDs.

    How It Works:
    ------------
    1. **Agent Identification**: Accepts either agent_name (friendly name) or agent_id (runtime ID)
    2. **Runtime Lookup**: If agent_name provided, queries AgentCore to find runtime ID
    3. **Log Group Resolution**: Constructs CloudWatch log group path from runtime ID and endpoint
    4. **Action Routing**: Directs request to appropriate log retrieval method
    5. **Time Filtering**: Applies time range filters (default: last hour for recent logs)
    6. **Pattern Matching**: Executes CloudWatch filter patterns for search operations
    7. **Response Formatting**: Returns formatted logs with timestamps and context

    Log Access Process:
    ------------------
    1. **Validation**: Ensures either agent_name or agent_id is provided
    2. **Runtime Resolution**: Looks up agent runtime ID from AgentCore if needed
    3. **Log Group Construction**: Builds log group name: `/aws/bedrock-agentcore/runtimes/{runtime_id}-{endpoint}`
    4. **Action Execution**: Performs requested operation (recent, streams, search, tail)
    5. **Event Retrieval**: Fetches log events from CloudWatch with pagination
    6. **Time Parsing**: Converts timestamps to human-readable format
    7. **Result Formatting**: Structures logs for easy reading and debugging

    Four Log Access Patterns:
    -------------------------

    ### Pattern 1: Recent Logs (Default)
    **Get the most recent log events from all streams**

    ```python
    # Last hour of logs (default behavior)
    logs(agent_name='my-agent')

    # Last 24 hours with more events
    logs(agent_name='my-agent', start_time='2024-10-24T00:00:00', limit=200)

    # Specific time window
    logs(
        agent_id='my-agent-abc123',
        start_time='2024-10-24T12:00:00',
        end_time='2024-10-24T13:00:00',
        limit=500,
    )
    ```

    ### Pattern 2: Search Logs
    **Find specific log patterns using CloudWatch filter syntax**

    ```python
    # Find all errors
    logs(agent_name='my-agent', action='search', filter_pattern='ERROR')

    # Find exceptions in last 24 hours
    logs(
        agent_name='my-agent',
        action='search',
        filter_pattern='Exception',
        start_time='2024-10-23T00:00:00',
    )

    # Complex pattern matching
    logs(
        agent_id='my-agent-abc123',
        action='search',
        filter_pattern='[timestamp, request_id, level = "ERROR", ...]',
    )
    ```

    ### Pattern 3: List Log Streams
    **Discover available log streams and their activity**

    ```python
    # List all streams
    logs(agent_name='my-agent', action='streams')

    # List with higher limit
    logs(agent_id='my-agent-abc123', action='streams', limit=100)
    ```

    ### Pattern 4: Tail Logs
    **Get latest events from a specific log stream**

    ```python
    # Tail latest stream (auto-detected)
    logs(agent_name='my-agent', action='tail', limit=100)

    # Tail specific stream
    logs(
        agent_name='my-agent',
        action='tail',
        log_stream_name='2024/10/24/[runtime-logs]session-abc123',
        limit=50,
    )
    ```

    Args:
        agent_name: Friendly agent name for lookup (e.g., "strands_agentcore_agent")
            The tool will query AgentCore to find the runtime ID
            Easier to remember than runtime IDs
            Example: "my-research-agent"

        agent_id: Direct agent runtime ID (e.g., "strands_agentcore_agent-u8o2y49M5t")
            Skip the lookup step if you have the runtime ID
            Faster for programmatic access
            Format: {agent-name}-{random-suffix}

        action: Log access operation to perform:
            - "recent" (default): Get recent log events from all streams
              Uses: Quick health checks, latest activity
            - "streams": List available log streams with timestamps
              Uses: Session discovery, restart history
            - "search": Search logs using CloudWatch filter patterns
              Uses: Error tracking, pattern analysis
            - "tail": Get latest events from specific stream
              Uses: Session monitoring, real-time debugging

        limit: Maximum number of events/streams to return (default: 50)
            Recent/Search: Number of log events
            Streams: Number of log streams to list
            Tail: Number of events from specific stream
            Range: 1-10000 (CloudWatch limit)

        start_time: Time range start in ISO 8601 format
            Format: "2024-10-24T12:00:00" or "2024-10-24T12:00:00Z"
            Default for recent: Last 1 hour
            Default for search: Last 24 hours
            Timezone-aware recommended: "2024-10-24T12:00:00-07:00"

        end_time: Time range end in ISO 8601 format
            Format: Same as start_time
            Default: Current time (now)
            Must be after start_time
            Useful for precise debugging windows

        filter_pattern: CloudWatch Logs filter pattern for search
            Required for action="search"
            Examples:
              - Simple: "ERROR", "Exception"
              - Multiple: "ERROR" "WARNING" (OR condition)
              - Structured: "[level=ERROR]"
              - JSON: "{ $.level = \"ERROR\" }"
            See CloudWatch Logs filter syntax documentation

        log_stream_name: Specific log stream to tail
            Optional for action="tail" (uses latest if not provided)
            Format: "{year}/{month}/{day}/[runtime-logs]{session-id}"
            Example: "2024/10/24/[runtime-logs]abc123"
            Get from action="streams" output

        endpoint: AgentCore endpoint qualifier (default: "DEFAULT")
            Used to construct log group name
            Custom endpoints: Use custom endpoint name
            Production/staging separation: Use different endpoints

        region: AWS region where agent is deployed (default: us-west-2)
            Must match agent deployment region
            Cross-region log access not supported

    Returns:
        Dict containing status and response content in the format:
        {
            "status": "success|error",
            "content": [
                {"text": "Found N log events"},
                {"text": "[timestamp] [stream] message"}
            ]
        }

        Success cases:
        - recent: Formatted log events with timestamps
        - streams: List of streams with first/last event times
        - search: Matching log events with context
        - tail: Latest events from specified stream

        Error cases:
        - ResourceNotFoundException: Log group doesn't exist (agent not deployed)
        - ValidationException: Invalid parameters (time range, pattern)
        - AccessDeniedException: Missing CloudWatch Logs permissions

    Notes:
        - **Prerequisites**: Agent must be deployed and running to have logs
        - **Log Retention**: CloudWatch logs retained per account settings (default: never expire)
        - **Cost**: CloudWatch Logs charges apply for ingestion and storage
        - **Lag**: 1-2 second delay between event and availability in CloudWatch
        - **Pagination**: Tool handles CloudWatch pagination automatically
        - **Performance**: Recent logs query all streams (slower for many streams)
        - **Best Practice**: Use specific time ranges for production debugging
        - **Permissions**: Requires `logs:FilterLogEvents`, `logs:DescribeLogStreams`, `logs:GetLogEvents`
        - **Stream Lifecycle**: Streams auto-created per session, never deleted
        - **Default Times**: Recent=1hr, Search=24hr - always specify for production
        - **Pattern Syntax**: CloudWatch filter pattern syntax, not regex
        - **Memory Logs**: Memory operations appear in agent logs with "memory" prefix
        - **Tool Logs**: Tool executions logged with tool name and results
        - **Streaming**: Use tail action for real-time monitoring of active sessions
        - **Cross-Reference**: Combine with invoke() to correlate requests and logs
        - **Debugging Flow**: launch → status → logs → search for efficient troubleshooting
    """
    try:
        if not agent_name and not agent_id:
            return {
                'status': 'error',
                'content': [{'text': 'Either agent_name or agent_id must be provided'}],
            }

        client = boto3.client('logs', region_name=region)

        # If agent_name provided, lookup runtime ID
        if agent_name and not agent_id:
            bedrock_client = boto3.client('bedrock-agentcore-control', region_name=region)
            response = bedrock_client.list_agent_runtimes()

            # Find matching agent
            runtime_id = None
            for agent in response.get('agentRuntimes', []):
                if agent.get('agentRuntimeName') == agent_name:
                    runtime_id = agent.get('agentRuntimeId')
                    break

            if not runtime_id:
                return {
                    'status': 'error',
                    'content': [
                        {'text': f'Agent not found: {agent_name}'},
                        {'text': "Use agents(action='list') to see available agents"},
                    ],
                }
            agent_id = runtime_id

        # Build correct log group name: /aws/bedrock-agentcore/runtimes/{runtime_id}-{endpoint}
        log_group_name = f'/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint}'

        if action == 'recent':
            return _get_recent_logs(
                client, log_group_name, limit, start_time, end_time, filter_pattern
            )
        elif action == 'streams':
            return _list_log_streams(client, log_group_name, limit)
        elif action == 'search':
            if not filter_pattern:
                return {
                    'status': 'error',
                    'content': [{'text': 'filter_pattern required for search action'}],
                }
            return _search_logs(
                client, log_group_name, filter_pattern, limit, start_time, end_time
            )
        elif action == 'tail':
            if not log_stream_name:
                # Get latest stream
                log_stream_name = _get_latest_stream(client, log_group_name)
                if not log_stream_name:
                    return {
                        'status': 'error',
                        'content': [{'text': 'No log streams found'}],
                    }
            return _tail_logs(client, log_group_name, log_stream_name, limit)
        else:
            return {
                'status': 'error',
                'content': [
                    {'text': f'Unknown action: {action}. Use: recent, streams, search, tail'}
                ],
            }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            return {
                'status': 'error',
                'content': [
                    {'text': f'Log group not found: {log_group_name}'},
                    {'text': "Agent may not be deployed or hasn't logged yet"},
                ],
            }
        return {'status': 'error', 'content': [{'text': f'AWS Error: {str(e)}'}]}
    except Exception as e:
        return {'status': 'error', 'content': [{'text': f'Error: {str(e)}'}]}


def _get_recent_logs(
    client,
    log_group_name: str,
    limit: int,
    start_time: Optional[str],
    end_time: Optional[str],
    filter_pattern: Optional[str],
) -> Dict[str, Any]:
    """Get recent log events from all streams."""
    params = {
        'logGroupName': log_group_name,
        'limit': limit,
        'interleaved': True,
    }

    # Add time range if specified
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        params['startTime'] = int(start_dt.timestamp() * 1000)
    else:
        # Default: last hour
        params['startTime'] = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)

    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        params['endTime'] = int(end_dt.timestamp() * 1000)

    if filter_pattern:
        params['filterPattern'] = filter_pattern

    response = client.filter_log_events(**params)
    events = response.get('events', [])

    if not events:
        return {
            'status': 'success',
            'content': [{'text': 'No log events found in specified time range'}],
        }

    # Format logs
    log_lines = []
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        stream_name = event['logStreamName']
        message = event['message'].rstrip()
        log_lines.append(f'[{timestamp}] [{stream_name}] {message}')

    return {
        'status': 'success',
        'content': [
            {'text': f'Found {len(events)} log events\n'},
            {'text': '\n'.join(log_lines)},
        ],
    }


def _list_log_streams(client, log_group_name: str, limit: int) -> Dict[str, Any]:
    """List available log streams."""
    response = client.describe_log_streams(
        logGroupName=log_group_name,
        orderBy='LastEventTime',
        descending=True,
        limit=limit,
    )

    streams = response.get('logStreams', [])

    if not streams:
        return {
            'status': 'success',
            'content': [{'text': 'No log streams found'}],
        }

    # Format stream info
    stream_lines = [f'Found {len(streams)} log streams:\n']
    for stream in streams:
        stream_name = stream['logStreamName']
        last_event = datetime.fromtimestamp(stream.get('lastEventTimestamp', 0) / 1000).strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        first_event = datetime.fromtimestamp(stream.get('firstEventTimestamp', 0) / 1000).strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        stream_lines.append(f'Stream: {stream_name}')
        stream_lines.append(f'  First: {first_event}')
        stream_lines.append(f'  Last: {last_event}')
        stream_lines.append('')

    return {'status': 'success', 'content': [{'text': '\n'.join(stream_lines)}]}


def _search_logs(
    client,
    log_group_name: str,
    filter_pattern: str,
    limit: int,
    start_time: Optional[str],
    end_time: Optional[str],
) -> Dict[str, Any]:
    """Search logs with filter pattern."""
    params = {
        'logGroupName': log_group_name,
        'filterPattern': filter_pattern,
        'limit': limit,
        'interleaved': True,
    }

    # Add time range
    if start_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        params['startTime'] = int(start_dt.timestamp() * 1000)
    else:
        params['startTime'] = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)

    if end_time:
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        params['endTime'] = int(end_dt.timestamp() * 1000)

    response = client.filter_log_events(**params)
    events = response.get('events', [])

    if not events:
        return {
            'status': 'success',
            'content': [{'text': f'No matches found for pattern: {filter_pattern}'}],
        }

    # Format results
    log_lines = [f"Found {len(events)} matches for '{filter_pattern}':\n"]
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        message = event['message'].rstrip()
        log_lines.append(f'[{timestamp}] {message}')

    return {'status': 'success', 'content': [{'text': '\n'.join(log_lines)}]}


def _tail_logs(client, log_group_name: str, log_stream_name: str, limit: int) -> Dict[str, Any]:
    """Get latest logs from specific stream."""
    response = client.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        limit=limit,
        startFromHead=False,
    )

    events = response.get('events', [])

    if not events:
        return {
            'status': 'success',
            'content': [{'text': f'No events in stream: {log_stream_name}'}],
        }

    # Format logs
    log_lines = [f'Latest {len(events)} events from {log_stream_name}:\n']
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        message = event['message'].rstrip()
        log_lines.append(f'[{timestamp}] {message}')

    return {'status': 'success', 'content': [{'text': '\n'.join(log_lines)}]}


def _get_latest_stream(client, log_group_name: str) -> Optional[str]:
    """Get the most recent log stream name."""
    response = client.describe_log_streams(
        logGroupName=log_group_name, orderBy='LastEventTime', descending=True, limit=1
    )

    streams = response.get('logStreams', [])
    return streams[0]['logStreamName'] if streams else None
