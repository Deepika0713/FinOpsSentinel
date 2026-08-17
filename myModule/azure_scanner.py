import os
import json
import subprocess
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.monitor.querymetrics import MetricsClient

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
        self.sql_client = SqlManagementClient(self.credential, self.subscription_id)
        self.monitor_client = MetricsClient("https://global.metrics.monitor.azure.com", self.credential)

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

    def scan_idle_sql_databases(self, sql_client=None, monitor_client=None):
        """Discovers SQL databases with low or zero CPU/DTU usage over the past 7 days."""
        print("🔍 Scanning Azure SQL API for idle databases...")
        idle_dbs = []
        s_client = sql_client or self.sql_client
        m_client = monitor_client or self.monitor_client
        
        from datetime import datetime, timezone, timedelta
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        
        try:
            servers = s_client.servers.list()
            for server in servers:
                resource_group = server.id.split("/")[4] if "/" in server.id else "Unknown"
                databases = s_client.databases.list_by_server(resource_group, server.name)
                for db in databases:
                    if db.name.lower() == "master":
                        continue
                        
                    cpu_avg = 0.0
                    dtu_avg = 0.0
                    try:
                        metrics_response = m_client.query_resource(
                            db.id,
                            metric_names=["cpu_percent", "dtu_consumption_percent"],
                            timespan=(start_time, end_time)
                        )
                        for metric in metrics_response.metrics:
                            if metric.name == "cpu_percent" and metric.timeseries:
                                vals = [v.average for v in metric.timeseries[0].data if v.average is not None]
                                cpu_avg = sum(vals) / len(vals) if vals else 0.0
                            elif metric.name == "dtu_consumption_percent" and metric.timeseries:
                                vals = [v.average for v in metric.timeseries[0].data if v.average is not None]
                                dtu_avg = sum(vals) / len(vals) if vals else 0.0
                    except Exception as e:
                        print(f"    ⚠️ Could not query metrics for DB {db.name}: {e}")
                        cpu_avg = 0.0
                        dtu_avg = 0.0
                        
                    if cpu_avg < 1.0 and dtu_avg < 1.0:
                        idle_dbs.append({
                            "resource_id": db.id,
                            "name": db.name,
                            "type": "SqlDatabase",
                            "resource_group": resource_group,
                            "location": db.location,
                            "status": "Idle / Low Usage",
                            "estimated_monthly_cost_usd": 15.00
                        })
        except Exception as e:
            print(f"❌ Error scanning SQL databases: {e}")
            
        return idle_dbs

    def scan_all(self):
        """Executes a full scan across all supported resource types."""
        disks = self.scan_unattached_disks()
        ips = self.scan_unassigned_public_ips()
        dbs = self.scan_idle_sql_databases()
        return disks + ips + dbs

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