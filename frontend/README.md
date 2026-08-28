# React 19 + FastAPI Frontend Template

![Frontend Code Quality](https://github.com/mobitrendz/react-frontend-template/actions/workflows/frontend.yml/badge.svg?branch=develop)
![Test Coverage](https://github.com/mobitrendz/react-frontend-template/actions/workflows/coverage.yml/badge.svg?branch=develop)
![Coverage Percentage](https://img.shields.io/badge/coverage-92.66%25-brightgreen)

A modern, high-performance full-stack template featuring a React 19 frontend and a FastAPI backend. Optimized for **2026 industry standards**, this template is pre-configured with a premium design system, TanStack Query orchestration, and comprehensive unit testing.

### 🔗 Related Repositories & Documentation

- **Live Documentation**: [Docusaurus Developer Docs](https://mobitrendz.github.io/react-frontend-template/)

- **Backend Template**: [FastAPI Backend Template](https://github.com/mobitrendz/fastapi-backend-template)

- **Expo Template**: [Expo Mobile App Template](https://github.com/mobitrendz/expo-mobile-template)

## 🛠 Tech Stack

- **Frontend**: React 19 (TypeScript)
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router 7
- **UI Components**: shadcn/ui + Lucide Icons
- **Build Tool**: Vite 8
- **Styling**: Tailwind CSS 4
- **Validation**: Zod
- **Testing**: Vitest + RTL

## 🏗️ 2026 Modern Standards

This template goes beyond basic boilerplate by implementing high-performance patterns:

- **🔄 Server State Orchestration**: Powered by **TanStack Query** for automatic caching, background revalidation, and built-in loading/error management.
- **🛡️ Fail-Safe Environment**: **Zod-validated** configuration ensures the app never starts with missing or invalid environment variables.
- **🎨 Premium UI Framework**: Built on **shadcn/ui** and **Tailwind CSS 4**, featuring glassmorphism, adaptive dark mode, and Lucide-powered iconography.
- **🧬 Contract-First SDK**: Type-safe API client generated directly from your FastAPI OpenAPI schema.

## 🚀 Key Features

### 💻 Frontend & User Experience

- **🔒 Secure Authentication**: Robust login/signup flow with JWT persistence and public registration support.
- **🛣 Multi-Page Architecture**: Seamless navigation between Dashboard and Profile using React Router 7.
- **✅ Advanced Task Management**: Inline editing, priority filtering, and real-time search for tasks.
- **👤 Account Lifecycle**: Secure account deletion with password verification and automated task cleanup.
- **🌓 Adaptive Design**: Premium dark-mode design system with modern micro-animations.

### 🛠 Administrative Controls

- **👥 User Management**: Powerful admin dashboard to manage all system users.
- **⚡ Status Control**: Instant activation/deactivation of user accounts with visual feedback.
- **➕ Admin Creation**: Create new administrative accounts directly from the control center.
- **🔍 Search & Filter**: Sophisticated user searching and role-based filtering.

## 🧪 Unit Testing & Quality Assurance

The project maintains high standards for reliability with a comprehensive test suite and automated quality gates.

### Test Coverage Status

<!-- START_COVERAGE_TABLE -->

| Category       | Coverage   |
| :------------- | :--------- |
| **Statements** | **92.66%** |
| **Lines**      | **93.98%** |
| **Functions**  | **90.47%** |
| **Branches**   | **84.46%** |

<!-- END_COVERAGE_TABLE -->

### Test Coverage Details

Our test suite covers critical user flows and administrative edge cases:

- **🔐 Authentication**: Full coverage for login, token persistence, and role-based route protection.
- **👤 Profile Management**: Testing for user details updates, password changes, and account deletion flows.
- **✅ Task Operations**: Comprehensive testing of Task CRUD, filtering, and real-time search functionality.
- **🛠️ Admin Controls**:
  - **User Management**: Creation, deletion, and status toggling for administrative and regular accounts.
  - **System Intelligence**: Metrics visualization, server health monitoring, and request success ratios.
- **🛡️ Error Handling**: Robust testing of global Error Boundaries and API error extraction logic.

### Testing Stack

- **Vitest**: A blazing fast unit test framework powered by Vite.
- **React Testing Library**: The industry standard for testing component behavior.
- **JSDOM**: Modern browser environment simulation.

### Testing Workflow

To maintain our high reliability standards, follow these steps during development:

1.  **Watch Mode**: Best for active development.
    ```bash
    npm test
    ```
2.  **Full Validation**: Run the entire suite once (used in pre-commit).
    ```bash
    npm run test:run
    ```
3.  **Coverage Report**: Generate a detailed HTML report in `/coverage`.
    ```bash
    npm run test:coverage
    ```
4.  **Formatting Check**: Verify code style without applying fixes.
    ```bash
    npm run format:check
    ```
5.  **UI Debugging**: Vitest provides a powerful UI for visualizing test flows.
    ```bash
    npx vitest --ui
    ```

## 🛡️ Automated Quality Checks

### CI/CD API Guardrails

Our **GitHub Actions** workflow (`frontend.yml`) includes an automated **API Sync Check**. If the backend schema changes without a corresponding frontend SDK update (`npm run generate-client`), the CI pipeline will fail, preventing broken contracts from reaching production.

### Local Git Hooks

Before every commit, **pre-commit** runs ESLint, Prettier, and TypeScript type-checks to ensure only high-quality code enters the repository. This ensures absolute consistency with our CI/CD standards.

## 🏁 Getting Started

### Prerequisites

1.  **Node.js**: v22.14.0 (locked via `.nvmrc`).
2.  **Python**: 3.12+ (required for `pre-commit`).
3.  **Backend**: FastAPI backend running (default: `http://localhost:8000`).

### 🚀 Quick Start

Get up and running in less than 60 seconds. This template is designed for **Zero-Config** local development.

1.  **Install dependencies**:
    ```bash
    npm install
    pre-commit install
    ```
2.  **Generate the API Client**:
    ```bash
    npm run generate-client
    ```
3.  **Start development**:
    ```bash
    npm run dev
    ```

> [!TIP]
> The app defaults to `http://localhost:8000` for the backend. To customize this or other settings, see the [Environment Configuration](#-environment-configuration) section below.

## ⚙️ Environment Configuration

While the app works out-of-the-box with sensible defaults, you can customize your environment by creating a `.env` file:

```bash
cp .env.example .env
```

### Configuration Options

| Variable                | Description                            | Default                 |
| :---------------------- | :------------------------------------- | :---------------------- |
| `VITE_API_URL`          | The base URL for your FastAPI backend. | `http://localhost:8000` |
| `VITE_ENV`              | Current execution environment.         | `development`           |
| `VITE_ENABLE_ANALYTICS` | Toggle for premium analytics tracking. | `false`                 |

## 🧬 API Integration (@hey-api/openapi-ts)

This project uses `@hey-api/openapi-ts` to generate a type-safe SDK. We've enhanced this with **TanStack Query** support for a declarative data-fetching experience.

### Usage Example

```typescript
import { useQuery } from "@tanstack/react-query";
import { readTodosApiV1TodosGet } from "./client/sdk.gen";

const { data, isLoading, error } = useQuery({
  queryKey: ["todos"],
  queryFn: () => readTodosApiV1TodosGet(),
});
```

## 📂 Project Structure

- `docs-site/`: Docusaurus documentation website source code and markdown guides.
- `src/client/`: Auto-generated API client and TanStack Query hooks.
- `src/components/ui/`: shadcn/ui primitives (Button, Input, Card, etc.).
- `src/lib/`: Shared utilities (Auth logic, error handling, env validation).
- `src/env.ts`: Zod-validated environment schema.
- `src/index.css`: Tailwind 4 design system.

## 📖 Developer Documentation (Docusaurus)

We maintain detailed developer documentation inside the `/docs-site` directory, powered by **Docusaurus**.

The live hosted version of this documentation is available at **[https://mobitrendz.github.io/react-frontend-template/](https://mobitrendz.github.io/react-frontend-template/)**.

To run or build the documentation site locally from the root folder:

```bash
# Start the local Docusaurus development server
npm run docs:dev

# Build the static documentation website
npm run docs:build

# Clear Docusaurus build caches
npm run docs:clear
```

---

Built with ❤️ for rapid full-stack development. Refer to [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.

## 📋 Release Notes

See the full [Release Notes](./RELEASE_NOTES.md) for a detailed history of changes.

## ⚖️ License

This project is licensed under the MIT License.

## 💡 Inspiration

This project is heavily inspired by the official [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) in the FastAPI repository. It builds upon those foundational concepts, incorporating modern toolchain upgrades, enhanced observability, and AI-optimized developer workflows.
