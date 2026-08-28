---
id: index
title: React 19 + FastAPI Frontend Template
sidebar_label: Overview
slug: /
---

Welcome to the official developer documentation for the **React 19 + FastAPI Frontend Template**. This documentation is organized as a docs-as-code site powered by **Docusaurus**, detailing every aspect of the project's modern tech stack, design choices, API lifecycle, and quality assurance framework.

---

## 🚀 Overview

This repository provides an enterprise-ready, high-performance web frontend template pre-configured for modern production environments. It is designed to act as a seamless counterpart to the **FastAPI Backend Template**, sharing a contract-first development philosophy.

With strict validation, auto-generated type-safe APIs, a component catalog built using Shadcn UI and Tailwind CSS 4, and extensive automated test coverage, developers can build responsive, secure, and resilient web applications.

---

## 🛠️ Key Technology Stack

The project operates on a cutting-edge 2026 stack, choosing libraries that emphasize strict type safety, visual excellence, and rapid iteration:

- **Core Logic**: **React 19** utilizing modern hooks and asynchronous rendering strategies, programmed in strict **TypeScript**.
- **Asset Bundler & Development Server**: **Vite 8** for lightning-fast Hot Module Replacement (HMR) and optimized, tree-shaken production bundles.
- **State & Data Orchestration**: **TanStack Query** (React Query v5+) for automated caching, query deduplication, optimistic updates, and offline resilience.
- **Routing Framework**: **React Router 7**, enabling secure, declarative routing with integrated layouts.
- **Design & Styling**: **Tailwind CSS 4** paired with **shadcn/ui** and **Lucide Icons** for a dark-mode first design system featuring sophisticated micro-animations.
- **Form & Schema Validation**: **Zod** for compile-time and runtime validation (e.g. environment parameters and input fields).
- **Testing Infrastructure**: **Vitest** coupled with **React Testing Library** and **JSDOM** to ensure over 90% statement coverage.

---

## 📂 Documentation Directory

To explore specific sections of this project in detail, consult the following guides:

1.  **[Getting Started](getting-started.md)**: Steps to configure environment files, install system and package dependencies, synchronize the API client, and launch the dev environment.
2.  **[Architectural Design](architecture.md)**: Deconstruction of the folder layout, core runtime lifecycle, routing strategy, and CSS custom property structures.
3.  **[Authentication & Security](authentication.md)**: Deep dive into standard and administrative authorization, session management, secure context wrappers, and route guards.
4.  **[UI Component Library](components.md)**: Reference guide of the application's pages (Dashboard, Admin controls, profile interfaces) and shadcn components.
5.  **[API & SDK Integration](api.md)**: Configuration details of `@hey-api/openapi-ts` client generation, server query wrappers, and background synchronization check.
6.  **[Testing & CI/CD Guardrails](testing.md)**: Overview of Vitest configurations, mock suites, code coverage specifications, and GitHub action triggers.
