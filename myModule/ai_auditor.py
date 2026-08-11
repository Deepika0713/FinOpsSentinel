import os
import json
from dotenv import load_dotenv
from groq import Groq
from tools import TOOL_SCHEMAS

load_dotenv()

class FinOpsAIAuditor:
    """
    Groq / Llama 3 agent interface supporting multi-turn conversations
    and autonomous tool selection via function calling.
    """
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("❌ Missing GROQ_API_KEY in .env file!")
            
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        self.system_prompt = """
        You are FinOpsSentinel, an autonomous Cloud FinOps & Security AI Agent.
        Your job is to assist engineers in scanning, auditing, tagging, and optimizing Azure resources.

        Guidelines:
        1. Always use available tools to retrieve live information before answering questions about Azure resources.
        2. Evaluate cost risks carefully (Unattached disks < 64GB are LOW risk).
        3. Be clear, direct, and action-oriented.
        """

    def run_agent_step(self, messages: list) -> dict:
        """
        Sends the conversation history (including tool calls/results) to Llama 3.
        Returns the response choice containing either text or requested tool calls.
        """
        # Ensure system prompt is always present at index 0
        formatted_messages = messages.copy()
        if not formatted_messages or formatted_messages[0].get("role") != "system":
            formatted_messages.insert(0, {"role": "system", "content": self.system_prompt})

        response = self.client.chat.completions.create(
            messages=formatted_messages,
            model=self.model,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.1
        )

        return response.choices[0].message