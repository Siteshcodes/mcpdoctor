from core.groq import GroqLLM
from mcp_client import MCPClient
from core.tools import ToolManager


class Chat:
    def __init__(self, llm: GroqLLM, clients: dict[str, MCPClient]):
        self.llm: GroqLLM = llm
        self.clients: dict[str, MCPClient] = clients
        self.messages: list[dict] = []

    async def _process_query(self, query: str):
        self.messages.append({"role": "user", "content": query})

    async def run(
        self,
        query: str,
    ) -> str:
        final_text_response = ""

        await self._process_query(query)

        while True:
            message = self.llm.chat(
                messages=self.messages,
                tools=await ToolManager.get_all_tools(self.clients),
            )

            self.llm.add_assistant_message(self.messages, message)

            if message.tool_calls:
                text = self.llm.text_from_message(message)
                if text:
                    print(text)
                tool_result_messages = await ToolManager.execute_tool_requests(
                    self.clients, message
                )
                self.messages += tool_result_messages
            else:
                final_text_response = self.llm.text_from_message(message)
                break

        return final_text_response
