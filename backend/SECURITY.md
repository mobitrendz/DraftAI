# Security Policy

## Supported Versions

Security updates are provided for the latest version of this project on the main
branch. If you are using an older fork or release, please update to the latest
available version before reporting an issue.

## Reporting a Vulnerability

Please do not create a public GitHub issue for security vulnerabilities.

To report a vulnerability, contact the project maintainer(sreeraj.dev@icloud.com) privately with:

- A clear description of the vulnerability
- Steps to reproduce the issue
- The affected endpoint, module, dependency, or configuration
- Any proof-of-concept code, logs, or screenshots that help explain the issue
- Your contact information for follow-up questions

If this repository is hosted on GitHub, you may also use GitHub's private
vulnerability reporting feature if it is enabled for the repository.

## Response Expectations

After a report is received, the maintainer will aim to:

1. Acknowledge the report within 5 business days.
2. Confirm whether the issue is reproducible.
3. Assess severity and potential impact.
4. Prepare and test a fix when appropriate.
5. Publish a security update or advisory once the fix is available.

## Disclosure Guidelines

Please allow reasonable time for the vulnerability to be investigated and fixed
before publicly disclosing details. Coordinated disclosure helps protect users
while the issue is being resolved.

## Security Best Practices for Deployments

When deploying this project, make sure to:

- Use strong, unique values for secrets and environment variables.
- Keep dependencies updated.
- Run the application behind HTTPS in production.
- Restrict database and admin access to trusted networks and users.
- Rotate credentials immediately if they may have been exposed.
- Review authentication, authorization, and role-based access controls before
  exposing the API publicly.
