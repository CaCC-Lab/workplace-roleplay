document.addEventListener('DOMContentLoaded', function() {
    const modelSelect = document.getElementById('model-select');
    const modelSelectContainer = document.querySelector('.model-select');
    const modelSelectionSection = document.getElementById('model-selection-section');
    const learningHistoryCard = document.getElementById('learning-history-card');
    const strengthAnalysisCard = document.getElementById('strength-analysis-card');

    // Geminiモデルのリスト
    let geminiModels = [];
    
    // 機能フラグを取得
    fetch('/api/feature_flags')
        .then(response => response.json())
        .then(flags => {
            // UIの条件表示
            if (flags.model_selection && modelSelectionSection) {
                modelSelectionSection.style.display = 'block';
            }
            if (flags.learning_history && learningHistoryCard) {
                learningHistoryCard.style.display = 'block';
            }
            if (flags.strength_analysis && strengthAnalysisCard) {
                strengthAnalysisCard.style.display = 'block';
            }
            
            // モデル選択が無効の場合はデフォルトモデルを使用
            if (!flags.model_selection && flags.default_model) {
                localStorage.setItem('selectedModel', flags.default_model);
            }
        })
        .catch(err => {
            console.error('Failed to load feature flags:', err);
            // エラー時はデフォルトで表示
            if (modelSelectionSection) modelSelectionSection.style.display = 'block';
            if (learningHistoryCard) learningHistoryCard.style.display = 'block';
            if (strengthAnalysisCard) strengthAnalysisCard.style.display = 'block';
        });

    // APIからモデル一覧を取得
    fetch('/api/models')
        .then(response => response.json())
        .then(data => {
            // Geminiモデルを取得
            data.models.forEach(model => {
                // modelはオブジェクト形式 {id: "...", name: "...", provider: "..."}
                if (model.id && model.id.startsWith('gemini/')) {
                    geminiModels.push({
                        value: model.id,
                        label: model.name || model.id.replace('gemini/', '')
                    });
                } else if (typeof model === 'string' && model.startsWith('gemini/')) {
                    // 後方互換性のため文字列形式もサポート
                    geminiModels.push({
                        value: model,
                        label: model.replace('gemini/', '')
                    });
                }
            });

            // モデルリストを更新
            updateModelSelect();
            
            // modelSelectContainerが存在する場合のみ表示
            if (modelSelectContainer) {
                modelSelectContainer.style.display = 'flex';
            }
            
            // 保存された選択を復元するか、デフォルト値を設定
            const savedModel = localStorage.getItem('selectedModel');
            
            // modelSelectが存在する場合のみ値を設定
            if (modelSelect) {
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
            }
        })
        .catch(error => {
            handleError(error);
            console.error('Failed to fetch models:', error);
        });


    // モデル選択時の処理（要素が存在する場合のみ）
    if (modelSelect) {
        modelSelect.addEventListener('change', function() {
            const selectedModel = this.value;
            localStorage.setItem('selectedModel', selectedModel);
        });
    }

    // モデル選択の更新
    function updateModelSelect() {
        // modelSelectが存在しない場合は何もしない
        if (!modelSelect) {
            return;
        }
        
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
        
        // modelSelectContainerが存在しない場合は何もしない
        if (!modelSelectContainer) {
            return;
        }
        
        const errorMessage = document.createElement('div');
        errorMessage.className = 'error-message';
        errorMessage.textContent = 'モデル一覧の取得に失敗しました。ページを更新してください。';
        modelSelectContainer.appendChild(errorMessage);
    }
}); 