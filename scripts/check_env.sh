#!/bin/bash
echo "📦 アウトデートされたパッケージ一覧:"
pip list --outdated

echo -e "\n📚 現在の依存パッケージ凍結:"
pip freeze > freeze_all.txt

echo -e "\n🌲 依存関係ツリー:"
pipdeptree || echo "⚠️ pipdeptree 未インストール: pip install pipdeptree"

echo -e "\n📦 pip-compile 実行:"
pip-compile requirements.in || echo "⚠️ pip-tools 未インストール: pip install pip-tools"

echo -e "\n🧪 テスト実行 (pytest):"
pytest --maxfail=1 --disable-warnings -q
