# Python＋Git＋環境管理向け・調べておくと便利なコマンド集（2025-10-30）

---

## Pythonパッケージ・環境管理

- `pip list --outdated`
  - インストール済みパッケージのうち、アップデート可能なものを一覧。依存関係トラブルの予兆を掴める。
  - [note.nkmk.me](https://note.nkmk.me/python-pip-list-outdated/)

- `pip freeze --all > freeze_all.txt`
  - 全パッケージ（サブ依存も含む）をフリーズ。環境再現性と依存汚染をチェック。
  - [Stack Overflow](https://stackoverflow.com/questions/34704335/pip-freeze-all-packages-including-dependencies)

- `pipdeptree`（インストール必要）　
  - 依存関係ツリーを視覚化。どのパッケージが誰を引き込んでるか把握できる。
  - [Reddit](https://www.reddit.com/r/Python/comments/7w2w2g/pipdeptree_a_command_line_utility_to_display/)

---

## Git運用・履歴管理

- `git log --oneline --graph --all`
  - ブランチやマージの履歴をざっと可視化。ブランチ運用が乱れてないか確認用。

- `git diff HEAD~1`
  - 直前コミットとの差分チェック。意図しない変更が混ざってないか即座に確認できる。
  - [Level Up Coding](https://levelup.gitconnected.com/git-diff-explained-6c7e4b6cfa75)

- `git bisect start → git bisect good/git bisect bad`
  - バグがいつ混入したか探すスイッチ。開発が進んで「どこで壊れた？」となった時に使える。

---

## テスト・CI/CD

- `python -m unittest discover` または `pytest --maxfail=1 --disable-warnings -q`
  - 単体・統合テストを全自動で回す。CI化の根幹。
  - [Real Python](https://realpython.com/python-testing/)

- `gh workflow run <workflow_file>`（GitHub CLI）
  - CIワークフローを手動で起動。テスト／ビルド／デプロイをコマンドから。

---

## 依存管理・ロックファイル

- `pip install pip‑tools && pip-compile requirements.in`
  - 手動で管理した「トップレベル依存」からロックファイル生成。pip freezeだけでは依存に漏れ・不要が生まれる。
  - [Built In](https://builtin.com/software-engineering-perspectives/pip-tools-python)

---

## Docker・仮想環境

- `docker-compose run --rm app pytest`
  - アプリをコンテナ化して、環境差異排除。Windows特有のDLL・DPI・マルチモニタ問題がOCRで出るなら、仮想環境基盤で一貫試験するのが安心。
