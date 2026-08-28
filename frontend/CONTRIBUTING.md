# Contributing to MobiTrendz React Template

Thank you for your interest in contributing! This project follows modern 2026 industry standards for React and FastAPI integration. Please follow these guidelines to ensure a smooth contribution process.

## 🛠️ Development Environment

### Prerequisites

- **Node.js**: v22.14.0 (Check `.nvmrc`)
- **npm**: v10.0.0 or higher
- **FastAPI Backend**: Ensure the [FastAPI Backend Template](https://github.com/mobitrendz/fastapi-backend-template) is running locally on port 8000 for full functionality.

### Setup

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    npm install
    pre-commit install
    ```
3.  Set up your environment variables:
    ```bash
    cp .env.example .env
    ```
4.  Start the development server:
    ```bash
    npm run dev
    ```

## 🏗️ Technical Standards

### 1. Contract-First Development

We use `@hey-api/openapi-ts` to generate our API client. **Never** modify files in `src/client/` manually.

- If the backend schema changes, run:
  ```bash
  npm run generate-client
  ```

### 2. State Management

- Use **TanStack Query** for all server-state (API calls).
- Avoid `useEffect` for data fetching.
- Use the auto-generated hooks from `src/client/sdk.gen` where possible.

### 3. Styling & Components

- We use **Tailwind CSS 4** and **shadcn/ui**.
- New UI primitives should be added to `src/components/ui/`.
- Maintain the **MobiTrendz** premium aesthetic (glassmorphism, dark mode, high-contrast borders).

### 4. Type Safety

- All new code must be written in **TypeScript**.
- Use **Zod** for any runtime validation (forms, API responses, env variables).

## 🧪 Testing Policy

We maintain a **90%+ test coverage** goal.

- Run tests: `npm test`
- Check coverage: `npm run test:coverage`
- Ensure all new features include unit tests using **Vitest** and **React Testing Library**.

## 🚀 Pull Request Process

1.  Create a feature branch from `main`.
2.  Ensure `pre-commit run --all-files` passes locally.
3.  Verify all tests pass locally.
4.  Update the `README.md` if you are adding new features or changing configuration.
5.  Open a PR with a clear description of changes and screenshots for UI modifications.

## 📜 Code of Conduct

Please be respectful and professional in all interactions. We aim to foster an inclusive and welcoming environment for all contributors.

---

_Happy Coding!_ 🚀
