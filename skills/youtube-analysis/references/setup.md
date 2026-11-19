# Dependency Setup

Share only the section for whatever the preflight found missing; never paste the whole page. The user must do every step themselves, because sign-ins, authorizations and key creation all involve their own accounts.

## Contents

1. vidIQ MCP connector (by client)
2. YouTube Data API key
3. Letting the agent read the key (the most common snag)
4. Common errors

---

## 1. vidIQ MCP connector

- Server URL: `https://mcp.vidiq.com/mcp`
- Auth: OAuth. Connecting opens a browser to sign in to vidIQ and authorize; the client never sees the vidIQ password.
- Plans: Free, Boost and Max all include MCP. Free gets about 150 credits a month, shared with vidIQ's other AI features on the website. Once they run out, you wait for the billing cycle to reset; the Free plan cannot buy top-ups.

| Client | How to add it |
|---|---|
| Claude.ai / Claude Desktop (incl. Cowork) | Settings → Connectors → search the directory for vidIQ and connect. If it is not listed, click Add custom connector, paste the URL above → Connect → sign in to vidIQ and authorize |
| Claude Code | Run `claude mcp add --transport http vidiq https://mcp.vidiq.com/mcp` in a terminal, then type `/mcp` in Claude Code and pick vidiq to sign in |
| ChatGPT | Search the ChatGPT app directory for vidIQ → Install → sign in and authorize |
| Codex CLI | `codex mcp add vidiq --url https://mcp.vidiq.com/mcp`, then `codex mcp login vidiq` |
| Cursor | Settings → MCP → Add new MCP server, or put `{"mcpServers": {"vidiq": {"url": "https://mcp.vidiq.com/mcp"}}}` in `~/.cursor/mcp.json`, then sign in from the MCP settings |
| VS Code (Copilot) | Put `{"servers": {"vidiq": {"type": "http", "url": "https://mcp.vidiq.com/mcp"}}}` in `.vscode/mcp.json` and sign in when prompted on server start |
| Gemini CLI | Put `{"mcpServers": {"vidiq": {"httpUrl": "https://mcp.vidiq.com/mcp"}}}` in `~/.gemini/settings.json`, then run `/mcp auth vidiq` |
| OpenCode | Put `{"mcp": {"vidiq": {"type": "remote", "url": "https://mcp.vidiq.com/mcp"}}}` in `opencode.json` |
| Other MCP clients | Add a remote HTTP (Streamable HTTP) MCP server with the URL above, using OAuth |

Client menus and commands change over time; their current documentation wins. New tools usually appear only after restarting the session.

**Verify**: have the agent call `vidiq_balance` (free). If it returns `totalCredits`, the connection works.

## 2. YouTube Data API key

Official and free, with a default of 10,000 quota units per project per day. A full single-video analysis uses roughly 20–50 units.

1. Open https://console.cloud.google.com/, sign in with a Google account, and create a project from the top bar (any name, e.g. youtube-analysis).
2. Left menu: APIs & Services → Library → search **YouTube Data API v3** → Enable.
3. APIs & Services → Credentials → Create credentials → **API key**.
4. Recommended: Edit API key → API restrictions → Restrict key → tick only YouTube Data API v3. Leave Application restrictions at None, because script calls cannot pass a website-referrer restriction.
5. Copy the key and store it as described in the next section.

No credit card and no OAuth consent screen are needed. An API key reads public data only; private data such as audience demographics, retention curves and traffic sources needs the channel owner's authorization (see "Data neither source can reach" in `data-sources.md`).

## 3. Letting the agent read the key

**Do not paste the key into the chat.** Chat history is stored, and a leaked key lets others burn through your quota.

The scripts look for the key in this order and use the first one found:

1. Environment variable `YOUTUBE_API_KEY`
2. A `.env` file in the current directory
3. `~/.config/youtube-analysis/.env`
4. On macOS, `launchctl getenv YOUTUBE_API_KEY`

**Recommended: a config file.** It works across agents and platforms.

macOS / Linux, in a terminal (replace `your-key`):

```bash
mkdir -p ~/.config/youtube-analysis && printf 'YOUTUBE_API_KEY=%s\n' 'your-key' > ~/.config/youtube-analysis/.env && chmod 600 ~/.config/youtube-analysis/.env
```

Windows PowerShell:

```powershell
New-Item -Force -ItemType Directory "$HOME\.config\youtube-analysis" | Out-Null; Set-Content "$HOME\.config\youtube-analysis\.env" "YOUTUBE_API_KEY=your-key"
```

**Why `export` is not enough**: processes started by GUI apps such as Claude Desktop or Cursor do not inherit variables exported in a terminal window, so the agent never sees them. The config file above is the simplest fix. On macOS, `launchctl setenv YOUTUBE_API_KEY "your-key"` also works until the next reboot; on Windows, `setx YOUTUBE_API_KEY "your-key"` works for programs started afterwards.

**Cloud sandboxes** (Claude.ai code execution, Codex cloud and similar) cannot see local files. Either set `YOUTUBE_API_KEY` in the platform's environment-variable or secrets settings, or confirm the sandbox can reach `www.googleapis.com`. If it cannot, use vidIQ-only mode.

## 4. Common errors

| Preflight message | Cause | Fix |
|---|---|---|
| YOUTUBE_API_KEY not found | The key is not set, or the agent cannot see it | Write the config file from section 3 |
| The key is invalid | Copied incompletely, stray spaces or quotes, or the key was deleted | Copy it again |
| YouTube Data API v3 is not enabled | Step 2 was skipped | Enable it in the Library and wait 1–2 minutes |
| API restrictions do not include YouTube Data API v3 | The key is restricted to other APIs | Edit the key and add YouTube Data API v3 |
| Website (referrer) or IP restriction | Application restrictions are set | Change them to None |
| Today's quota is used up | Over 10,000 units | Resets at midnight Pacific Time |
| Cannot reach googleapis.com | Network, proxy or sandbox allowlist | Check the network; if it cannot be fixed, use vidIQ-only mode |
| vidIQ tools missing | Connector not added or not authorized, or the session needs a restart | Add it per section 1 and restart the session |
| vidIQ returns unauthorized or 401 | OAuth expired | Sign in to vidIQ again from the client |
