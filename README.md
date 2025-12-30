# Hush - Smart Notifications for Home Assistant

[![CI](https://github.com/mossipcams/hush/actions/workflows/ci.yml/badge.svg)](https://github.com/mossipcams/hush/actions/workflows/ci.yml)

The notification system Home Assistant should have shipped with.

**One-liner:** Notifications that just work, with smart defaults that grow with you.

## Features

- **Zero-config useful** - Works immediately after install with smart defaults
- **Auto-classification** - Automatically categorizes notifications by entity type
- **Quiet hours** - Silences non-critical notifications at night (safety alerts always come through)
- **Deduplication** - Collapses repeated notifications to reduce spam
- **Notification history** - Dashboard card showing recent notifications
- **UI-first** - Everything configurable without touching YAML

## Quick Start

### Installation via HACS

1. Open HACS in your Home Assistant
2. Search for "Hush"
3. Click Install
4. Restart Home Assistant
5. Go to Settings → Devices & Services → Add Integration → Hush
6. Select your notification target (e.g., your phone)
7. Done!

### Manual Installation

1. Copy `custom_components/hush` to your `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via Settings → Devices & Services

## Usage

Replace your notification service calls with `notify.hush`:

```yaml
# Before
service: notify.mobile_app_my_phone
data:
  message: "Front door opened"

# After - Hush handles the rest
service: notify.hush
data:
  message: "Front door opened"
```

Hush will:
- Auto-detect the category from the trigger entity
- Apply smart routing rules (quiet hours, deduplication)
- Log the notification to history
- Deliver to your configured target

## Smart Defaults

| Category | Behavior |
|----------|----------|
| Safety (leak, smoke, CO) | Always notify immediately |
| Security (doors, locks) | Notify, respect quiet hours |
| Device (offline, battery) | Notify once per hour |
| Motion | Log only, don't push |
| Other | Notify with 5-min deduplication |

## Configuration

Most users won't need to configure anything beyond the initial setup. Advanced settings are available in the Hush panel (sidebar).

## License

MIT License - see [LICENSE](LICENSE) for details.
