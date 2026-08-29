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
