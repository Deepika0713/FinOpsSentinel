import os
import json
import subprocess
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.web import WebSiteManagementClient

class AzureResourceScanner:
    """
    Scans Microsoft Azure subscriptions to discover orphaned assets
    such as unattached Managed Disks and unassigned Public IP addresses.
    """
    def __init__(self, subscription_id: str):
        self.subscription_id = subscription_id
        
        # DefaultAzureCredential automatically authenticates using your active 'az login' session
        self.credential = DefaultAzureCredential()
        
        # Initialize Azure SDK Management Clients
        self.compute_client = ComputeManagementClient(self.credential, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credential, self.subscription_id)
        self.web_client = WebSiteManagementClient(self.credential, self.subscription_id)

    def scan_unattached_disks(self):
        """Discovers managed disks where managed_by is None."""
        print("🔍 Scanning Azure Compute API for unattached Managed Disks...")
        orphaned_disks = []
        
        disks = self.compute_client.disks.list()
        for disk in disks:
            # If disk.managed_by is None, the disk is NOT attached to any Virtual Machine
            if disk.managed_by is None:
                resource_group = disk.id.split("/")[4] if "/" in disk.id else "Unknown"
                
                # Estimate cost (~$0.05 per GB/month for Standard LRS)
                estimated_cost = round((disk.disk_size_gb or 0) * 0.05, 2)
                
                orphaned_disks.append({
                    "resource_id": disk.id,
                    "name": disk.name,
                    "type": "Unattached Managed Disk",
                    "resource_group": resource_group,
                    "size_gb": disk.disk_size_gb,
                    "location": disk.location,
                    "status": "Unattached",
                    "estimated_monthly_cost_usd": estimated_cost
                })
                
        return orphaned_disks

    def scan_unassigned_public_ips(self):
        """Discovers Public IPs where ip_configuration is None."""
        print("🔍 Scanning Azure Network API for unassigned Public IPs...")
        orphaned_ips = []
        
        public_ips = self.network_client.public_ip_addresses.list_all()
        for ip in public_ips:
            # If ip.ip_configuration is None, the IP address is sitting idle
            if ip.ip_configuration is None:
                resource_group = ip.id.split("/")[4] if "/" in ip.id else "Unknown"
                
                orphaned_ips.append({
                    "resource_id": ip.id,
                    "name": ip.name,
                    "type": "Unassigned Public IP",
                    "resource_group": resource_group,
                    "ip_address": ip.ip_address if ip.ip_address else "Unassigned Static",
                    "location": ip.location,
                    "status": "Unassociated",
                    "estimated_monthly_cost_usd": 3.60  # Standard hourly rate estimation (~$0.005/hr)
                })
                
        return orphaned_ips

    def scan_empty_app_service_plans(self, web_client=None):
        """Discovers App Service Plans with 0 hosted web apps on paid tiers."""
        print("🔍 Scanning Azure Web API for empty App Service Plans...")
        orphaned_plans = []
        client = web_client or self.web_client
        
        plans = client.app_service_plans.list()
        for plan in plans:
            has_paid_sku = plan.sku and plan.sku.tier and plan.sku.tier.lower() != "free"
            if plan.number_of_sites == 0 and has_paid_sku:
                resource_group = plan.id.split("/")[4] if "/" in plan.id else "Unknown"
                orphaned_plans.append({
                    "resource_id": plan.id,
                    "name": plan.name,
                    "type": "AppServicePlan",
                    "resource_group": resource_group,
                    "location": plan.location,
                    "status": "Empty",
                    "estimated_monthly_cost_usd": 19.20
                })
        return orphaned_plans

    def scan_aged_snapshots(self, compute_client=None, max_age_days=90):
        """Discovers VM snapshots older than max_age_days."""
        print("🔍 Scanning Azure Compute API for aged VM Snapshots...")
        orphaned_snapshots = []
        client = compute_client or self.compute_client
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        snapshots = client.snapshots.list()
        for snapshot in snapshots:
            if snapshot.time_created:
                age_days = (now - snapshot.time_created).days
                if age_days > max_age_days:
                    resource_group = snapshot.id.split("/")[4] if "/" in snapshot.id else "Unknown"
                    estimated_cost = round((snapshot.disk_size_gb or 0) * 0.05, 2)
                    orphaned_snapshots.append({
                        "resource_id": snapshot.id,
                        "name": snapshot.name,
                        "type": "Snapshot",
                        "resource_group": resource_group,
                        "location": snapshot.location,
                        "status": "Aged",
                        "estimated_monthly_cost_usd": estimated_cost
                    })
        return orphaned_snapshots

    def scan_all(self):
        """Executes a full scan across all supported resource types."""
        disks = self.scan_unattached_disks()
        ips = self.scan_unassigned_public_ips()
        plans = self.scan_empty_app_service_plans()
        snapshots = self.scan_aged_snapshots()
        return disks + ips + plans + snapshots

if __name__ == "__main__":
    # Helper to automatically retrieve Subscription ID from active Azure CLI session
    try:
        sub_info = subprocess.check_output("az account show", shell=True)
        subscription_id = json.loads(sub_info)["id"]
        
        print(f"✅ Active Subscription ID: {subscription_id}\n")
        
        scanner = AzureResourceScanner(subscription_id=subscription_id)
        results = scanner.scan_all()
        
        print("\n" + "="*50)
        print(f"🎯 SCAN COMPLETE: Found {len(results)} Orphaned Assets")
        print("="*50)
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        print("💡 Hint: Did you run 'az login' inside your terminal first?")