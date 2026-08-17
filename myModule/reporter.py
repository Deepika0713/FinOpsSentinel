import os
import json
from datetime import datetime

class FinOpsReporter:
    """
    Tracks agent actions, calculates estimated cost savings, 
    and exports JSON audit logs and Markdown reports.
    """
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.audit_log = []
        self.total_savings_usd = 0.0

    def log_action(self, tool_name: str, args: dict, result: dict, status: str):
        """Records an individual tool execution entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": tool_name,
            "arguments": args,
            "status": status,
            "result": result
        }
        self.audit_log.append(entry)

        # Track potential monthly cost savings on deletion/remediation
        if tool_name == "delete_azure_resource" and status == "EXECUTED":
            res_type = args.get("resource_type", "")
            if res_type == "disk":
                self.total_savings_usd += 1.60  # Default benchmark cost for test disks
            elif res_type == "public_ip":
                self.total_savings_usd += 3.60  # Default benchmark cost for unassigned IPs
            elif res_type == "nic":
                self.total_savings_usd += 0.00  # NICs do not have standalone direct costs
            elif res_type == "nsg":
                self.total_savings_usd += 0.00  # NSGs do not have standalone direct costs
            elif res_type == "route_table":
                self.total_savings_usd += 0.00  # Route tables do not have standalone direct costs

    def export_reports(self, subscription_id: str, mode: str):
        """Generates both JSON and Markdown report artifacts."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        dry_run = (mode == "DRY-RUN (SAFE)")

        # 1. Trigger an automatic re-scan/state refresh
        print("[STATUS] Re-scanning infrastructure to confirm state changes...")
        from .azure_scanner import AzureResourceScanner
        scanner = AzureResourceScanner(subscription_id=subscription_id)
        
        live_findings = []
        try:
            # Try to scan live Azure infrastructure
            scanned = scanner.scan_all()
            for item in scanned:
                # Map scanned resource to findings schema
                res_name = item.get("name")
                res_type = item.get("type")
                est_cost = item.get("estimated_monthly_cost_usd", 0.0)
                
                if res_type == "NetworkInterface":
                    reasoning = f"The unattached network interface '{res_name}' poses a security and hygiene risk."
                elif res_type == "NetworkSecurityGroup":
                    reasoning = f"The unassociated network security group '{res_name}' is detached from all subnets and interfaces."
                elif res_type == "RouteTable":
                    reasoning = f"The unlinked route table '{res_name}' is not associated with any subnets."
                else:
                    reasoning = f"The unattached/unassigned {res_type} poses a cost risk."
                
                live_findings.append({
                    "resource_name": res_name,
                    "risk_level": "LOW",
                    "recommended_action": "TAG_FOR_DELETION",
                    "reasoning": reasoning,
                    "estimated_savings_usd": est_cost,
                    "dry_run_executed": dry_run
                })
        except Exception:
            # If live scanning fails (e.g. sandbox mode), filter the initial findings file
            print("[WARNING] Live Azure scan failed (Sandbox Mode). Filtering resolved resources locally...")
            initial_findings_file = "finops_audit_report.json"
            initial_findings = []
            if os.path.isfile(initial_findings_file):
                try:
                    with open(initial_findings_file, "r") as f:
                        initial_data = json.load(f)
                        initial_findings = initial_data.get("findings", [])
                except Exception:
                    pass
            
            # Determine which resources were successfully deleted
            deleted_resources = set()
            for action in self.audit_log:
                if action.get("tool") == "delete_azure_resource" and action.get("status") == "EXECUTED":
                    deleted_resources.add(action.get("arguments", {}).get("resource_name"))
            
            # Filter out deleted resources
            for finding in initial_findings:
                if finding.get("resource_name") not in deleted_resources:
                    finding["dry_run_executed"] = dry_run
                    live_findings.append(finding)

        # 2. Export JSON Audit Logs
        json_data = {
            "project": "FinOpsSentinel",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "dry_run": dry_run,
            "subscription_id": subscription_id,
            "total_orphaned_assets": len(live_findings),
            "findings": live_findings
        }

        # Write to finops_audit_report.json in the root
        with open("finops_audit_report.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        # Write to reports/finops_audit_report.json
        with open(os.path.join(self.output_dir, "finops_audit_report.json"), "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        # Write to audit_latest.json
        with open(os.path.join(self.output_dir, "audit_latest.json"), "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        # Also write the timestamped version
        json_filename = os.path.join(self.output_dir, f"finops_audit_{timestamp_str}.json")
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        # 3. Export Markdown Summary Report
        md_filename = os.path.join(self.output_dir, f"finops_report_{timestamp_str}.md")
        md_content = self._generate_markdown(subscription_id, mode, live_findings)

        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Also write to latest Markdown pointer
        with open(os.path.join(self.output_dir, "report_latest.md"), "w", encoding="utf-8") as f:
            f.write(md_content)

        print("\n" + "="*50)
        print("[REPORT] FINOPSSENTINEL REPORT GENERATED")
        print("="*50)
        print(f"  • JSON Audit Log : {json_filename}")
        print(f"  • Markdown Report: {md_filename}")
        print(f"  • Estimated Monthly Savings: ${round(self.total_savings_usd, 2)} USD")
        print("="*50 + "\n")

    def _generate_markdown(self, subscription_id: str, mode: str, live_findings: list) -> str:
        """Helper to build a styled Markdown report."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        md = f"""# 🛡️ FinOpsSentinel - Cloud Audit & Remediation Summary

**Date:** {now}  
**Subscription ID:** `{subscription_id}`  
**Execution Mode:** `{mode}`  
**Projected Monthly Savings:** **${round(self.total_savings_usd, 2)} USD**

---

## 🔍 Live Findings (Remaining Active Issues: {len(live_findings)})

"""
        if not live_findings:
            md += "*No active orphaned assets remaining! Infrastructure is clean.*\n\n"
        else:
            md += "| Resource Name | Risk Level | Recommended Action | Estimated Savings |\n"
            md += "| :--- | :--- | :--- | :--- |\n"
            for finding in live_findings:
                name = finding.get("resource_name")
                risk = finding.get("risk_level")
                action = finding.get("recommended_action")
                savings = finding.get("estimated_savings_usd", 0.0)
                md += f"| `{name}` | `{risk}` | `{action}` | `${savings:.2f} USD` |\n"
            md += "\n"

        md += """## 📑 Action Log Details

| Timestamp (UTC) | Tool Name | Target Resource / Arguments | Execution Status |
| :--- | :--- | :--- | :--- |
"""
        for item in self.audit_log:
            ts = item['timestamp'].split('T')[1][:8]
            tool = item['tool']
            status = item['status']
            args = json.dumps(item['arguments'])
            
            status_badge = "✅ EXECUTED" if status == "EXECUTED" else f"⚠️ {status}"
            md += f"| `{ts}` | `{tool}` | `{args}` | {status_badge} |\n"

        md += """
---
*Report auto-generated by FinOpsSentinel Autonomous Cloud AI Agent.*
"""
        return md