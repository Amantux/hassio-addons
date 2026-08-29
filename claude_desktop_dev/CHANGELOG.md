# Changelog

## 1.35-dev7

Fix a first-boot ownership race that left the Claude Code integration silently
half-configured.

cont-init.d runs as root, but the tooling in 82-claude_tools.sh runs as the
`abc` runtime user (the configured PUID, 65000 on a stock install). On a FRESH
install `$HOME/.claude` did not exist, so that script created it root-owned and
the tools could not write into it:

    tokensave: failed to write .../.claude/settings.json.new: Permission denied
    rtk:       Failed to create temp file in .../.claude: Permission denied

tokensave landed its MCP server and hooks in `.claude.json` (a file in an
already-chowned directory) but never wrote `settings.json`; rtk installed no
hook and no RTK.md. 20-folders.sh chowns $HOME recursively but runs earlier, so
it could not cover a directory created afterwards, and the corrective sweep in
84-claude_runtime_ownership.sh runs after the failed writes — which is why the
integration repaired itself on the SECOND boot and looked like a fluke.

`$HOME/.claude` is now created with the runtime identity, derived from
`id -u abc` so it follows a customised PUID rather than assuming 1000. The late
sweep in 84 is retained: 83 still writes settings.json as root by design.

Also reverts the CLAUDE_CODE_LOCAL_BINARY override added in 1.35-dev6. Reading
the shipped app bundle showed the constructor only reads that variable and
discards it, and a headless run confirmed no LOCAL OVERRIDE line is ever logged,
so it had no effect.


## 1.35-dev6

Fix "The Claude Code binary is missing or damaged."

The previous release changed PATH order, on the theory that Desktop resolved
`claude` from PATH and found this add-on's wrapper script. That was wrong:
Claude Desktop does not consult PATH for Claude Code at all. It manages its own
pinned build, downloading it into <userData>/claude-code and running that copy.
The error means that managed copy is absent or not executable -- which in this
add-on has to happen inside HOME=/data/data on every install.

Desktop supports an override, CLAUDE_CODE_LOCAL_BINARY: if the path passes an
X_OK check it is used instead of the managed download. Desktop now starts with
that pointed at /usr/bin/claude, the native binary the claude-code apt package
already installs (verified in the arm64 image: executable, and `--version`
reports 2.1.236). The download is removed from the startup path entirely.


## 1.35-dev5

Fix "The Claude Code binary is missing or damaged." Claude Desktop resolves the
Claude Code CLI from PATH, and `/usr/local/bin` precedes `/usr/bin`, so it found
this add-on's `claude` wrapper (a bashio shell script) instead of the real binary
at `/usr/bin/claude`. Desktop now launches with `/usr/bin` ahead of
`/usr/local/bin`, the same shadowing fix the wrapper already applies to itself
when handing off to Headroom.

Interactive shells are unchanged: typing `claude` in a terminal still resolves to
the wrapper, so `permission_mode` and Headroom wrapping behave exactly as before.

## 1.1

- Fix build failure: set HOME=/root when running rtk install script to ensure binary is installed to /root/.local/bin instead of /config/.local/bin (caused by LSIO base image overriding HOME)

## 1.0

- Fix build failure: remove separate `npm` apt package (already bundled in NodeSource nodejs)

## debianbookworm-1ae1f8ff-ls13

- Initial Claude Desktop add-on using LinuxServer Selkies, Home Assistant ingress, persistent sign-in data, runtime Claude Desktop updates, optional apt/pip additions, custom scripts, and bundled Claude Code optimization tools.
