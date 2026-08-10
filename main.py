import sys
import json
import argparse
import subprocess
from datetime import datetime, timezone
from azure_scanner import AzureResourceScanner
from ai_auditor import FinOpsAIAuditor
from remediator import AzureRemediator

def main():
    parser = argparse.ArgumentParser(description="FinOpsSentinel: Autonomous Cloud AI Agent")
    parser.add_argument("--apply", action="store_true", help="Execute real remediation actions (default is dry-run mode)")
    args = parser.parse_args()

    dry_run_mode = not args.apply

    print("==================================================")
    print("🛡️  FinOpsSentinel: Autonomous Cloud AI Agent")
    print(f"⚙️  Execution Mode: {'[DRY-RUN (SAFE)]' if dry_run_mode else '[LIVE APPLY]'}")
    print("==================================================\n")

    # 1. Get Azure Subscription ID
    try:
        sub_info = subprocess.check_output("az account show", shell=True)
        subscription_id = json.loads(sub_info)["id"]
        print(f"🔑 Active Subscription: {subscription_id}")
    except Exception as e:
        print("❌ Could not fetch subscription ID. Run 'az login' first.")
        return

    # 2. Scan Azure Resources
    scanner = AzureResourceScanner(subscription_id=subscription_id)
    scanned_resources = scanner.scan_all()

    if not scanned_resources:
        print("🎉 No orphaned resources found in subscription!")
        return

    # 3. AI Risk Audit
    print(f"\n🧠 Auditing {len(scanned_resources)} scanned assets with Llama 3...")
    auditor = FinOpsAIAuditor()
    remediator = AzureRemediator(subscription_id=subscription_id, dry_run=dry_run_mode)
    
    audit_findings = []

    for resource in scanned_resources:
        print(f"\n📌 Resource: {resource['name']} ({resource['type']})")
        evaluation = auditor.analyze_resource_risk(resource)
        print(f"   ├─ AI Risk Level: {evaluation.get('risk_level')}")
        print(f"   ├─ Action: {evaluation.get('recommended_action')}")
        print(f"   └─ Reasoning: {evaluation.get('reasoning')}")

        # 4. Trigger Remediation based on AI Risk
        if evaluation.get("risk_level") == "LOW":
            # Tag resource for tracking
            tag_payload = {
                "FinOpsSentinelStatus": "Orphaned",
                "FinOpsSentinelAction": evaluation.get("recommended_action"),
                "EvaluatedBy": "Llama3-Groq"
            }
            remediator.tag_resource(resource["resource_id"], tag_payload)

        evaluation["dry_run_executed"] = dry_run_mode
        audit_findings.append(evaluation)

    # 5. Save Final Audit Log
    report = {
        "project": "FinOpsSentinel",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run_mode,
        "subscription_id": subscription_id,
        "total_orphaned_assets": len(audit_findings),
        "findings": audit_findings
    }

    with open("finops_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*50)
    print("✅ Day 3 Pipeline Complete! Report updated in 'finops_audit_report.json'")

if __name__ == "__main__":
    main()