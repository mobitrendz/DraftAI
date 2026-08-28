---
id: getting-started
title: Getting Started
sidebar_label: Getting Started
---

Follow this guide to set up, configure, and launch the frontend environment on your local development machine.

---

## Prerequisites

Before beginning, make sure your machine meets the following environment specifications:

1.  **Node.js**: `v22.14.0` (Strictly enforced via `.nvmrc`).
2.  **npm**: Packaged with Node (v10+ recommended).
3.  **Python**: `3.12+` (Required to initialize the local Git pre-commit hooks).
4.  **Running Backend**: A running instance of the FastAPI backend (usually listens at `http://localhost:8000`).

---

## Quick Start Installation

Execute the following commands in your shell to clone and configure the project:

### 1. Install Project Dependencies

Run `npm install` at the project root to fetch all Node modules:

```bash
npm install
```

### 2. Configure Git Hooks (Optional but Recommended)

The project utilizes Python-based `pre-commit` hook configurations to enforce styling and linting standards before commits are processed:

```bash
pre-commit install
```

### 3. Synchronize the OpenAPI Client

Generate the contract-first SDK classes and TanStack hooks from the active backend schema:

```bash
npm run generate-client
```

:::note
If your backend is running on a port other than `8000`, verify the backend setup or define the `VITE_API_URL` configuration environment variable before running this command.
:::

### 4. Start the Vite Development Server

Start the local server with hot module reloading (HMR) active:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser to interact with the application.

---

## ⚙️ Environment Configuration

The application validates all configuration inputs at start time using a Zod schema configured in `src/env.ts`.

### Setting up the Environment

Copy the example template file to create your active environment variable file:

```bash
cp .env.example .env
```

### Configuration Parameters

The following table details the variables available for customization in your `.env` file:

| Variable Name           | Required | Default Value           | Description                                                               |
| :---------------------- | :------- | :---------------------- | :------------------------------------------------------------------------ |
| `VITE_API_URL`          | No       | `http://localhost:8000` | The primary endpoint URL where your FastAPI backend resides.              |
| `VITE_ENV`              | No       | `development`           | Defines the execution mode. Options: `development`, `production`, `test`. |
| `VITE_ENABLE_ANALYTICS` | No       | `false`                 | A feature flag toggle to activate or deactivate frontend event reporting. |

---

## 🛠️ Main CLI Commands

Use these package manager scripts to maintain and build the codebase:

- **`npm run dev`**: Starts the HMR Vite dev server.
- **`npm run build`**: Type-checks the source code and builds optimized static assets into the `/dist` directory.
- **`npm run generate-client`**: Executes the `@hey-api/openapi-ts` builder to parse backend schemas and write them to `src/client/`.
- **`npm test`**: Launches the Vitest test suites in interactive watch mode.
- **`npm run test:run`**: Executes the test suites once and validates that coverage thresholds match required limits.
- **`npm run test:coverage`**: Runs all tests and outputs detailed code-coverage tables into `/coverage`.
- **`npm run lint`**: Inspects files for patterns violating ESLint rules.
- **`npm run format`**: Re-formats files using Prettier according to standard project conventions.
