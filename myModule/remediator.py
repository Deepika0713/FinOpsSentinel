import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

class AzureRemediator:
    """
    Executes safe remediation actions (tagging & deletion) 
    on Azure resources evaluated as LOW risk by FinOpsSentinel AI.
    """
    def __init__(self, subscription_id: str, dry_run: bool = True):
        self.subscription_id = subscription_id
        self.dry_run = dry_run
        self.credential = DefaultAzureCredential()
        
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)
        self.compute_client = ComputeManagementClient(self.credential, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credential, self.subscription_id)

    def tag_resource(self, resource_id: str, tags: dict) -> bool:
        """Applies FinOps tracking tags safely using Azure's dedicated Tags operations."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would apply tags {tags} to {resource_id.split('/')[-1]}")
            return True

        try:
            print(f"  🏷️ Applying tags {tags} to {resource_id.split('/')[-1]}...")
            
            # Format payload specifically for Azure TagResource scope API
            tag_parameter = {
                "properties": {
                    "tags": tags
                }
            }
            
            # Use self.resource_client.tags directly
            poller = self.resource_client.tags.begin_create_or_update_at_scope(
                scope=resource_id,
                parameters=tag_parameter
            )
            poller.wait()
            
            print("  ✅ Tag applied successfully!")
            return True
        except Exception as e:
            print(f"  ❌ Failed to tag resource: {e}")
            return False
        
    def delete_unattached_disk(self, resource_group: str, disk_name: str) -> bool:
        """Deletes an unattached managed disk from Azure."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would delete unattached disk: {disk_name}")
            return True

        try:
            print(f"  🗑️ Deleting unattached disk {disk_name}...")
            async_delete = self.compute_client.disks.begin_delete(resource_group, disk_name)
            async_delete.wait()
            print("  ✅ Disk deleted successfully!")
            return True
        except Exception as e:
            print(f"  ❌ Failed to delete disk: {e}")
            return False

    def delete_unassigned_public_ip(self, resource_group: str, ip_name: str) -> bool:
        """Deletes an unassigned static public IP address."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would delete unassigned public IP: {ip_name}")
            return True

        try:
            print(f"  🗑️ Deleting public IP {ip_name}...")
            async_delete = self.network_client.public_ip_addresses.begin_delete(resource_group, ip_name)
            async_delete.wait()
            print("  ✅ Public IP deleted successfully!")
            return True
        except Exception as e:
            print(f"  ❌ Failed to delete Public IP: {e}")
            return False