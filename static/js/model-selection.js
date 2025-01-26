document.addEventListener('DOMContentLoaded', function() {
    const providerSelect = document.getElementById('provider-select');
    const modelSelect = document.getElementById('model-select');
    const modelSelectContainer = document.querySelector('.model-select');

    // モデルのグループ化用のオブジェクト
    let modelGroups = {
        gemini: [],
        openai: [],
        local: []
    };

    // APIからモデル一覧を取得
    fetch('/api/models')
        .then(response => response.json())
        .then(data => {
            // モデルをグループ化
            data.models.forEach(model => {
                if (model.startsWith('gemini/')) {
                    modelGroups.gemini.push({
                        value: model,
                        label: model.replace('gemini/', '')
                    });
                } else if (model.startsWith('openai/')) {
                    modelGroups.openai.push({
                        value: model,
                        label: model.replace('openai/', '')
                    });
                } else {
                    modelGroups.local.push({
                        value: model,
                        label: model
                    });
                }
            });

            // 保存された選択を復元
            const savedProvider = localStorage.getItem('selectedProvider');
            const savedModel = localStorage.getItem('selectedModel');
            
            if (savedProvider) {
                providerSelect.value = savedProvider;
                updateModelSelect(savedProvider);
                modelSelectContainer.style.display = 'block';
                
                if (savedModel) {
                    modelSelect.value = savedModel;
                }
            }
        })
        .catch(error => {
            handleError(error);
            console.error('Failed to fetch models:', error);
        });

    // プロバイダー選択時の処理
    providerSelect.addEventListener('change', function() {
        const selectedProvider = this.value;
        localStorage.setItem('selectedProvider', selectedProvider);
        
        updateModelSelect(selectedProvider);
        modelSelectContainer.style.display = 'block';
        
        // 最初のモデルを自動選択
        if (modelSelect.options.length > 0) {
            modelSelect.selectedIndex = 0;
            localStorage.setItem('selectedModel', modelSelect.value);
        }
    });

    // モデル選択時の処理
    modelSelect.addEventListener('change', function() {
        const selectedModel = this.value;
        localStorage.setItem('selectedModel', selectedModel);
    });

    // モデル選択の更新
    function updateModelSelect(provider) {
        // 既存のオプションをクリア
        modelSelect.innerHTML = '';
        
        // 選択されたプロバイダーのモデルを追加
        const models = modelGroups[provider] || [];
        models.forEach(model => {
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