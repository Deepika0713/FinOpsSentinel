import unittest
import os
import json
import shutil
from pathlib import Path
from myModule.reporter import FinOpsReporter

class ReporterStateFlushTest(unittest.TestCase):
    def setUp(self):
        # Create a temp output directory
        self.output_dir = "temp_reports"
        self.reporter = FinOpsReporter(output_dir=self.output_dir)
        
        # Write a mock initial finops_audit_report.json at root
        self.initial_data = {
            "project": "FinOpsSentinel",
            "timestamp": "2026-08-10T03:46:05.826982+00:00",
            "dry_run": False,
            "subscription_id": "test-sub",
            "total_orphaned_assets": 2,
            "findings": [
                {
                    "resource_name": "test-disk-to-delete",
                    "risk_level": "LOW",
                    "recommended_action": "TAG_FOR_DELETION",
                    "reasoning": "Test disk",
                    "estimated_savings_usd": 1.6,
                    "dry_run_executed": False
                },
                {
                    "resource_name": "test-disk-to-keep",
                    "risk_level": "LOW",
                    "recommended_action": "TAG_FOR_DELETION",
                    "reasoning": "Test disk to keep",
                    "estimated_savings_usd": 3.6,
                    "dry_run_executed": False
                }
            ]
        }
        
        # Save a backup of existing finops_audit_report.json if it exists
        self.backup_file = Path("finops_audit_report.json.bak")
        self.main_file = Path("finops_audit_report.json")
        if self.main_file.exists():
            shutil.copy(self.main_file, self.backup_file)
            
        with open(self.main_file, "w") as f:
            json.dump(self.initial_data, f, indent=2)

    def tearDown(self):
        # Cleanup temp directory
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
            
        # Restore backup of finops_audit_report.json
        if self.backup_file.exists():
            shutil.copy(self.backup_file, self.main_file)
            self.backup_file.unlink()
        elif self.main_file.exists():
            self.main_file.unlink()

    def test_remediation_removes_resolved_resource_from_reports(self):
        # Simulate deleting 'test-disk-to-delete'
        self.reporter.log_action(
            tool_name="delete_azure_resource",
            args={"resource_name": "test-disk-to-delete", "resource_type": "disk", "resource_group": "rg"},
            result={"status": "success"},
            status="EXECUTED"
        )
        
        # Export reports (scanning will fail/revert to local sandbox mock filtering)
        self.reporter.export_reports(subscription_id="test-sub", mode="LIVE APPLY")
        
        # Verify the root finops_audit_report.json has only the non-deleted resource
        with open(self.main_file, "r") as f:
            report_data = json.load(f)
            
        findings = report_data.get("findings", [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["resource_name"], "test-disk-to-keep")
        
        # Verify reports/report_latest.md exists and only contains test-disk-to-keep
        md_file = Path(self.output_dir) / "report_latest.md"
        self.assertTrue(md_file.exists())
        md_content = md_file.read_text(encoding="utf-8")
        self.assertIn("| `test-disk-to-keep` |", md_content)
        self.assertNotIn("| `test-disk-to-delete` |", md_content)

if __name__ == "__main__":
    unittest.main()
