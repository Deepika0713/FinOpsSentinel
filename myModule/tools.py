import json
from .azure_scanner import AzureResourceScanner
from .remediator import AzureRemediator

# ---------------------------------------------------------------------------
# 1. Groq / Llama 3 Tool Definitions (JSON Schemas)
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scan_orphaned_disks",
            "description": "Scans the active Azure subscription or a specific Resource Group for unattached managed disks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_group": {
                        "type": "string",
                        "description": "Optional Azure resource group name to filter scanning. If omitted, scans entire subscription."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_unassigned_public_ips",
            "description": "Scans the active Azure subscription or a specific Resource Group for unassigned public IP addresses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_group": {
                        "type": "string",
                        "description": "Optional Azure resource group name to filter scanning. If omitted, scans entire subscription."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tag_azure_resource",
            "description": "Applies specified key-value tags to an Azure resource using its Resource ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {
                        "type": "string",
                        "description": "The full Azure Resource ID string."
                    },
                    "tags": {
                        "type": "object",
                        "description": "Key-value dictionary of tags to apply (e.g., {'FinOpsSentinelStatus': 'Orphaned'})."
                    }
                },
                "required": ["resource_id", "tags"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_azure_resource",
            "description": "Deletes a specified unattached disk or unassigned IP address from Azure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_group": {
                        "type": "string",
                        "description": "The name of the Azure Resource Group containing the resource."
                    },
                    "resource_name": {
                        "type": "string",
                        "description": "The name of the resource to delete."
                    },
                    "resource_type": {
                        "type": "string",
                        "enum": ["disk", "public_ip"],
                        "description": "The category of the resource to delete ('disk' or 'public_ip')."
                    }
                },
                "required": ["resource_group", "resource_name", "resource_type"]
            }
        }
    }
]

# Append/Ensure these multi-cloud schemas are inside TOOL_SCHEMAS in tools.py

MULTI_CLOUD_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scan_aws_unattached_ebs",
            "description": "Scans AWS EC2 API for unattached Elastic Block Store (EBS) volumes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "AWS region (e.g. us-east-1)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_gcp_idle_disks",
            "description": "Scans Google Cloud Compute Engine for idle unattached persistent disks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "GCP Project ID"}
                },
                "required": []
            }
        }
    }
]

# Combine with existing Azure tool schemas
TOOL_SCHEMAS.extend(MULTI_CLOUD_SCHEMAS)


# ---------------------------------------------------------------------------
# 2. Tool Registry Class
# ---------------------------------------------------------------------------
class ToolRegistry:
    """
    Registry mapping function names received from Llama 3 tool calls 
    to underlying Azure scanner and remediator execution routines.
    """
    def __init__(self, subscription_id: str, dry_run: bool = True):
        self.subscription_id = subscription_id
        self.dry_run = dry_run
        self.scanner = AzureResourceScanner(subscription_id=subscription_id)
        self.remediator = AzureRemediator(subscription_id=subscription_id, dry_run=dry_run)

    def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Dispatches execution to the corresponding cloud handler."""
        # Azure Tools
        if tool_name == "scan_orphaned_disks":
            return self.scan_orphaned_disks()
        elif tool_name == "scan_unassigned_public_ips":
            return self.scan_unassigned_public_ips()
        elif tool_name == "tag_azure_resource":
            return self.tag_azure_resource(arguments.get("resource_id"), arguments.get("tags", {}))
        elif tool_name == "delete_azure_resource":
            return self.delete_azure_resource(
                arguments.get("resource_group"),
                arguments.get("resource_name"),
                arguments.get("resource_type")
            )
        
        # Multi-Cloud Mock Endpoints (Extensible for AWS / GCP SDKs)
        elif tool_name == "scan_aws_unattached_ebs":
            region = arguments.get("region", "us-east-1")
            return {
                "status": "success",
                "provider": "AWS",
                "region": region,
                "unattached_volumes": [
                    {"volume_id": "vol-0a1b2c3d4e5f6g7h8", "size_gb": 100, "type": "gp3", "est_monthly_cost_usd": 8.00}
                ]
            }
        elif tool_name == "scan_gcp_idle_disks":
            project = arguments.get("project_id", "default-project")
            return {
                "status": "success",
                "provider": "GCP",
                "project_id": project,
                "idle_disks": [
                    {"disk_name": "gcp-idle-disk-01", "size_gb": 50, "type": "pd-standard", "est_monthly_cost_usd": 2.00}
                ]
            }
        else:
            return {"status": "error", "message": f"Tool '{tool_name}' not implemented in registry."}

if __name__ == "__main__":
    # Sanity test tool registry setup
    print("✅ Testing tools.py initialization...")
    print(f"Defined {len(TOOL_SCHEMAS)} Llama 3 tool schemas.")
    for schema in TOOL_SCHEMAS:
        print(f"  • {schema['function']['name']}: {schema['function']['description']}")
