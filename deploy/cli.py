
import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

def main():

    parser = argparse.ArgumentParser(
        description="NovaCart AI Operations Copilot - CLI Interface"
    )
    parser.add_argument("--prompt-variant", choices=["v1_minimal", "v2_safety_first", "v3_structured"],
                        default=os.environ.get("PROMPT_VARIANT", "v3_structured"),
                        help="Prompt strategy variant")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("--session", type=str, default="", help="Session ID for memory continuity")
    args = parser.parse_args()

    os.environ["PROMPT_VARIANT"] = args.prompt_variant

    try:
        from agent.graph import run_agent
    except ImportError as e:
        print(f"Error importing agent modules: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)

    session_id = args.session or ""
    history = []

    # ANSI escape codes for terminal colouring; empty strings when --no-color.
    GREEN = "\033[92m" if not args.no_color else ""
    BLUE = "\033[94m" if not args.no_color else ""
    YELLOW = "\033[93m" if not args.no_color else ""
    CYAN = "\033[96m" if not args.no_color else ""
    RESET = "\033[0m" if not args.no_color else ""

    print(f"\n{'='*60}")
    print(f"  NovaCart AI Operations Copilot")
    print(f"  Prompt Variant: {args.prompt_variant}")
    print(f"  Decision Support Only - Read Only System")
    print(f"{'='*60}")
    print(f"\nType '/quit' to exit, '/session' to see session info, '/variant <name>' to switch prompts.")
    print(f"Provide feedback with /feedback positive or /feedback negative after a response.\n")
    print(f"Auto-tuning is active - the agent adapts based on your feedback patterns!\n")

    while True:
        try:
            user_input = input(f"{BLUE}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{GREEN}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit"):
            print(f"\n{GREEN}Goodbye!{RESET}")
            break
        elif user_input.lower() == "/session":
            print(f"Session ID: {session_id or 'Not started'}")
            print(f"History: {len(history)} interactions")
            print(f"Total cached responses: {sum(1 for h in history if h.get('cached'))}")
            continue
        elif user_input.lower().startswith("/variant"):
            parts = user_input.split()
            if len(parts) >= 2:
                new_variant = parts[1]
                if new_variant in ["v1_minimal", "v2_safety_first", "v3_structured"]:
                    os.environ["PROMPT_VARIANT"] = new_variant
                    print(f"Switched to prompt variant: {new_variant}")
                else:
                    print(f"Unknown variant: {new_variant}. Options: v1_minimal, v2_safety_first, v3_structured")
            continue
        elif user_input.lower().startswith("/feedback"):
            parts = user_input.split()
            if len(parts) >= 2 and history:
                feedback = "positive" if "positive" in parts[1].lower() else "negative"
                last_query = history[-1]
                print(f"Feedback recorded: {feedback}")

                # Re-run last query with feedback for adaptation learning
                original_input = last_query.get("user", "")
                if feedback == "negative" and original_input:
                    print("Re-processing with feedback to improve future responses...")
                    result = run_agent(original_input, session_id=session_id, feedback=feedback)
                    response = result.get("response", "No response generated.")
                    session_id = result.get("session_id", session_id)
                    confidence = result.get("confidence", 0.0)
                    latency = result.get("total_latency_ms", 0)

                    adaptation = result.get("adaptation_applied")
                    if adaptation:
                        print(f"{CYAN}[Auto-tuning activated: prompt adjusted for this topic]{RESET}")

                    print(f"{GREEN}Assistant (adapted):{RESET} {response}")
                    if confidence < 0.5:
                        print(f"{YELLOW}[Low confidence - please verify]{RESET}")
                    print(f"[{latency:.0f}ms | confidence: {confidence:.0%}]\n")
                continue
            else:
                print("No previous response to give feedback on.")
            continue

        result = run_agent(user_input, session_id=session_id)
        response = result.get("response", "No response generated.")
        session_id = result.get("session_id", session_id)
        confidence = result.get("confidence", 0.0)
        latency = result.get("total_latency_ms", 0)
        cached = result.get("cached", False)
        adaptation = result.get("adaptation_applied")

        history.append({"user": user_input, "assistant": response, "cached": cached})

        if result.get("requires_escalation"):
            print(f"{YELLOW}[Escalation Recommended]{RESET}")

        print(f"{GREEN}Assistant:{RESET} {response}")

        if adaptation:
            print(f"{CYAN}[Auto-tuned: prompt adapted based on past feedback]{RESET}")
        if cached:
            print(f"{YELLOW}[Cached response]{RESET}")
        if confidence < 0.5:
            print(f"{YELLOW}[Low confidence - please verify]{RESET}")
        print(f"[{latency:.0f}ms | confidence: {confidence:.0%}]\n")

if __name__ == "__main__":
    main()
