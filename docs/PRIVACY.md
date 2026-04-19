# Privacy Policy

**AI Quality Gate** — Last updated: April 19, 2026

## 1. Overview

AI Quality Gate ("the App") is committed to protecting your privacy. This policy explains what data we process and how we handle it.

## 2. Data We Process

When installed on a GitHub repository, the App processes the following data from GitHub webhook events:

- **Issue and PR metadata**: titles, descriptions, labels, author usernames
- **PR diffs**: code changes for quality analysis
- **Repository metadata**: owner name, repository name
- **Installation metadata**: installation ID for authentication

## 3. Data We Do NOT Collect or Store

- We do **not** store any webhook payload data
- We do **not** store repository source code
- We do **not** store personal information (emails, real names, etc.)
- We do **not** use cookies or tracking mechanisms
- We do **not** sell or share any data with third parties
- We do **not** use data for advertising or marketing

## 4. How Data is Processed

1. GitHub sends a webhook event to our server when an issue or PR is created/edited
2. The App analyzes the text content in-memory using pattern matching
3. Results (AI score, quality score) are posted back to GitHub as comments/labels
4. The webhook payload is discarded immediately after processing
5. No data persists beyond the request lifecycle

## 5. Third-Party Services

- **GitHub API**: Used to read repository configuration and post analysis results
- **Render.com**: Hosts the application server (see their [privacy policy](https://render.com/privacy))

## 6. Data Retention

Zero retention. All data is processed in real-time and not stored.

## 7. Your Rights

- **Uninstall**: Remove the App at any time via GitHub Settings > Applications
- **Self-host**: Run the App on your own infrastructure for full data control
- **Inspect**: The source code is open source and fully auditable

## 8. Security

- Webhook payloads are verified using HMAC-SHA256 signatures
- GitHub API authentication uses short-lived JWT tokens
- All communication uses HTTPS/TLS encryption
- No sensitive data is logged

## 9. Children's Privacy

The App does not knowingly process data from children under 13.

## 10. Changes to This Policy

We may update this policy at any time. Changes will be reflected in the "Last updated" date above.

## 11. Contact

For privacy questions, open an issue at [github.com/AbdullahBakir97/ai-quality-gate](https://github.com/AbdullahBakir97/ai-quality-gate/issues).
