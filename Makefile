.PHONY: test freeze outdated env deps docker-up check

# 仮想環境構築
env:
	python -m venv .venv
	. .venv/Scripts/activate && pip install -r requirements.txt

# テスト全部走らせる
test:
	python ocr-screenshot-app/main.py --image ./test_image.png
	pytest -m "not slow" --maxfail=1

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

# 追加のスモークテストと高速テスト実行
smoke-and-fast-test:
	@PYTHONPATH=src/python python -m ocr_screenshot_app.main --image test_image.png --no-clipboard --json > NUL 2> NUL
	@echo smoke ok
	@pytest -m "not slow" --maxfail=1
