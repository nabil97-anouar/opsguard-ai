# Security policy

Security fixes target the current `main` branch. Older commits and unreleased snapshots have no separate maintenance commitment.

## Report privately

Use this repository's **Security → Report a vulnerability** option when GitHub private vulnerability reporting is enabled. If that option is unavailable, open an issue asking only for a private reporting channel; do not include vulnerability details. Adding this file does not enable GitHub's reporting feature.

Privately include the affected commit, a minimal reproduction using synthetic data, impact, and any proposed mitigation. Do not put credentials, personal data, real incident logs, exploit payloads, or access tokens in public issues or pull requests. Coordinate public disclosure with the maintainer after a fix or mitigation has been discussed; there is no promised response deadline or bounty.

## Scope and limits

OpsGuard currently uses deterministic reasoning and local fixture adapters. It has no authentication, tenant isolation, infrastructure control, or approve/reject/resume workflow. Run the unauthenticated API within a trusted local boundary. Compose publishes services on loopback. Policy checks and regression tests do not establish general model-level injection resistance or semantic correctness.

Evidence and audit history are ordinary SQL records, not tamper-evident storage. Dependency checks cover known package advisories, not all application vulnerabilities. See [Security Boundaries](docs/SECURITY_BOUNDARIES.md).

## Dependency policy

CI runs `pip-audit` and `npm audit` across runtime and development dependencies. High/critical findings fail. Python advisories are enriched with GitHub severity; unrated findings and scanner/feed failures also fail for review. Low/moderate findings remain visible without failing CI. No advisory exceptions are currently configured. Do not suppress a finding without documenting its scope, rationale, owner and expiry in a reviewed change.
