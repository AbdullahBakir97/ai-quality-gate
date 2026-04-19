# Terms of Service

**AI Quality Gate** — Last updated: April 19, 2026

## 1. Acceptance of Terms

By installing or using the AI Quality Gate GitHub App ("the App"), you agree to these Terms of Service. If you do not agree, do not install or use the App.

## 2. Description of Service

AI Quality Gate is an open-source GitHub App that analyzes issues and pull requests for AI-generated content patterns and contribution quality. The App:

- Receives webhook events from GitHub repositories where it is installed
- Analyzes text content using pattern matching and heuristic algorithms
- Posts comments, applies labels, and creates check runs on GitHub
- Does not store any data beyond the duration of request processing

## 3. Data Processing

- The App processes webhook payloads sent by GitHub in real time
- No user data, repository content, or personal information is stored permanently
- Analysis is performed in-memory and results are sent back to GitHub immediately
- The App does not collect, sell, or share any personal data

## 4. User Responsibilities

- You are responsible for configuring the App appropriately for your repositories
- You may customize behavior via `.github/ai-gate.yml` in your repository
- You may uninstall the App at any time to stop all processing

## 5. Accuracy Disclaimer

The App uses heuristic pattern matching to estimate AI authorship probability. Results are indicative, not definitive. False positives and false negatives may occur. The App should be used as one signal among many, not as the sole basis for rejecting contributions.

## 6. Open Source License

The App is open source under the MIT License. You may inspect, modify, and self-host the source code at any time.

## 7. Limitation of Liability

THE APP IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM THE USE OF THE APP.

## 8. Changes to Terms

We may update these terms at any time. Continued use of the App constitutes acceptance of updated terms.

## 9. Contact

For questions about these terms, open an issue at [github.com/AbdullahBakir97/ai-quality-gate](https://github.com/AbdullahBakir97/ai-quality-gate/issues).
