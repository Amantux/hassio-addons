#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

# homeassistant_config:rw mounts HA's config tree (at /homeassistant), but it's owned by
# root with a restrictive mode, and this add-on runs Claude as the non-root desktop user
# (abc, whose uid is the configured PUID -- deliberately NOT 1000, so the ACL we add to the
# shared host volume benefits only this add-on and not some other uid-1000 process).
# Without an access grant, abc gets "permission denied" on /homeassistant. Grant abc an ACL
# (ownership left untouched; HA Core runs as root and ignores ACLs, so it is unaffected).
#
# secrets.yaml and .storage/ are deliberately EXCLUDED from the grant: abc gets no ACL there,
# so they stay root-only and unreadable to everything Claude does -- Read/Edit/Write AND raw
# Bash -- since abc is unprivileged. This makes the deny-rules in managed-settings.json
# belt-and-suspenders rather than the only barrier.
#
# Runs after 20-folders.sh has remapped abc to the final PUID/PGID.

RUNTIME_UID="$(id -u abc)"
RUNTIME_GID="$(id -g abc)"

for root in /homeassistant /config /homeassistant_config; do
    # Only act on a path that actually looks like an HA config tree.
    [ -d "$root" ] || continue
    { [ -e "$root/configuration.yaml" ] || [ -d "$root/.storage" ] || [ -e "$root/secrets.yaml" ]; } || continue

    bashio::log.info "Granting uid ${RUNTIME_UID} access to HA config tree at ${root}"

    if command -v setfacl > /dev/null 2>&1 \
        && setfacl -R -m "u:${RUNTIME_UID}:rwX" "$root" 2> /dev/null \
        && setfacl -R -d -m "u:${RUNTIME_UID}:rwX" "$root" 2> /dev/null; then
        bashio::log.info "  ACL applied to ${root} (ownership unchanged)"
        method="acl"
    else
        bashio::log.warning "  setfacl unavailable or unsupported on this filesystem; falling back to chown"
        if chown -R "${RUNTIME_UID}:${RUNTIME_GID}" "$root"; then
            bashio::log.info "  chowned ${root} to ${RUNTIME_UID}:${RUNTIME_GID}"
            method="chown"
        else
            bashio::log.error "  could not grant access to ${root}; it may remain inaccessible to Claude"
            continue
        fi
    fi

    # Keep secrets.yaml and .storage/ inaccessible to the runtime uid, regardless of method.
    for sens in "$root/.storage" "$root/secrets.yaml"; do
        [ -e "$sens" ] || continue
        if [ "$method" = "acl" ]; then
            setfacl -R -x "u:${RUNTIME_UID}" "$sens" 2> /dev/null || true
            setfacl -R -d -x "u:${RUNTIME_UID}" "$sens" 2> /dev/null || true
        else
            # chown fallback grabbed these too; hand them back to root and lock the mode.
            chown -R root:root "$sens" 2> /dev/null || true
            chmod -R go-rwx "$sens" 2> /dev/null || true
        fi
        bashio::log.info "  excluded ${sens} from the runtime uid's access"
    done
done
