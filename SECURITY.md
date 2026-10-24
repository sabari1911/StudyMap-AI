# Security Policy

## Supported version
Security fixes are accepted for the latest code on the `main` branch.

## Reporting a vulnerability
Do not publish API keys, credentials, or exploitable security details in a public issue. Use GitHub's private vulnerability reporting feature if enabled. Otherwise, contact the repository owner privately through their GitHub profile.

## Safe development
- Keep secrets in local environment variables and never commit `.env`.
- Do not use real student personal data in test fixtures or issue reports.
- The Flask server is for local development only; do not expose its debug server publicly.
