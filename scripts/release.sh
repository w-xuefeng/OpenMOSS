#!/bin/bash
set -e

# 确保在项目根目录执行
cd "$(dirname "$0")/.."

# 检查工作区是否干净
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ 错误: 工作区有未提交的更改，请先提交或暂存它们。"
  exit 1
fi

# 获取当前所在分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "webui" ]; then
  echo "❌ 错误: 只能在 webui 分支上执行发布。当前分支为: $CURRENT_BRANCH"
  exit 1
fi

echo "📦 可选版本升级类型:"
echo "  1) patch (修补 bug, 0.0.x -> 0.0.x+1)"
echo "  2) minor (新增功能, 0.x.0 -> 0.x+1.0)"
echo "  3) major (重大更新, x.0.0 -> x+1.0.0)"
read -p "请输入对应的选项 (默认 1): " choice

case $choice in
  2) LEVEL="minor" ;;
  3) LEVEL="major" ;;
  *) LEVEL="patch" ;;
esac

echo "🚀 开始升级版本 ($LEVEL)..."

# 执行版本升级并自定义 tag 的前缀
npm version $LEVEL --tag-version-prefix="webui-v" -m "chore(release): webui-v%s"

# 读取生成的版本号和 tag
VERSION=$(node -p "require('./package.json').version")
TAG="webui-v$VERSION"

echo "📤 正在推送代码和标签 ($TAG) 到远程仓库..."
git push origin webui
git push origin $TAG

echo "✅ 发布成功！"
echo "👉 GitHub Actions 正在自动打包并创建 Release。请随后在 GitHub 仓库查看。"
