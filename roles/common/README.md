# `common` role

> **Status:** implemented Debian-family baseline.

## Purpose

Provide the shared operating-system baseline that every HamStack-managed node can rely on, without turning the role into a kitchen-sink server build.

## Expected starting state

A supported Linux system that is booted, network-reachable, and accessible to Ansible over SSH with privilege escalation where required.

## Responsibilities

- Establish baseline packages and host settings used across HamStack roles.
- Apply project-wide conventions that are truly common to managed nodes.
- Provide a predictable foundation for higher-level radio, network, service, and visual roles.

## Non-goals

- Install or configure application-specific ham-radio software.
- Assume a particular Raspberry Pi model or other hardware platform unless a common task genuinely requires it.
- Store site-specific secrets or private inventory data.

## Configuration

See the [HamStack configuration reference](../../docs/configuration.md#role-common) for the public variables owned by this role.

## Device udev rules

With `hamstack_common_manage_udev_rules: true`, the role renders
`/etc/udev/rules.d/90-hamstack-devices.rules` from `hamstack_devices` entries
that define a `udev` mapping (for example a stable `/dev/aioc-ptt` symlink for
an AIOC's CM108 HID interface) and reloads udev when the file changes. HamStack
owns that file; operator rules belong in separate files. The option is off by
default.
