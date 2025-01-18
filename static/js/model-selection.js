document.addEventListener('DOMContentLoaded', function() {
    // ページ読み込み時に最初のモデルを保存
    const modelSelect = document.getElementById('model-select');
    if (modelSelect && modelSelect.value) {
        localStorage.setItem('selectedModel', modelSelect.value);
    }

    // モデル選択時の保存
    modelSelect.addEventListener('change', function() {
        const selectedModel = this.value;
        localStorage.setItem('selectedModel', selectedModel);
    });
}); 