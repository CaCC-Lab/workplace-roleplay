document.addEventListener('DOMContentLoaded', function() {
    const modelSelect = document.getElementById('model-select');
    const modelSelectContainer = document.querySelector('.model-select');

    // Geminiモデルのリスト
    let geminiModels = [];

    // APIからモデル一覧を取得
    fetch('/api/models')
        .then(response => response.json())
        .then(data => {
            // Geminiモデルを取得
            data.models.forEach(model => {
                // modelはオブジェクト形式 {id: "gemini/...", name: "...", provider: "gemini"}
                if (typeof model === 'object' && model.id && model.id.startsWith('gemini/')) {
                    geminiModels.push({
                        value: model.id,
                        label: model.name || model.id.replace('gemini/', '')
                    });
                } else if (typeof model === 'string' && model.startsWith('gemini/')) {
                    // 旧形式の互換性のため
                    geminiModels.push({
                        value: model,
                        label: model.replace('gemini/', '')
                    });
                }
            });

            // モデルリストを更新
            updateModelSelect();
            modelSelectContainer.style.display = 'flex';
            
            // 保存された選択を復元するか、デフォルト値を設定
            const savedModel = localStorage.getItem('selectedModel');
            
            if (savedModel && geminiModels.some(model => model.value === savedModel)) {
                modelSelect.value = savedModel;
            } else {
                // デフォルトでgemini-1.5-flashを選択
                const defaultModel = 'gemini/gemini-1.5-flash';
                const defaultModelExists = geminiModels.some(model => model.value === defaultModel);
                
                if (defaultModelExists) {
                    modelSelect.value = defaultModel;
                } else if (geminiModels.length > 0) {
                    // なければ最初のモデルを選択
                    modelSelect.value = geminiModels[0].value;
                }
                
                // 選択を保存
                if (modelSelect.value) {
                    localStorage.setItem('selectedModel', modelSelect.value);
                }
            }
        })
        .catch(error => {
            handleError(error);
            console.error('Failed to fetch models:', error);
        });


    // モデル選択時の処理
    modelSelect.addEventListener('change', function() {
        const selectedModel = this.value;
        localStorage.setItem('selectedModel', selectedModel);
    });

    // モデル選択の更新
    function updateModelSelect() {
        // 既存のオプションをクリア
        modelSelect.innerHTML = '';
        
        // Geminiモデルを追加
        geminiModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.value;
            option.textContent = model.label;
            modelSelect.appendChild(option);
        });
    }

    // エラーハンドリング
    function handleError(error) {
        console.error('Error in model selection:', error);
        const errorMessage = document.createElement('div');
        errorMessage.className = 'error-message';
        errorMessage.textContent = 'モデル一覧の取得に失敗しました。ページを更新してください。';
        modelSelectContainer.appendChild(errorMessage);
    }
}); 