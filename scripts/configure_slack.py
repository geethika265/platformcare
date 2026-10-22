"""Save user-entered Slack tokens without terminal echo or shell history."""
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    bot = getpass("Paste Bot User OAuth Token (xoxb-...), then Enter: ").strip()
    app = getpass("Paste App-Level Token (xapp-...), then Enter: ").strip()
    if not bot.startswith("xoxb-") or not app.startswith("xapp-"):
        raise SystemExit("Token types do not match; nothing saved. Bot token starts xoxb-, app-level token starts xapp-.")
    channel = input("Optional test channel ID for automated alerts (Enter to skip): ").strip()
    if channel and not channel.startswith(("C", "G")):
        raise SystemExit("Expected a Slack channel ID beginning C or G; nothing saved.")
    settings = dict(SLACK_BOT_TOKEN=bot, SLACK_APP_TOKEN=app, SLACK_TRANSPORT="socket", SLACK_ALERT_CHANNEL=channel)
    path = ROOT / ".env"
    text = path.read_text() if path.exists() else (ROOT / ".env.example").read_text()
    lines = [line for line in text.splitlines() if line.partition("=")[0].strip() not in settings]
    lines.extend(f"{key}={value}" for key, value in settings.items())
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text("\n".join(lines) + "\n")
    print("Slack configuration saved locally. Tokens were not displayed; existing model settings preserved.")

if __name__ == "__main__":
    main()
