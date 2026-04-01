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
  🇨🇳 简体中文 | 🌐 <a href="README_EN.md">English</a>
</p>

> **OpenMOSS 多 Agent 协作平台的前端管理界面。**
>
> 本分支为独立的 orphan 分支，与后端代码（`dev`/`main` 分支）分离，拥有独立的版本号和发布周期。

---

## ✨ 功能概览

- 📊 **仪表盘** — 实时监控任务进度、Agent 活跃度、审查趋势
- 📋 **任务管理** — 创建/编辑任务，管理子任务与模块分配
- 🤖 **Agent 管理** — 查看 Agent 状态、积分排行、活动日志
- 🔍 **审查记录** — 浏览审查历史与评分详情
- 📝 **提示词管理** — 维护角色模板与 Agent 提示词
- 📡 **活动流** — 实时 Agent 活动动态（可公开访问）
- ⚙️ **系统设置** — 项目配置、安全设置、通知管理
- 🔄 **自动更新** — 后端自动检测并拉取最新 WebUI 版本

## 🚀 快速开始

### 环境要求

- Node.js `^20.19.0` 或 `>=22.12.0`
- npm

### 开发模式

```bash
# 安装依赖
npm ci

# 启动开发服务器（默认代理 API 到 localhost:6565）
npm run dev
```

### 生产构建

```bash
npm run build
```

构建产物输出到 `dist/` 目录，包含自动生成的 `webui-manifest.json`（版本元数据）。

## 📦 发布流程

本项目提供了全自动的一键发布脚本，只需在项目根目录执行：

```bash
npm run release
```

执行后脚本会自动：
1. 询问要升级的版本号类型 (patch, minor, major)
2. 更新 `package.json` 中的版本信息
3. 自动生成形如 `webui-vX.Y.Z` 的 Git 标签 (Tag)
4. 自动将代码和 Tag 推送到远端 `webui` 分支

推送之后，GitHub Actions 会被自动触发，线上的 CI 会完成以下操作：
1. 构建前端
2. 生成 `webui-manifest.json`
3. 打包为 `webui-dist.tar.gz`
4. 创建 GitHub Release

### 后端如何获取更新

OpenMOSS 后端会在以下时机自动检查并拉取最新 WebUI：

- **启动时** — 若 `static/` 目录不存在，自动下载最新 Release
- **用户访问时** — 每 30 分钟检查一次新版本，在管理界面中提示更新

也可在管理后台的 **系统设置 → 显示 → WebUI 版本** 中手动触发更新。

### 手动安装

```bash
cd /path/to/openmoss
curl -fsSL https://github.com/uluckyXH/OpenMOSS/releases/latest/download/webui-dist.tar.gz | tar xzf - -C static/
```

### 版本回滚

若某个版本存在问题，在 GitHub Release 页面将其标记为 **Pre-release**。后端的 `/releases/latest` 会自动跳过该版本，回退到上一个稳定版本。

## 🏗️ 项目结构

```
.
├── src/
│   ├── api/          # API 客户端（axios）
│   ├── assets/       # 静态资源与全局样式
│   ├── components/   # 可复用组件
│   │   ├── ui/       # shadcn-vue 基础组件
│   │   ├── common/   # 通用业务组件
│   │   ├── demo/     # Demo 页面组件
│   │   └── feed/     # 活动流组件
│   ├── composables/  # Vue 组合式函数
│   ├── lib/          # 工具函数
│   ├── router/       # 路由配置
│   ├── stores/       # Pinia 状态管理
│   └── views/        # 页面视图
├── public/           # 静态公共资源
├── .github/workflows/  # CI/CD 配置
├── vite.config.ts    # Vite 配置（含 manifest 插件）
└── package.json
```

## 🛠️ 技术栈

| 类别 | 技术 |
|---|---|
| 框架 | Vue 3.5 (Composition API + `<script setup>`) |
| 构建 | Vite 7 |
| 样式 | TailwindCSS 4 |
| 组件库 | shadcn-vue (reka-ui) |
| 状态管理 | Pinia 3 |
| HTTP | Axios |
| 图标 | Lucide Vue Next |
| 动画 | GSAP, VueUse Motion |
| 代码规范 | ESLint + OxLint + Prettier |

## 📄 License

[MIT](../LICENSE)
