# Changelog

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
