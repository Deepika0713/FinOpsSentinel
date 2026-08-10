import json
import argparse
import subprocess
from ai_auditor import FinOpsAIAuditor
from tools import ToolRegistry

def main():
    parser = argparse.ArgumentParser(description="FinOpsSentinel: Interactive Autonomous Agent")
    parser.add_argument("--apply", action="store_true", help="Execute live remediation actions (default is dry-run mode)")
    args = parser.parse_args()

    dry_run_mode = not args.apply

    print("==================================================")
    print("🛡️  FinOpsSentinel: Interactive Cloud AI Agent")
    print(f"⚙️  Execution Mode: {'[DRY-RUN (SAFE)]' if dry_run_mode else '[LIVE APPLY]'}")
    print("==================================================")

    # Fetch Subscription ID
    try:
        sub_info = subprocess.check_output("az account show", shell=True)
        subscription_id = json.loads(sub_info)["id"]
        print(f"🔑 Subscription: {subscription_id}\n")
    except Exception:
        print("❌ Could not get active Azure subscription. Run 'az login'.")
        return

    # Initialize AI Auditor & Tool Registry
    auditor = FinOpsAIAuditor()
    registry = ToolRegistry(subscription_id=subscription_id, dry_run=dry_run_mode)

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

            # Append user request to conversation history
            messages.append({"role": "user", "content": user_input})

            # Process response loop (handles multi-step tool calls)
            while True:
                response_message = auditor.run_agent_step(messages)

                # Convert response message object into printable/storable dict format
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

                # Case A: Model wants to call one or more tools
                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)

                        # Execute requested tool via Registry
                        result = registry.execute_tool(func_name, args)

                        # Append tool execution output back into conversation history
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": json.dumps(result)
                        })
                    
                    # Continue inner loop so Llama 3 reads tool results and decides next step
                    continue

                # Case B: Model gave a final text answer
                print(f"\n🤖 Agent > {response_message.content}\n")
                break

        except KeyboardInterrupt:
            print("\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error during execution: {e}\n")

if __name__ == "__main__":
    main()