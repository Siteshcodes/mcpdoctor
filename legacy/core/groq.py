from groq import Groq
from groq.types.chat import ChatCompletionMessage


class GroqLLM:
    def __init__(self, model: str):
        # Groq() picks up GROQ_API_KEY from the environment, just like Anthropic().
        self.client = Groq()
        self.model = model

    def add_user_message(self, messages: list, message):
        messages.append(
            {
                "role": "user",
                "content": message.content
                if isinstance(message, ChatCompletionMessage)
                else message,
            }
        )

    def add_assistant_message(self, messages: list, message):
        # When the assistant calls tools, the message object carries `tool_calls`,
        # so we append it as-is rather than flattening it to a string.
        if isinstance(message, ChatCompletionMessage):
            messages.append(message)
        else:
            messages.append({"role": "assistant", "content": message})

    def text_from_message(self, message: ChatCompletionMessage) -> str:
        return message.content or ""

    def chat(
        self,
        messages,
        system=None,
        temperature=1.0,
        stop_sequences=None,
        tools=None,
    ) -> ChatCompletionMessage:
        # Anthropic takes `system` as a top-level field; OpenAI/Groq expect a
        # system message at the front of the messages list.
        if system:
            messages = [{"role": "system", "content": system}] + messages

        params = {
            "model": self.model,
            "max_tokens": 8000,
            "messages": messages,
            "temperature": temperature,
        }

        if stop_sequences:
            params["stop"] = stop_sequences

        if tools:
            params["tools"] = tools

        completion = self.client.chat.completions.create(**params)
        return completion.choices[0].message
