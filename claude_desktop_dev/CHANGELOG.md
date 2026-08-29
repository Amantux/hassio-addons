# Changelog

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
