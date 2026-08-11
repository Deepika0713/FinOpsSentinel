import re

class SafetyGuardrailInterceptor:
    """
    Interceptor layer that validates tool calls requested by Llama 3
    against safety policies and enforces Human-in-the-Loop (HITL) approval.
    """
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        # Resources matching these patterns are protected from automated actions
        self.protected_patterns = [r"prod", r"production", r"critical", r"db", r"database"]

    def is_protected_resource(self, resource_name: str) -> bool:
        """Checks if a resource name contains sensitive/production keywords."""
        if not resource_name:
            return False
        for pattern in self.protected_patterns:
            if re.search(pattern, resource_name, re.IGNORECASE):
                return True
        return False

    def validate_and_intercept(self, tool_name: str, arguments: dict) -> tuple[bool, str]:
        """
        Evaluates risk for a requested tool call.
        Returns: (is_allowed: bool, reason_or_message: str)
        """
        # Read-only operations are always safe
        if tool_name in ["scan_orphaned_disks", "scan_unassigned_public_ips"]:
            return True, "SAFE_READ_ONLY"

        # 1. Evaluate Tagging Actions
        if tool_name == "tag_azure_resource":
            res_id = arguments.get("resource_id", "")
            if self.is_protected_resource(res_id):
                print(f"\n⚠️  [GUARDRAIL WARNING] Tagging requested on protected resource ID: {res_id}")
            return True, "SAFE_TAGGING"

        # 2. Evaluate Destructive Deletion Actions
        if tool_name == "delete_azure_resource":
            res_name = arguments.get("resource_name", "")
            res_group = arguments.get("resource_group", "")

            # Check for Production Name Matching
            if self.is_protected_resource(res_name) or self.is_protected_resource(res_group):
                print(f"\n🚨 [GUARDRAIL BLOCK] Intercepted deletion request for protected resource: '{res_name}' in group '{res_group}'!")
                return False, f"BLOCKED: Action cancelled. Resource '{res_name}' matches production naming protection rules."

            # Force Human-in-the-Loop (HITL) Confirmation Prompt
            print("\n" + "!"*60)
            print("🚨 HUMAN-IN-THE-LOOP (HITL) APPROVAL REQUIRED")
            print("!"*60)
            print(f"  • Requested Action: DELETION")
            print(f"  • Target Resource : {res_name}")
            print(f"  • Resource Group  : {res_group}")
            print(f"  • Mode            : {'DRY-RUN (Simulated)' if self.dry_run else 'LIVE APPLY (Permanent)'}")
            print("-" * 60)

            user_choice = input("👉 Confirm execution? Type 'YES' to approve, or press Enter to cancel: ").strip()

            if user_choice.upper() == "YES":
                print("✅ HITL Approval Granted by Engineer.")
                return True, "APPROVED_BY_HUMAN"
            else:
                print("❌ HITL Request Denied by Engineer.")
                return False, "DENIED_BY_HUMAN: User explicitly aborted the deletion operation."

        return True, "DEFAULT_ALLOW"