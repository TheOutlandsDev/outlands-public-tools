"""Terminal entry point. Importing this module performs no network or file actions."""
import argparse
import json
import sys

from .core import ChatError, Conversation, OllamaClient, load_session, safe_text, save_session


def _common(parser, sub=False):
    default = argparse.SUPPRESS if sub else None
    parser.add_argument("--connect", action="store_true", default=argparse.SUPPRESS if sub else False,
                        help="Explicitly permit a request to the independently managed local backend.")
    parser.add_argument("--endpoint", default=default if sub else "http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=default if sub else 60, help="Socket timeout in seconds, 1-300.")
    parser.add_argument("--context-chars", type=int, default=default if sub else 16384)
    parser.add_argument("--max-output-tokens", type=int, default=default if sub else 256)


def parser():
    root = argparse.ArgumentParser(description="Steven / Stephen: local terminal chat; no automatic downloads or transcript saves.")
    _common(root)
    root.add_argument("--demo", action="store_true", help="Print a deterministic fictional exchange without a backend.")
    commands = root.add_subparsers(dest="command")
    for name in ("models", "ask", "chat"):
        command = commands.add_parser(name)
        _common(command, sub=True)
        if name != "models":
            command.add_argument("--model", required=True, help="An installed local model; no model is downloaded.")
            command.add_argument("--session", help="Read one explicit schema-1 session; the model must match.")
            command.add_argument("--save", help="Write a new session file after successful exchange(s); never overwrite.")
        if name == "ask":
            command.add_argument("--prompt", required=True)
    return root


def _conversation(args):
    conversation = load_session(args.session) if args.session else Conversation(args.model)
    if conversation.model != args.model:
        raise ChatError("Requested model differs from the session; choose the same model or start a new session.")
    # Validate the bound through the constructor, keeping a defensive snapshot.
    return Conversation(args.model, conversation.messages, args.context_chars)


def main(argv=None):
    # Redirected Windows consoles may use a narrow encoding. Preserve the UTF-8
    # session content while rendering unsupported characters as visible escapes.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(errors="backslashreplace")
            except (OSError, ValueError):
                pass
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    try:
        if args.demo:
            if args.command is not None or args.connect:
                raise ChatError("Use --demo by itself without a live command or --connect.")
            print(json.dumps({"simulated": True, "modelInferenceVerified": False,
                              "description": "Fictional deterministic example; no model, server, session or network was opened.",
                              "exchange": [{"role": "user", "content": "Help me organize a fictional study plan."},
                                           {"role": "assistant", "content": "Demo fixture: list three topics, then choose one short study block."}]}, indent=2))
            return 0
        if args.command is None:
            argument_parser.print_help()
            return 0
        if not args.connect:
            raise ChatError("Live commands require --connect. Use --demo for the offline example.")
        client = OllamaClient(args.endpoint, args.timeout, args.max_output_tokens)
        if args.command == "models":
            for name in client.models():
                print(safe_text(name))
            return 0
        conversation = _conversation(args)
        successes = 0
        if args.command == "ask":
            print(safe_text(conversation.ask(client, args.prompt)))
            successes = 1
        else:
            print("Steven / Stephen: local backend chat. /help, /clear, /exit. No automatic transcript saving.")
            while True:
                try:
                    prompt = input("You: ")
                except EOFError:
                    break
                command = prompt.strip().lower()
                if command in ("/exit", "/quit", "exit", "quit"):
                    break
                if command == "/help":
                    print("/clear resets in-memory history (keeps an initial system message); /exit ends chat. --save writes once on normal exit.")
                    continue
                if command in ("/clear", "/reset"):
                    conversation.clear()
                    print("In-memory context cleared; no file was changed.")
                    continue
                if not prompt.strip():
                    continue
                try:
                    print("Steven: " + safe_text(conversation.ask(client, prompt)))
                    successes += 1
                except ChatError as error:
                    print("Error: " + safe_text(str(error)), file=sys.stderr)
        if args.save and successes:
            save_session(args.save, conversation)
            print("Saved the explicit fresh session file.", file=sys.stderr)
        return 0
    except ChatError as error:
        print("Error: " + safe_text(str(error)), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCancelled; no automatic session save was performed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
