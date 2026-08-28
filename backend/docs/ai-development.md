---
icon: lucide/brain-circuit
---

# AI-Driven Development

This project is built to work seamlessly with AI coding assistants, specifically **Google Antigravity** and **Gemini CLI**.

## 🤖 Google Antigravity
Google Antigravity serves as your primary AI coding collaborator. It is optimized for:
- **Implementation**: Generating features, refactoring code, and writing tests.
- **Review**: Proactive code analysis and pull request review.
- **Maintenance**: Automated documentation and repository housekeeping.

## 🤖 Gemini CLI
The Gemini CLI is an AI-powered autonomous agent designed for rapid, surgical engineering within this project.

### Core Benefits:
- **Autonomous Engineering**: Use the CLI to research the codebase, plan complex changes, and execute focused edits.
- **Context Awareness**: Leverages repository guidance (such as `GEMINI.md`), existing code patterns, and test suites to ensure changes adhere to project standards.
- **Automated Validation**: Integrated workflows for running tests and linters immediately after any AI-initiated modification.

### Getting Started with Gemini CLI
To interact with this project:

```bash
# Start an interactive session
gemini

# Sandbox - Restrict access strictly to the current project directory
gemini --sandbox seatbelt

# Example directive
> "Add a new CRUD endpoint for 'Products' following the existing user pattern"
```

## 🧠 Architectural Mandates (`GEMINI.md`)
Always refer to `GEMINI.md` in the project root. This file contains the foundational mandates that guide AI assistants in maintaining the project's architectural integrity, security, and coding standards.
