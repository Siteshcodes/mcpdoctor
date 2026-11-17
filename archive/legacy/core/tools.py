import json
from typing import Optional, List
from mcp.types import CallToolResult, TextContent
from mcp_client import MCPClient
from groq.types.chat import ChatCompletionMessage


class ToolManager:
    @classmethod
    async def get_all_tools(cls, clients: dict[str, MCPClient]) -> list[dict]:
        """Gets all tools from the provided clients in OpenAI/Groq function format."""
        tools = []
        for client in clients.values():
            tool_models = await client.list_tools()
            tools += [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        # MCP's inputSchema is already JSON Schema, which is
                        # exactly what `parameters` expects.
                        "parameters": t.inputSchema,
                    },
                }
                for t in tool_models
            ]
        return tools

    @classmethod
    async def _find_client_with_tool(
        cls, clients: list[MCPClient], tool_name: str
    ) -> Optional[MCPClient]:
        """Finds the first client that has the specified tool."""
        for client in clients:
            tools = await client.list_tools()
            tool = next((t for t in tools if t.name == tool_name), None)
            if tool:
                return client
        return None

    @classmethod
    def _build_tool_result_message(cls, tool_call_id: str, text: str) -> dict:
        """Builds a `role: tool` message tied to the originating tool call."""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": text,
        }

    @classmethod
    async def execute_tool_requests(
        cls, clients: dict[str, MCPClient], message: ChatCompletionMessage
    ) -> List[dict]:
        """Executes the tool calls in a Groq message against the MCP clients."""
        tool_calls = message.tool_calls or []
        tool_result_messages: list[dict] = []

        for tool_call in tool_calls:
            tool_call_id = tool_call.id
            tool_name = tool_call.function.name
            # Groq returns arguments as a JSON string; MCP expects a dict.
            try:
                tool_input = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_input = {}

            client = await cls._find_client_with_tool(
                list(clients.values()), tool_name
            )

            if not client:
                tool_result_messages.append(
                    cls._build_tool_result_message(
                        tool_call_id, "Could not find that tool"
                    )
                )
                continue

            try:
                tool_output: CallToolResult | None = await client.call_tool(
                    tool_name, tool_input
                )
                items = tool_output.content if tool_output else []
                content_list = [
                    item.text for item in items if isinstance(item, TextContent)
                ]
                content_json = json.dumps(content_list)
            except Exception as e:
                content_json = json.dumps(
                    {"error": f"Error executing tool '{tool_name}': {e}"}
                )
                print(content_json)

            tool_result_messages.append(
                cls._build_tool_result_message(tool_call_id, content_json)
            )

        return tool_result_messages
