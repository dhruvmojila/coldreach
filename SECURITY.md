# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅ Yes    |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a security issue:

1. Email the maintainer directly (see GitHub profile)
2. Or open a [GitHub Security Advisory](https://github.com/dhruvmojila/coldreach/security/advisories/new) (private)

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

You will receive a response within **72 hours**. If the issue is confirmed, a fix will be released as quickly as possible.

## Security Considerations

ColdReach is a **local-only tool** by design:

- The API server (`coldreach serve`) binds to `127.0.0.1` only — never exposed to the network
- No user data is sent to external servers (except to the external APIs you configure)
- No telemetry or analytics
- Groq API key and other credentials stay in your local `.env` file
- The Chrome extension only communicates with `localhost:8765`

## Responsible Use

ColdReach is intended for legitimate business development, job searching, and sales outreach with proper consent. Misuse for spamming or harassment violates our [Code of Conduct](CODE_OF_CONDUCT.md) and may violate applicable laws (GDPR, CAN-SPAM, etc.).
