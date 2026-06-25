"""Kiro Q&A demo — register once, replay tokens, ask questions.

First run performs full registration (~2-3 min). Subsequent runs
load saved tokens and go straight to Q&A.

Usage:
    python test_kiro_qa.py                        # register + ask
    python test_kiro_qa.py --tokens path.json     # use specific token file
    python test_kiro_qa.py --clear                 # delete saved tokens
    python test_kiro_qa.py --history               # load session history
"""

import sys, os, argparse
sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', buffering=1)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from platforms.kiro.replay import KiroSession


def main():
    ap = argparse.ArgumentParser(description="Kiro Q Developer Q&A demo")
    ap.add_argument("--tokens", default="", help="Path to saved tokens JSON")
    ap.add_argument("--clear", action="store_true", help="Delete saved tokens")
    ap.add_argument("--history", action="store_true", help="Show session history instead of asking")
    ap.add_argument("--no-ask", action="store_true", help="Skip asking a question (just load)")
    ap.add_argument("prompt", nargs="*", default=["Write a Python hello world function, return ONLY the code, no explanation"],
                    help="Question to ask Q Developer")
    args = ap.parse_args()

    session = KiroSession(token_path=args.tokens or "")

    if args.clear:
        session.clear()
        print("Tokens cleared.")
        return

    if not session.load():
        print("No saved tokens found. Starting registration...")
        from platforms.kiro.protocol_mailbox import KiroProtocolMailboxWorker
        from providers.mailbox.tempyemail import TempyMailbox

        mailbox = TempyMailbox({})
        acct = mailbox.get_email()
        worker = KiroProtocolMailboxWorker(tag="KIRO-QA")
        result = worker.run(
            email=acct.email,
            password="KiroStr99!",
            name="QA Demo",
            otp_callback=lambda: mailbox.wait_for_code(
                acct, keyword="verification", timeout=120,
                code_pattern=r"Verification code[:\s]*(\d{6})",
            ),
        )
        if not result.get("sessionToken"):
            print(f"Registration incomplete: {result}")
            return

        session.save(result)
        print(f"Tokens saved. Email: {result.get('email', '')}")

    tokens_ok = session.has_tokens
    print(f"Session loaded: accessToken={'yes' if session.access_token else 'no'}, "
          f"sessionToken={'yes' if session.session_token else 'no'}")

    if not tokens_ok:
        print("Cannot proceed without valid tokens.")
        return

    if args.history:
        msgs = session.history()
        print(f"\nSession history ({len(msgs)} events):")
        for i, ev in enumerate(msgs):
            et = ev.get("eventType", "?")
            payload = str(ev.get("payload", ""))[:150]
            print(f"  [{i}] {et}: {payload}")
        return

    if args.no_ask:
        return

    prompt = " ".join(args.prompt)
    print(f"\nQ: {prompt}")
    print("Waiting for response...", flush=True)
    response = session.ask(prompt, timeout=90)
    print(f"A ({len(response)} chars):")
    print(response)


if __name__ == "__main__":
    main()
