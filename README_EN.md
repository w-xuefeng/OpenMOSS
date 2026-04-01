# OpenMOSS WebUI

<p align="center">
<img src="https://github.com/uluckyXH/OpenMOSS/blob/main/docs/logo.png?raw=true" alt="OpenMOSS Logo" width="200" />
</p>

<p align="center">
<img src="https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue">
<img src="https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white" alt="Vite">
<img src="https://img.shields.io/badge/TailwindCSS-4-06B6D4?logo=tailwindcss&logoColor=white" alt="TailwindCSS">
<img src="https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
<img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

<p align="center">
  🇨🇳 <a href="README.md">简体中文</a> | 🌐 English
</p>

> **The frontend management interface for the OpenMOSS Multi-Agent Collaboration Platform.**

> This is a standalone orphan branch, completely decoupled from the backend codebase (`dev`/`main` branches), with its own independent versioning and release cycle.

---

## ✨ Features Overview

- 📊 **Dashboard** — Monitor task progress, agent activity, and review trends in real-time.
- 📋 **Task Management** — Create/edit tasks, manage sub-tasks, and handle module assignments.
- 🤖 **Agent Management** — View agent statuses, point leaderboards, and activity logs.
- 🔍 **Review Records** — Browse review history and scoring details.
- 📝 **Prompt Management** — Maintain role templates and agent-specific prompts.
- 📡 **Activity Feed** — Real-time agent activity feed (can be made publicly accessible).
- ⚙️ **System Settings** — Project configuration, security settings, and notifications management.
- 🔄 **Auto Updates** — The backend automatically detects and pulls the latest WebUI releases.

## 🚀 Quick Start

### Prerequisites

- Node.js `^20.19.0` or `>=22.12.0`
- npm

### Development Mode

```bash
# Install dependencies
npm ci

# Start dev server (automatically proxies API requests to localhost:6565)
npm run dev
```

### Production Build

```bash
npm run build
```

Build outputs are generated in the `dist/` directory, containing an auto-generated `webui-manifest.json` (version metadata).

## 📦 Release Workflow

We provide an automated, one-click release script. Simply run the following command in the project root:

```bash
npm run release
```

The script will automatically:
1. Prompt you for the version bump type (patch, minor, major)
2. Update the version inside `package.json`
3. Generate a git tag structured as `webui-vX.Y.Z`
4. Push the code and the new tag to the remote `webui` branch

Once pushed, GitHub Actions will automatically be triggered to:
1. Build the frontend
2. Generate `webui-manifest.json`
3. Package everything into `webui-dist.tar.gz`
4. Create a GitHub Release

### How the Backend Retrieves Updates

The OpenMOSS backend will automatically check and pull the latest WebUI during these specific events:

- **On Startup** — If the `static/` directory does not exist, it automatically downloads the latest Release.
- **On User Access** — Checks for new versions every 30 minutes, prompting users to update within the admin interface.

You can also trigger manual updates in the admin panel by navigating to **Settings → Display → WebUI Version**.

### Manual Installation

```bash
cd /path/to/openmoss
curl -fsSL https://github.com/uluckyXH/OpenMOSS/releases/latest/download/webui-dist.tar.gz | tar xzf - -C static/
```

### Rollbacks

If an issue arises with a specific version, simply mark it as **Pre-release** on the GitHub Releases page. The backend's `/releases/latest` API will automatically skip this version and rollback to the last stable release.

## 🏗️ Project Structure

```
.
├── src/
│   ├── api/          # API Client (Axios)
│   ├── assets/       # Static assets and global styles
│   ├── components/   # Reusable components
│   │   ├── ui/       # shadcn-vue base components
│   │   ├── common/   # Common business components
│   │   ├── demo/     # Demo page components
│   │   └── feed/     # Activity feed components
│   ├── composables/  # Vue Composables
│   ├── lib/          # Utility functions
│   ├── router/       # Vue Router configuration
│   ├── stores/       # Pinia state management
│   └── views/        # Page views
├── public/           # Public static assets
├── .github/workflows/  # CI/CD configuration
├── vite.config.ts    # Vite configuration (includes manifest plugin)
└── package.json
```

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Framework | Vue 3.5 (Composition API + `<script setup>`) |
| Build Tool | Vite 7 |
| Styling | TailwindCSS 4 |
| Component Library | shadcn-vue (reka-ui) |
| State Management | Pinia 3 |
| HTTP Client | Axios |
| Icons | Lucide Vue Next |
| Animations | GSAP, VueUse Motion |
| Linter / Formatting | ESLint + OxLint + Prettier |

## 📄 License

[MIT](../LICENSE)
