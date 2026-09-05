[English](./SECURITY.md) | [日本語](./SECURITY_ja.md)

# Security Policy

## Supported Versions

Version 0.4.0 is currently unreleased on a development branch. The table below describes released versions.

Security updates are provided for the following versions. We recommend using the latest version.

| Version | Supported          |
| ------- | ------------------ |
| 0.3.0   | :white_check_mark: |
| < 0.3.0 | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, **please do not create a public Issue**.

### How to Report

Please report via one of the following methods:

1. **GitHub Security Advisory** (recommended)
   - Report privately via [Security Advisories](https://github.com/elvezjp/code2map/security/advisories/new)

2. **Email**
   - Contact the security team directly: info@elvez.co.jp

### Information to Include

- **Description of the vulnerability**: Summary and type of the problem
- **Steps to reproduce**: Specific steps to reproduce the problem
- **Potential impact**: Estimated scope of damage and severity
- **Suggested fix** (if possible): Proposed mitigations or fixes
- **Contact information** (optional): For follow-up

### Report Example

```
Subject: [SECURITY] Vulnerability in file path handling

Description:
Insufficient validation of the input file path allows directory traversal attacks.

Steps to Reproduce:
1. Run: code2map build "../../../etc/passwd" --out ./out
2. Unintended files are processed

Impact:
Arbitrary files may be read. Severity: High

Suggested Fix:
Add normalization of the input path and validation that it resides within an allowed directory.
```

## Response Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Resolution**: Based on severity
  - Critical: Within 14 days
  - High: Within 30 days
  - Medium: Within 60 days
  - Low: Next release cycle

## Security Considerations

### File Handling

- code2map reads the specified source file and writes analysis results to the output directory
- Exercise caution when processing files from untrusted sources
- Specify a safe output directory with appropriate write permissions

### Input Validation

- Input files are identified by extension (`.py`, `.java`)
- Malformed files are handled as parse errors
- Be aware of symbolic link traversal risks

### Output Security

- Generated Markdown files contain fragments of the original source code
- When processing source code containing sensitive information, handle output files with care
- `MAP.json` contains path information of the original files

### Dependencies

- Dependencies are regularly scanned for vulnerabilities
- Run `uv sync` to obtain the latest dependencies

### Dependabot Alert Policy

We operate Dependabot alerts according to the following policy.

**Malware tab**: Always remediate, regardless of where the alert originates.

**Vulnerable**: **Remediate** (update dependencies / open a PR).

**Note**: Up to v0.2.1, the repository kept snapshots of older versions under `versions/`, and Dependabot alerts also fired against those archived lockfiles. That directory was removed in 0.3.0 (version management moved to git tags; see the README), so alerts now only fire against manifests at the repository root. Any remaining alerts originating from the removed directory are dismissed and closed after reviewing their impact.

A dismissed alert will not recur for the exact same combination of "manifest × package × CVE", but a new CVE published against the same package will trigger a new alert.

## Security Best Practices

Follow these recommendations to use code2map safely:

1. **Use the latest version**: It may contain security fixes
2. **Verify input files**: Review file contents before processing files from untrusted sources
3. **Restrict the output directory**: Manage write destinations appropriately and avoid writing to sensitive directories
4. **Handle generated artifacts carefully**: Output files contain original source code — apply appropriate access controls
5. **Run in a sandboxed environment**: Consider running in an isolated environment when processing untrusted code

## Known Security Limitations

- This tool performs static analysis only and does not execute code
- Dependencies introduced via dynamic dispatch or reflection cannot be detected
- No functionality is provided for detecting malicious code patterns

## Contact

For security-related questions that are not vulnerabilities:

- Create a GitHub Issue with the `security` label
- GitHub Discussions is available for general questions

## Acknowledgements

We are grateful to security researchers who report vulnerabilities. Upon request, we will acknowledge reporters in the release notes of the fix.
