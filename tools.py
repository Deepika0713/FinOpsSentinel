import json
from azure_scanner import AzureResourceScanner
from remediator import AzureRemediator

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
        """
        Routes the tool invocation to the corresponding Python implementation.
        """
        print(f"\n⚙️  [TOOL EXECUTION] Running '{tool_name}' with arguments: {arguments}")

        try:
            if tool_name == "scan_orphaned_disks":
                # Scan disks across subscription or specific RG
                disks = self.scanner.scan_unattached_disks()
                rg_filter = arguments.get("resource_group")
                if rg_filter:
                    disks = [d for d in disks if rg_filter.lower() in d["resource_id"].lower()]
                return {"status": "success", "count": len(disks), "data": disks}

            elif tool_name == "scan_unassigned_public_ips":
                ips = self.scanner.scan_unassigned_public_ips()
                rg_filter = arguments.get("resource_group")
                if rg_filter:
                    ips = [ip for ip in ips if rg_filter.lower() in ip["resource_id"].lower()]
                return {"status": "success", "count": len(ips), "data": ips}

            elif tool_name == "tag_azure_resource":
                res_id = arguments.get("resource_id")
                tags = arguments.get("tags", {})
                success = self.remediator.tag_resource(res_id, tags)
                return {
                    "status": "success" if success else "failed",
                    "resource_id": res_id,
                    "applied_tags": tags,
                    "dry_run": self.dry_run
                }

            elif tool_name == "delete_azure_resource":
                rg = arguments.get("resource_group")
                res_name = arguments.get("resource_name")
                res_type = arguments.get("resource_type")

                if res_type == "disk":
                    success = self.remediator.delete_unattached_disk(rg, res_name)
                elif res_type == "public_ip":
                    success = self.remediator.delete_unassigned_public_ip(rg, res_name)
                else:
                    return {"status": "failed", "error": f"Unsupported resource type: {res_type}"}

                return {
                    "status": "success" if success else "failed",
                    "resource_name": res_name,
                    "action": "deleted",
                    "dry_run": self.dry_run
                }

            else:
                return {"status": "failed", "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Sanity test tool registry setup
    print("✅ Testing tools.py initialization...")
    print(f"Defined {len(TOOL_SCHEMAS)} Llama 3 tool schemas.")
    for schema in TOOL_SCHEMAS:
        print(f"  • {schema['function']['name']}: {schema['function']['description']}")