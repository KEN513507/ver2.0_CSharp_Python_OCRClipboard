#!/bin/bash
echo "🧾 Git ログ表示 (グラフ形式):"
git log --oneline --graph --all

echo -e "\n🧾 直前コミットとの diff:"
git diff HEAD~1

echo -e "\n🐛 bisect のヒント:"
echo "使い方: git bisect start → git bisect bad → git bisect good"
