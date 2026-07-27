import os
import json
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

class FinOpsAIAuditor:
    """
    Evaluates scanned Azure orphan resources using Llama 3 via Groq
    to determine deletion risk levels and recommended remediation actions.
    """
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or "YOUR_ACTUAL_GROQ_KEY" in api_key:
            raise ValueError("❌ Missing or default GROQ_API_KEY in .env file!")
            
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def analyze_resource_risk(self, resource_data: dict) -> dict:
        """
        Sends resource telemetry metadata to Llama 3 for safety evaluation.
        """
        system_prompt = """
        You are an expert Cloud FinOps & Infrastructure Security Auditor.
        Your job is to analyze orphaned cloud resource metadata and return a structured JSON risk evaluation.

        Evaluation Rules:
        1. 'Unattached Managed Disk' < 64GB with no critical tags = LOW risk.
        2. 'Unassigned Public IP' = LOW risk unless flagged as production reserved.
        3. Output MUST strictly be valid JSON with this schema:
           {
             "resource_name": "string",
             "risk_level": "LOW" | "MEDIUM" | "HIGH",
             "recommended_action": "TAG_FOR_DELETION" | "FLAG_FOR_REVIEW" | "DO_NOT_TOUCH",
             "reasoning": "1-2 sentence explanation",
             "estimated_savings_usd": number
           }
        Do NOT include any markdown formatting or commentary outside the raw JSON object.
        """

        user_prompt = f"Analyze this orphaned Azure resource metadata:\n{json.dumps(resource_data, indent=2)}"

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.1
            )

            raw_content = response.choices[0].message.content.strip()
            if raw_content.startswith("```json"):
                raw_content = raw_content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(raw_content)

        except Exception as e:
            print(f"⚠️ AI Evaluation fallback triggered for {resource_data.get('name')}: {e}")
            return {
                "resource_name": resource_data.get("name"),
                "risk_level": "MEDIUM",
                "recommended_action": "FLAG_FOR_REVIEW",
                "reasoning": "AI evaluation failed; defaulting to manual review.",
                "estimated_savings_usd": resource_data.get("estimated_monthly_cost_usd", 0)
            }

if __name__ == "__main__":
    # Test with sample disk telemetry
    sample_disk = {
        "resource_id": "/subscriptions/sub-123/resourceGroups/FinOpsSentinel-Test-RG/disks/sentinel-orphan-disk-01",
        "name": "sentinel-orphan-disk-01",
        "type": "Unattached Managed Disk",
        "size_gb": 32,
        "location": "southeastasia",
        "status": "Unattached",
        "estimated_monthly_cost_usd": 1.6
    }

    auditor = FinOpsAIAuditor()
    print("🧠 Running AI Risk Audit on sample telemetry...")
    audit_result = auditor.analyze_resource_risk(sample_disk)
    print("\n--- AI AUDIT RESULT ---")
    print(json.dumps(audit_result, indent=2))