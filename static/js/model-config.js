// モデル設定の管理
// サーバー側で環境変数から読み取ったデフォルトモデルを使用するため、
// クライアント側では明示的にモデルを指定しない

function getSelectedModel() {
    // 常にnullを返し、サーバー側でデフォルトモデルを使用させる
    return null;
}

// 後方互換性のために空の関数を定義
function saveSelectedModel(model) {
    // 何もしない - モデル選択はサーバー側で管理
}