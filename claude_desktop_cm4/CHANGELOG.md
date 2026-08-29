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

## 1.35-dev4

Initial release of the CM4 variant, for Home Assistant Yellow and other
Raspberry Pi Compute Module 4 / Pi 4 boards.

**Why this exists.** The standard Claude Desktop (Dev) add-on declares three
host devices that a Raspberry Pi running Home Assistant OS does not provide.
Docker refuses to create a container when any device in the list is missing, so
the add-on installs and then fails to start. Home Assistant add-on config has no
per-architecture `devices:` syntax, so the only way to support both boards is a
separate add-on.

**What changed versus Claude Desktop (Dev)**

- Removed `/dev/kvm` — arm64 KVM needs the kernel running at EL2 with
  `CONFIG_KVM`; HA OS on Raspberry Pi does not provide it.
- Removed `/dev/vhost-vsock` — needs the `vhost_vsock` module, not loaded on
  HA OS Pi builds.
- Removed `/dev/dri/card1` — a Pi exposes `card0` and `renderD128`; there is
  no second card node. The `/dev/dri` directory is mapped whole instead.
- Removed the x86 virtualization stack (`qemu-system-x86`, `ovmf`). With no
  `/dev/kvm` these would software-emulate x86 on a Cortex-A72 — installable but
  unusable. Cowork microVMs are not available on this board.
- Defaults tuned for the board: `SELKIES_FRAMERATE` 15 to 10 and `AUTO_GPU`
  off, because there is no VA-API/Vulkan userspace here and Selkies encodes on
  the CPU alongside Home Assistant itself.
- `DRINODE` picker reduced to the nodes a Pi can actually have.
- AppArmor profile renamed to `claude_desktop_cm4` so it cannot collide with
  the profile shipped by the other add-on.
