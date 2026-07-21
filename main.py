import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FinOpsSentinel:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.scanned_resources = []

    def scan_azure_resources(self):
        """
        Simulates / executes scanning Azure for unattached disks & unassigned IPs.
        """
        print("🔍 [1/3] Scanning Azure Subscription for Orphaned Resources...")
        
        # Real-world payload layout returned from Azure Compute & Network APIs
        self.scanned_resources = [
            {
                "resource_id": "/subscriptions/sub-123/resourceGroups/dev-rg/providers/Microsoft.Compute/disks/unused-temp-disk-01",
                "name": "unused-temp-disk-01",
                "type": "Unattached Managed Disk",
                "size_gb": 128,
                "status": "Unattached",
                "created_days_ago": 42,
                "estimated_monthly_cost_usd": 19.20
            },
            {
                "resource_id": "/subscriptions/sub-123/resourceGroups/prod-rg/providers/Microsoft.Network/publicIPAddresses/orphan-ip-prod",
                "name": "orphan-ip-prod",
                "type": "Unassigned Public IP",
                "status": "Unassociated",
                "created_days_ago": 15,
                "estimated_monthly_cost_usd": 3.60
            }
        ]
        print(f"✅ Scanned successfully. Found {len(self.scanned_resources)} potential orphan assets.")

    def evaluate_with_ai(self):
        """
        AI Evaluation Engine: Simulates LLM risk analysis on telemetry logs.
        """
        print("\n🧠 [2/3] Analyzing Resource Risk via FinOps AI Engine...")
        
        audit_results = []
        for resource in self.scanned_resources:
            # LLM Reasoning logic
            if resource["created_days_ago"] > 30 and resource["status"] in ["Unattached", "Unassociated"]:
                risk_level = "LOW"
                action = "TAG_FOR_DELETION"
                reasoning = f"Resource has been {resource['status'].lower()} for >30 days with no active VM assignment."
            else:
                risk_level = "MEDIUM"
                action = "FLAG_FOR_REVIEW"
                reasoning = "Asset recently created. Requires human owner verification before removal."

            audit_results.append({
                "resource_name": resource["name"],
                "type": resource["type"],
                "monthly_waste_usd": resource["estimated_monthly_cost_usd"],
                "ai_risk_level": risk_level,
                "recommended_action": action,
                "ai_reasoning": reasoning
            })
        
        return audit_results

    def generate_report(self, audit_results):
        """
        Outputs structured JSON audit report.
        """
        print("\n📊 [3/3] Generating FinOps Audit Report...")
        total_waste = sum(item["monthly_waste_usd"] for item in audit_results)
        
        report = {
            "project": "FinOpsSentinel",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "dry_run_enabled": self.dry_run,
            "total_orphaned_assets": len(audit_results),
            "total_estimated_monthly_waste_usd": round(total_waste, 2),
            "findings": audit_results
        }
        
        # Save to file
        with open("finops_audit_report.json", "w") as f:
            json.dump(report, f, indent=2)
            
        print(json.dumps(report, indent=2))
        print("\n🎉 Audit Complete! Report saved to 'finops_audit_report.json'")

if __name__ == "__main__":
    agent = FinOpsSentinel(dry_run=True)
    agent.scan_azure_resources()
    results = agent.evaluate_with_ai()
    agent.generate_report(results)
