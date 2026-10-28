# Config

user_config.database_uri is required, has no default, and is sensitive.
The host may expand it only into DATABASE_URI.

The server argument --access-mode=restricted is taken from the upstream README. Upstream flag --access-mode=restricted is present. This package does not claim readonly beyond that flag.

This package was not connected to a database.

README: Restricted Mode limits operations to read-only transactions and presently limits execution time. Documented examples use --access-mode=unrestricted; do not omit --access-mode=restricted.
