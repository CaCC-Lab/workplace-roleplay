# Bugfix: 本番デプロイの pip install を requirements 未変更時にスキップ

## Current Behavior（現在の動作）

本番デプロイ（`.github/workflows/deploy-production.yml`）において、デプロイ時に毎回 VM 上で以下を無条件実行している:

```bash
python3 -m venv venv        # 既に存在しても実行される
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt   # 約 60 秒
```

結果、requirements.txt が変わらないコミットでも毎回全ライブラリの DL/再インストールが走る。
実測: deploy job 全体 47秒 / 5分24秒デプロイの一部。

## Expected Behavior（期待する動作）

`requirements.txt` のハッシュが前回デプロイ時と同じなら pip install をスキップ。
初回および requirements.txt 変更時のみ実行する。

- 初回（venv 不在）: 従来どおり全実行
- 2回目以降（requirements 変更なし）: スキップ
- requirements.txt 変更時: 再実行 + 新ハッシュ記録

## Unchanged Behavior（変更しない動作）

- venv の場所 (`${APP_PATH}/venv`)
- 依存パッケージの内容・バージョン
- requirements.txt の変更時は従来どおり完全再インストール
- ロールバック・バックアップロジック・ヘルスチェック

## Root Cause（根本原因）

GitHub Actions デプロイスクリプトが冪等性を意識せず、venv を毎回新規作成前提で書かれていた。

## Fix Strategy（修正方針）

VM 上で `venv/.requirements.sha256` にハッシュを記録し、次回デプロイ時に比較:

```bash
cd ${APP_PATH}
REQ_HASH=$(sha256sum requirements.txt | awk '{print $1}')
STAMP_FILE="venv/.requirements.sha256"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate

if [ ! -f "$STAMP_FILE" ] || [ "$(cat $STAMP_FILE 2>/dev/null)" != "$REQ_HASH" ]; then
  pip install --upgrade pip
  pip install -r requirements.txt
  echo "$REQ_HASH" > "$STAMP_FILE"
else
  echo "✓ requirements.txt unchanged, skipping pip install"
fi
```

## Test Strategy

- 本PR マージ時: requirements.txt 変更ありなので通常どおり pip install 実行
- 次回以降の軽微な修正コミット: pip install スキップされ deploy が 40秒程度短縮
- GitHub Actions のログに「✓ requirements.txt unchanged, skipping pip install」が出力されれば成功

## Risk Assessment

- **破壊的変更**: なし（初回は従来と同じパス）
- **ロールバック**: ワークフローを revert するだけで元通り
- **副作用**: venv が壊れた場合に自己回復しない可能性 → VM 上で `rm -rf venv/.requirements.sha256` すれば次回再インストール
