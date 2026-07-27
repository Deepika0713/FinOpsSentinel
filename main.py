import json
import subprocess
from datetime import datetime
from azure_scanner import AzureResourceScanner
from ai_auditor import FinOpsAIAuditor

def run_finops_sentinel_pipeline():
    print("==================================================")
    print("🛡️  FinOpsSentinel: Autonomous Cloud AI Agent")
    print("==================================================\n")

    # 1. Obtain Azure Subscription ID
    try:
        sub_info = subprocess.check_output("az account show", shell=True)
        subscription_id = json.loads(sub_info)["id"]
        print(f"🔑 Active Subscription: {subscription_id}")
    except Exception as e:
        print("❌ Could not obtain Azure subscription. Ensure 'az login' is active.")
        return

    # 2. Run Azure Resource Scanner
    scanner = AzureResourceScanner(subscription_id=subscription_id)
    scanned_resources = scanner.scan_all()

    if not scanned_resources:
        print("🎉 No orphaned resources found in subscription! Cloud is clean.")
        return

    # 3. Run AI Risk Auditor on Scanned Assets
    print(f"\n🧠 Analyzing {len(scanned_resources)} scanned assets with Llama 3...")
    auditor = FinOpsAIAuditor()
    ai_findings = []

    for resource in scanned_resources:
        print(f"   └─ Auditing {resource['name']}...")
        evaluation = auditor.analyze_resource_risk(resource)
        ai_findings.append(evaluation)

    # 4. Compile Final FinOps Audit Report
    total_monthly_waste = sum(item.get("estimated_savings_usd", 0) for item in ai_findings)

    report = {
        "project": "FinOpsSentinel",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "subscription_id": subscription_id,
        "total_orphaned_assets": len(ai_findings),
        "total_monthly_waste_usd": round(total_monthly_waste, 2),
        "audit_findings": ai_findings
    }

    # Save report to file
    with open("finops_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*50)
    print("📊 FINAL FINOPS AUDIT REPORT SUMMARY")
    print("="*50)
    print(json.dumps(report, indent=2))
    print("\n✅ Execution complete! Full report saved to 'finops_audit_report.json'")

if __name__ == "__main__":
    run_finops_sentinel_pipeline()