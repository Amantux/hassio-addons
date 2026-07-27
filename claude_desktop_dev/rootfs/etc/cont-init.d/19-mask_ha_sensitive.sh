#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

# The dev fork maps homeassistant_config:rw so Claude can read and edit the HA config tree
# (configuration.yaml, automations, scripts, custom_components/). HA's add-on `map` is
# folder-granular, so that mount unavoidably drags in secrets.yaml and .storage/ (auth
# tokens, refresh tokens, config-entry secrets, and the entity/device/area registries),
# which we do NOT want exposed. The mount can't exclude them, so instead we shadow those
# paths inside THIS container's mount namespace with empty, read-only bind mounts. The
# host's real files are never touched -- HA Core reads them from its own container -- and
# because the mask is a mount (not a permission), it cannot be bypassed by DAC_READ_SEARCH
# or by root inside this container.
#
# Fail-closed: if a config tree is mounted but a mask cannot be applied, abort startup
# rather than let the add-on come up with the credentials readable.

# A single empty, locked source for every mask. Kept for the container's lifetime; the bind
# mounts hold references regardless of these paths afterwards.
EMPTY_DIR="$(mktemp -d)"
EMPTY_FILE="$(mktemp)"
chmod 000 "$EMPTY_DIR" "$EMPTY_FILE"

# True if $1 is already a mount point (keeps re-runs within one boot idempotent).
is_masked() { awk -v p="$1" '$2 == p { found = 1 } END { exit !found }' /proc/self/mounts; }

# Shadow $1 (a dir or file) with the matching empty, read-only source. The bind is what
# hides the real contents; the read-only remount is defense-in-depth and best-effort.
mask_path() {
    local target="$1" src="$2"
    mount --bind "$src" "$target" || return 1
    mount -o remount,ro,bind "$target" 2> /dev/null \
        || bashio::log.warning "Could not make ${target} read-only (still masked)"
    return 0
}

found_config=false
masked_any=false

for root in /homeassistant /config /homeassistant_config; do
    # Only act on a path that actually looks like an HA config tree.
    if [ -d "$root" ] \
        && { [ -e "$root/configuration.yaml" ] || [ -d "$root/.storage" ] || [ -e "$root/secrets.yaml" ]; }; then
        found_config=true
        bashio::log.info "Masking sensitive paths in HA config tree at ${root}"

        if [ -d "$root/.storage" ] && ! is_masked "$root/.storage"; then
            if mask_path "$root/.storage" "$EMPTY_DIR"; then
                masked_any=true
                bashio::log.info "  masked ${root}/.storage"
            else
                bashio::log.fatal "Failed to mask ${root}/.storage; refusing to start to avoid exposing HA credentials"
                bashio::exit.nok
            fi
        fi

        if [ -e "$root/secrets.yaml" ] && ! is_masked "$root/secrets.yaml"; then
            if mask_path "$root/secrets.yaml" "$EMPTY_FILE"; then
                masked_any=true
                bashio::log.info "  masked ${root}/secrets.yaml"
            else
                bashio::log.fatal "Failed to mask ${root}/secrets.yaml; refusing to start to avoid exposing HA secrets"
                bashio::exit.nok
            fi
        fi
    fi
done

if [ "$found_config" = false ]; then
    bashio::log.info "No HA config tree mounted; nothing sensitive to mask."
elif [ "$masked_any" = false ]; then
    bashio::log.info "HA config tree present but no .storage or secrets.yaml found to mask."
fi
