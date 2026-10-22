# Stage 4: connect a test Slack workspace

No Docker, public tunnel or paid Slack workflow feature is needed. Use Slack in your browser to avoid installing a desktop app.

## 1. Workspace

Open https://slack.com/get-started#/createnew and create a workspace named **PlatformCare Lab**. Use the Free plan. You do not need to invite people or upgrade to a trial. Create a private test channel named `platformcare-test`.

## 2. App from manifest

Open https://api.slack.com/apps and choose **Create New App -> From a manifest**. Select your new workspace, choose the JSON tab, and paste the contents of the repository's `slack-manifest.json`. Review the app and create it.

On macOS you can copy the non-secret manifest with:

```bash
cd /Users/geethika/Documents/apple
pbcopy < slack-manifest.json
```

The manifest enables Socket Mode, the three slash commands, interactive feedback, and only bot scopes `commands` and `chat:write`. It does not request message-history reading permissions.

## 3. Two tokens

- **Bot token:** In **OAuth & Permissions**, choose **Install to Workspace**, review the requested permissions, then copy the **Bot User OAuth Token** beginning `xoxb-`.
- **App token:** In **Basic Information -> App-Level Tokens**, choose **Generate Token and Scopes**, name it `platformcare-socket`, add `connections:write`, and generate the token beginning `xapp-`.
- Confirm **Socket Mode** is enabled. A signing secret and public request URL are not required for this local Socket Mode setup.

Keep tokens out of chat, screenshots, source control and terminal commands. The app can post in channels it joins; use only the private test channel for the prototype.

## 4. Invite and save

In `platformcare-test`, run `/invite @PlatformCare`. The bot must be a member to post. Optionally copy the channel ID from the channel details; it begins with `C` or `G`.

Save tokens using the standard-library helper:

```bash
cd /Users/geethika/Documents/apple
python3 scripts/configure_slack.py
```

It asks for each token with hidden input, preserves existing Groq settings, and sets owner-only `.env` permissions. The optional channel ID enables automatic incident posts in that channel. Leave it blank until you want automated alerts enabled.

## 5. Live checks (after configuration)

Do not mark Stage 4 complete until the app is actually connected and these checks run in Slack:

1. Start only the Slack bot and the small local pipeline; a dashboard/API server is not required for these commands.
2. `/platform-health` should return the current synthetic pipeline state and freshness.
3. Run the invalid-input workload locally, then `/platform-help Why did the pipeline fail?`.
4. Verify immediate acknowledgment, a support thread, and a live model answer citing job/log/runbook evidence.
5. Click **Helpful**, **Not helpful**, or **Escalate** and verify local support metrics.
6. Use `/incident-summary <id>` for an incident ID from local job/incident records.
7. If alert delivery was enabled, confirm a new failure posts once under normal polling, then a healthy run posts a resolution in the same thread.
8. Stop the bot after testing to release RAM and disconnect Socket Mode.

Only one investigation runs at a time, with one additional queued request. Sending a third concurrent request produces a busy response rather than unbounded worker threads. Delivery retries are not exactly-once across process crashes; this is a documented local prototype.

Local handler tests use fake Slack clients and do not send messages or make LLM calls. They do not verify a real workspace installation or WebSocket connection.

## References

- Create a workspace: https://slack.com/help/articles/206845317-Create-a-Slack-workspace/
- Socket Mode: https://docs.slack.dev/tools/bolt-python/concepts/socket-mode/
- App manifests: https://docs.slack.dev/reference/app-manifest/
- Acknowledge within three seconds: https://docs.slack.dev/tools/bolt-python/concepts/acknowledge/
