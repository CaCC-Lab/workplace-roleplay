# Bugfix: test_security_fixed.py の PytestReturnNotNoneWarning 5件

## Current Behavior（現在の動作）

`tests/test_security_fixed.py` の5つのテスト関数が `return True` しており、pytest実行時に `PytestReturnNotNoneWarning` が5件発生する。

対象関数:
1. `test_security_utils` (L59)
2. `test_csrf_protection` (L77)
3. `test_rate_limiter` (L101)
4. `test_feature_flags` (L121)
5. `test_ab_routes_integration` (L150)

このファイルはスクリプト兼テストとして設計されており、`main()` から各関数を呼び出して `return True/False` で結果判定するパスと、pytestから呼び出されるパスが共存している。pytest実行時は `return` の値が無視されるだけで検証には影響しないが、全テストスイートのwarning 13件中5件を占めノイズになっている。

また `test_ab_routes_integration` はテスト内で `if response.status_code == 200` と条件分岐しており、失敗時もテストがpassする（assertで検証していない）。

## Expected Behavior（期待する動作）

- 5つのテスト関数から `return True` を削除
- `test_ab_routes_integration` の条件分岐を `assert` に変更
- `main()` の呼び出しは `return` 値に依存しているため、代替として各関数呼び出しをtry/exceptのみで判定するよう修正
- PytestReturnNotNoneWarning が0件になる

## Unchanged Behavior（変更しない動作）

- 各テスト関数内の `assert` 文による検証ロジックは変更しない
- `__main__` 実行時のスクリプト動作は維持する（成功/失敗のサマリー出力）
- 他のテストファイルに影響を与えない
