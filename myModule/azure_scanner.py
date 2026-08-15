import os
import json
import subprocess
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

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

    def scan_all(self):
        """Executes a full scan across all supported resource types."""
        disks = self.scan_unattached_disks()
        ips = self.scan_unassigned_public_ips()
        return disks + ips

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