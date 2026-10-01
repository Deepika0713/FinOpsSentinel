# /usr/bin/env python3

try:
    import sys
    import json
    import argparse
    import os
    import shutil
    import subprocess
    from myModule.ai_auditor import FinOpsAIAuditor
    from myModule.tools import ToolRegistry
    from myModule.guardrails import SafetyGuardrailInterceptor
    from myModule.reporter import FinOpsReporter
except ModuleNotFoundError :
    print('[WARNING] Module not found')
    exit()
except Exception as e :
    print(f'[WARNING] : {e}')
    exit()

BANNER = """
====================================================================
  ███████╗██╗███╗   ██╗██████╗ ██████╗ ███████╗███╗   ██╗████████╗
  ██╔════╝██║████╗  ██║██╔══██╗██╔══██╗██╔════╝████╗  ██║╚══██╔══╝
  █████╗  ██║██╔██╗ ██║██║  ██║██████╔╝███████╗██╔██╗ ██║   ██║   
  ██╔══╝  ██║██║╚██╗██║██║  ██║██╔═══╝ ╚════██║██║╚██╗██║   ██║   
  ██║     ██║██║ ╚████║██████╔╝██║     ███████║██║ ╚████║   ██║   
  ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝   ╚═╝   
             Autonomous Multi-Cloud FinOps & Security AI Agent
====================================================================
"""

def main():
    parser = argparse.ArgumentParser(
        description="FinOpsSentinel: Autonomous Multi-Cloud AI Agent for FinOps & Governance",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="Execute live remediation actions (default: dry-run mode)")
    args = parser.parse_args()

    print(BANNER)

    dry_run_mode = not args.apply
    mode_str = "DRY-RUN (SAFE)" if dry_run_mode else "LIVE APPLY"

    print(f"⚙️  Execution Mode  : [{mode_str}]")
    print(f"🔒 Safety Guardrails: [ACTIVE - HITL ENABLED]")

    # Resolve the subscription without requiring Azure CLI inside the container.
    subscription_id = (os.getenv("AZURE_SUBSCRIPTION_ID") or "").strip()
    if subscription_id:
        print(f"🔑 Configured Azure Sub : {subscription_id}\n")
    elif shutil.which("az"):
        try:
            completed = subprocess.run(
                ["az", "account", "show", "--query", "id", "--output", "tsv"],
                check=True,
                capture_output=True,
                text=True,
            )
            subscription_id = completed.stdout.strip()
            if subscription_id:
                print(f"🔑 Active Azure Sub : {subscription_id}\n")
        except (OSError, subprocess.CalledProcessError):
            subscription_id = None

    if not subscription_id:
        if args.apply:
            parser.error(
                "AZURE_SUBSCRIPTION_ID is required for --apply when Azure CLI is unavailable or not authenticated"
            )
        print("⚠️  Azure subscription is not configured; dry-run starts in local sandbox mode.\n")
        subscription_id = "sandbox-sub-0000"

    auditor = FinOpsAIAuditor()
    registry = ToolRegistry(subscription_id=subscription_id, dry_run=dry_run_mode)
    guardrail = SafetyGuardrailInterceptor(dry_run=dry_run_mode)
    reporter = FinOpsReporter()

    messages = []
    print("🤖 FinOpsSentinel Ready! (Type 'exit' or 'quit' to end session)\n")

    try:
        while True:
            user_input = input("👤 You > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("👋 Ending FinOpsSentinel session...")
                break

            messages.append({"role": "user", "content": user_input})

            while True:
                response_message = auditor.run_agent_step(messages)

                msg_dict = {"role": "assistant"}
                if response_message.content:
                    msg_dict["content"] = response_message.content
                if response_message.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in response_message.tool_calls
                    ]
                
                messages.append(msg_dict)

                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        func_name = tool_call.function.name
                        call_args = json.loads(tool_call.function.arguments)

                        is_allowed, status_msg = guardrail.validate_and_intercept(func_name, call_args)

                        if not is_allowed:
                            result = {"status": "blocked", "reason": status_msg}
                            reporter.log_action(func_name, call_args, result, status="BLOCKED")
                        else:
                            result = registry.execute_tool(func_name, call_args)
                            reporter.log_action(func_name, call_args, result, status="EXECUTED")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": json.dumps(result)
                        })
                    
                    continue

                print(f"\n🤖 Agent > {response_message.content}\n")
                break

    except KeyboardInterrupt:
        print("\n👋 Session interrupted.")
    finally:
        reporter.export_reports(subscription_id=subscription_id, mode=mode_str)

if __name__ == "__main__":
    main()
