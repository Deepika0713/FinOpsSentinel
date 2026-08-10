import json
import argparse
import subprocess
from ai_auditor import FinOpsAIAuditor
from tools import ToolRegistry
from guardrails import SafetyGuardrailInterceptor

def main():
    parser = argparse.ArgumentParser(description="FinOpsSentinel: Autonomous Cloud AI Agent with Safety Guardrails")
    parser.add_argument("--apply", action="store_true", help="Execute live remediation actions (default is dry-run mode)")
    args = parser.parse_args()

    dry_run_mode = not args.apply

    print("==================================================")
    print("🛡️  FinOpsSentinel: Autonomous Cloud AI Agent")
    print(f"⚙️  Execution Mode : {'[DRY-RUN (SAFE)]' if dry_run_mode else '[LIVE APPLY]'}")
    print(f"🔒 Safety Guardrails: [ACTIVE - HITL ENABLED]")
    print("==================================================")

    # Fetch Subscription ID
    try:
        sub_info = subprocess.check_output("az account show", shell=True)
        subscription_id = json.loads(sub_info)["id"]
        print(f"🔑 Subscription   : {subscription_id}\n")
    except Exception:
        print("❌ Could not fetch Azure subscription. Ensure 'az login' is active.")
        return

    # Initialize AI Auditor, Tool Registry, and Safety Guardrails
    auditor = FinOpsAIAuditor()
    registry = ToolRegistry(subscription_id=subscription_id, dry_run=dry_run_mode)
    guardrail = SafetyGuardrailInterceptor(dry_run=dry_run_mode)

    messages = []
    print("🤖 FinOpsSentinel Ready! Type your request (or 'exit' / 'quit' to stop).\n")

    while True:
        try:
            user_input = input("👤 You > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("👋 Exiting FinOpsSentinel session.")
                break

            messages.append({"role": "user", "content": user_input})

            # Process AI tool-calling loop
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

                # Process requested tool calls
                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)

                        # 🛑 STEP 1: SAFETY GUARDRAIL & HITL INTERCEPTION
                        is_allowed, status_msg = guardrail.validate_and_intercept(func_name, args)

                        if not is_allowed:
                            # Return intercept message directly to LLM context
                            result = {"status": "blocked", "reason": status_msg}
                        else:
                            # 🚀 STEP 2: EXECUTE TOOL VIA REGISTRY IF APPROVED
                            result = registry.execute_tool(func_name, args)

                        # Pass execution result back to conversation context
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": json.dumps(result)
                        })
                    
                    continue

                # Print final response from agent
                print(f"\n🤖 Agent > {response_message.content}\n")
                break

        except KeyboardInterrupt:
            print("\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error during execution: {e}\n")

if __name__ == "__main__":
    main()