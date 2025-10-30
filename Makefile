.PHONY: test freeze outdated env deps docker-up check

# 仮想環境構築
env:
	python -m venv .venv
	. .venv/Scripts/activate && pip install -r requirements.txt

# テスト全部走らせる
test:
	python ocr_app/main.py && pytest --maxfail=1 --disable-warnings -q

# freezeしてrequirements.txt更新
freeze:
	pip freeze > requirements.txt

# アップデート確認
outdated:
	pip list --outdated

# 依存ツリー確認（要 pipdeptree）
deps:
	pipdeptree

# Dockerで起動（任意）
docker-up:
	docker-compose up -d --build

# 全部まとめて実行（おまえ向き）
check:
	make outdated
	make deps
	make test
