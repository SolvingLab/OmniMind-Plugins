# Himalaya v2.2.1 usage quoted from the pinned README

Source: https://github.com/pimalaya/himalaya/blob/5b12b2a8c2c253b98f15c46610ad74cba2a182bc/README.md

Commit: `5b12b2a8c2c253b98f15c46610ad74cba2a182bc`

Tag: `v2.2.1`

The README title line is `CLI to manage emails`. This file quotes the Usage section. It is not a live mailbox session and not a sent message.

Do not run the installer commands earlier in that README.

## Usage

Every command carries its own `--help`, the source of truth for its flags and syntax. The snippets below are a taste of the surface.

```text
himalaya mailbox list
himalaya envelope list --page 2
himalaya envelope search from alice and after 2026-01-01 order by date desc
himalaya flag add --flag seen 1 2 3 5
himalaya message read 42
himalaya message copy --from INBOX --to Archives 42
himalaya attachment download 42
```

The same page says the grammar lives in `himalaya envelope search --help`.

Protocol-specific examples on that page include:

```text
himalaya imap raw 'a1 SEARCH FROM "alice@example.com"\r\n'
himalaya smtp send -f me@example.com -t you@example.com < message.eml
```

Compose example on that page:

```text
himalaya message compose --to you@example.org --subject Hello --body Hi --send
```

`smtp send` and `message compose --send` send mail. Do not run them unless the user explicitly requested that send. Account-reading commands use the user's own Himalaya configuration; this package does not create that configuration.
