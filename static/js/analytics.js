// 学習分析ダッシュボード

const AnalyticsDashboard = () => {
    const [overview, setOverview] = React.useState(null);
    const [skillProgression, setSkillProgression] = React.useState(null);
    const [scenarioPerformance, setScenarioPerformance] = React.useState(null);
    const [comparison, setComparison] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [selectedDays, setSelectedDays] = React.useState(30);
    const [activeTab, setActiveTab] = React.useState('overview');

    // データ取得
    React.useEffect(() => {
        fetchAnalyticsData();
    }, [selectedDays]);

    const fetchAnalyticsData = async () => {
        setLoading(true);
        try {
            // 概要データ
            const overviewRes = await fetch('/api/analytics/overview');
            const overviewData = await overviewRes.json();
            if (overviewData.success) {
                setOverview(overviewData.data);
            }

            // スキル進捗データ
            const progressionRes = await fetch(`/api/analytics/skill-progression?days=${selectedDays}`);
            const progressionData = await progressionRes.json();
            if (progressionData.success) {
                setSkillProgression(progressionData.data);
            }

            // シナリオパフォーマンス
            const scenarioRes = await fetch('/api/analytics/scenario-performance');
            const scenarioData = await scenarioRes.json();
            if (scenarioData.success) {
                setScenarioPerformance(scenarioData.data);
            }

            // 比較分析
            const comparisonRes = await fetch('/api/analytics/comparative-analysis');
            const comparisonData = await comparisonRes.json();
            if (comparisonData.success) {
                setComparison(comparisonData.data);
            }
        } catch (error) {
            console.error('Analytics data fetch error:', error);
            showNotification('分析データの取得に失敗しました', 'error');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="analytics-loading">
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-3">分析データを読み込んでいます...</p>
            </div>
        );
    }

    return (
        <div className="analytics-dashboard">
            <div className="dashboard-header">
                <h2>学習成果ダッシュボード</h2>
                <div className="time-filter">
                    <label>期間: </label>
                    <select 
                        value={selectedDays} 
                        onChange={(e) => setSelectedDays(Number(e.target.value))}
                        className="form-select form-select-sm d-inline-block w-auto"
                    >
                        <option value={7}>過去7日間</option>
                        <option value={30}>過去30日間</option>
                        <option value={90}>過去90日間</option>
                        <option value={180}>過去180日間</option>
                    </select>
                </div>
            </div>

            <ul className="nav nav-tabs mb-4">
                <li className="nav-item">
                    <a 
                        className={`nav-link ${activeTab === 'overview' ? 'active' : ''}`}
                        onClick={() => setActiveTab('overview')}
                        href="#"
                    >
                        概要
                    </a>
                </li>
                <li className="nav-item">
                    <a 
                        className={`nav-link ${activeTab === 'skills' ? 'active' : ''}`}
                        onClick={() => setActiveTab('skills')}
                        href="#"
                    >
                        スキル分析
                    </a>
                </li>
                <li className="nav-item">
                    <a 
                        className={`nav-link ${activeTab === 'scenarios' ? 'active' : ''}`}
                        onClick={() => setActiveTab('scenarios')}
                        href="#"
                    >
                        シナリオ分析
                    </a>
                </li>
                <li className="nav-item">
                    <a 
                        className={`nav-link ${activeTab === 'comparison' ? 'active' : ''}`}
                        onClick={() => setActiveTab('comparison')}
                        href="#"
                    >
                        比較分析
                    </a>
                </li>
            </ul>

            <div className="tab-content">
                {activeTab === 'overview' && <OverviewTab data={overview} />}
                {activeTab === 'skills' && <SkillsTab data={skillProgression} />}
                {activeTab === 'scenarios' && <ScenariosTab data={scenarioPerformance} />}
                {activeTab === 'comparison' && <ComparisonTab data={comparison} />}
            </div>
        </div>
    );
};

// 概要タブコンポーネント
const OverviewTab = ({ data }) => {
    if (!data) return null;

    const formatTime = (minutes) => {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return hours > 0 ? `${hours}時間${mins}分` : `${mins}分`;
    };

    return (
        <div className="overview-tab">
            <div className="row">
                <div className="col-md-3 mb-4">
                    <div className="stat-card">
                        <h5>総セッション数</h5>
                        <div className="stat-value">{data.total_sessions}</div>
                        <small className="text-muted">回</small>
                    </div>
                </div>
                <div className="col-md-3 mb-4">
                    <div className="stat-card">
                        <h5>総練習時間</h5>
                        <div className="stat-value">{formatTime(data.total_practice_time)}</div>
                    </div>
                </div>
                <div className="col-md-6 mb-4">
                    <div className="recommendation-card">
                        <h5>おすすめの次のステップ</h5>
                        <p>{data.recommendation?.message}</p>
                        {data.recommendation?.skill_focus && (
                            <span className="badge bg-primary">
                                {data.recommendation.skill_focus}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {data.skill_summary && data.skill_summary.current_scores && (
                <div className="current-skills-overview">
                    <h4>現在のスキルレベル</h4>
                    <div className="row">
                        {Object.entries(data.skill_summary.current_scores).map(([skill, score]) => (
                            <div key={skill} className="col-md-4 mb-3">
                                <div className="skill-card">
                                    <h6>{getSkillName(skill)}</h6>
                                    <div className="progress">
                                        <div 
                                            className="progress-bar"
                                            style={{width: `${score}%`}}
                                            role="progressbar"
                                            aria-valuenow={score}
                                            aria-valuemin="0"
                                            aria-valuemax="100"
                                        >
                                            {score}点
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {data.recent_activity && data.recent_activity.length > 0 && (
                <div className="recent-activity mt-4">
                    <h4>最近のアクティビティ</h4>
                    <div className="activity-list">
                        {data.recent_activity.map((activity, index) => (
                            <div key={index} className="activity-item">
                                <span className="activity-date">
                                    {new Date(activity.date).toLocaleDateString('ja-JP')}
                                </span>
                                <span className="activity-type badge bg-secondary ms-2">
                                    {activity.session_type === 'scenario' ? 'シナリオ練習' : '雑談練習'}
                                </span>
                                {activity.scenario_id && (
                                    <span className="activity-scenario ms-2">
                                        {activity.scenario_id}
                                    </span>
                                )}
                                <span className="activity-messages ms-2 text-muted">
                                    {activity.message_count}メッセージ
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// スキル分析タブコンポーネント
const SkillsTab = ({ data }) => {
    const [selectedSkill, setSelectedSkill] = React.useState(null);
    const [skillDetails, setSkillDetails] = React.useState(null);
    const [loadingDetails, setLoadingDetails] = React.useState(false);
    const chartRef = React.useRef(null);
    const chartInstance = React.useRef(null);

    if (!data) return null;

    // チャートの初期化と更新
    React.useEffect(() => {
        if (data.skill_trends && chartRef.current) {
            const ctx = chartRef.current.getContext('2d');
            
            // 既存のチャートを破棄
            if (chartInstance.current) {
                chartInstance.current.destroy();
            }

            // データセットの準備
            const datasets = [];
            const allDates = new Set();

            Object.entries(data.skill_trends).forEach(([skill, dataPoints]) => {
                dataPoints.forEach(point => allDates.add(point.date));
                
                const skillData = Array.from(allDates).sort().map(date => {
                    const point = dataPoints.find(p => p.date === date);
                    return point ? point.score : null;
                });

                datasets.push({
                    label: getSkillName(skill),
                    data: skillData,
                    borderColor: getSkillColor(skill),
                    backgroundColor: getSkillColor(skill, 0.1),
                    tension: 0.3,
                    spanGaps: true
                });
            });

            // チャートの作成
            chartInstance.current = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array.from(allDates).sort().map(date => 
                        new Date(date).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' })
                    ),
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'スキル成長推移'
                        },
                        legend: {
                            position: 'bottom'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '点';
                                }
                            }
                        }
                    }
                }
            });
        }

        // クリーンアップ
        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
            }
        };
    }, [data]);

    const fetchSkillDetails = async (skill) => {
        setLoadingDetails(true);
        try {
            const res = await fetch(`/api/analytics/skill/${skill}/progress?days=30`);
            const result = await res.json();
            if (result.success) {
                setSkillDetails(result.data);
                setSelectedSkill(skill);
            }
        } catch (error) {
            console.error('Skill details fetch error:', error);
        } finally {
            setLoadingDetails(false);
        }
    };

    return (
        <div className="skills-tab">
            <div className="row">
                <div className="col-md-8">
                    <h4>スキル成長率</h4>
                    <div className="growth-rates">
                        {Object.entries(data.growth_rates || {}).map(([skill, rate]) => (
                            <div key={skill} className="growth-item mb-3">
                                <div className="d-flex justify-content-between align-items-center">
                                    <span className="skill-name">
                                        {getSkillName(skill)}
                                    </span>
                                    <span className={`growth-rate badge ${
                                        rate > 0 ? 'bg-success' : rate < 0 ? 'bg-danger' : 'bg-secondary'
                                    }`}>
                                        {rate > 0 ? '+' : ''}{rate}%
                                    </span>
                                </div>
                                <button 
                                    className="btn btn-sm btn-outline-primary mt-2"
                                    onClick={() => fetchSkillDetails(skill)}
                                >
                                    詳細を見る
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="col-md-4">
                    <h4>分析情報</h4>
                    <div className="analysis-info">
                        <p><strong>分析期間:</strong> {data.period?.days}日間</p>
                        <p><strong>分析回数:</strong> {data.total_analyses}回</p>
                    </div>
                </div>
            </div>

            {/* スキル成長推移チャート */}
            {data.skill_trends && (
                <div className="chart-container mt-4">
                    <div className="card">
                        <div className="card-body">
                            <div style={{height: '400px'}}>
                                <canvas ref={chartRef}></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {selectedSkill && skillDetails && (
                <div className="skill-details-modal mt-4">
                    <div className="card">
                        <div className="card-header">
                            <h5>{getSkillName(selectedSkill)}の詳細分析</h5>
                            <button 
                                className="btn-close float-end"
                                onClick={() => setSelectedSkill(null)}
                            ></button>
                        </div>
                        <div className="card-body">
                            {loadingDetails ? (
                                <div className="text-center">
                                    <div className="spinner-border" role="status">
                                        <span className="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                            ) : (
                                <SkillDetailView data={skillDetails} />
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

// スキル詳細ビューコンポーネント
const SkillDetailView = ({ data }) => {
    return (
        <div className="skill-detail-view">
            <div className="row">
                <div className="col-md-6">
                    <h6>統計情報</h6>
                    <table className="table table-sm">
                        <tbody>
                            <tr>
                                <td>平均スコア:</td>
                                <td>{data.statistics?.mean}点</td>
                            </tr>
                            <tr>
                                <td>最高スコア:</td>
                                <td>{data.statistics?.max}点</td>
                            </tr>
                            <tr>
                                <td>最低スコア:</td>
                                <td>{data.statistics?.min}点</td>
                            </tr>
                            <tr>
                                <td>標準偏差:</td>
                                <td>{data.statistics?.std_dev}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div className="col-md-6">
                    <h6>トレンド分析</h6>
                    <p>方向性: <span className="badge bg-info">{data.trend?.direction}</span></p>
                    <p>最近の変化: {data.trend?.recent_change}点</p>
                </div>
            </div>

            {data.improvement_suggestions && (
                <div className="suggestions mt-3">
                    <h6>改善提案</h6>
                    <ul>
                        {data.improvement_suggestions.map((suggestion, index) => (
                            <li key={index}>{suggestion}</li>
                        ))}
                    </ul>
                </div>
            )}

            {data.milestones && data.milestones.length > 0 && (
                <div className="milestones mt-3">
                    <h6>達成記録</h6>
                    {data.milestones.map((milestone, index) => (
                        <div key={index} className="milestone-item">
                            <span className="milestone-date">
                                {new Date(milestone.date).toLocaleDateString('ja-JP')}
                            </span>
                            <span className="milestone-achievement ms-2">
                                {milestone.achievement}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// シナリオ分析タブコンポーネント
const ScenariosTab = ({ data }) => {
    if (!data) return null;

    const getScenarioName = (scenarioId) => {
        // シナリオIDから名前を取得（実際のマッピングは別途実装）
        return scenarioId;
    };

    return (
        <div className="scenarios-tab">
            <div className="row">
                <div className="col-md-6">
                    <h4>最も練習したシナリオ</h4>
                    <div className="scenario-list">
                        {data.most_practiced?.map((scenarioId, index) => (
                            <div key={index} className="scenario-item">
                                <span className="rank">{index + 1}.</span>
                                <span className="scenario-name">
                                    {getScenarioName(scenarioId)}
                                </span>
                                <span className="practice-count badge bg-primary ms-2">
                                    {data.scenarios[scenarioId]?.count || 0}回
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="col-md-6">
                    <h4>パフォーマンスが高いシナリオ</h4>
                    <div className="scenario-list">
                        {data.best_performing?.map((scenarioId, index) => (
                            <div key={index} className="scenario-item">
                                <span className="rank">{index + 1}.</span>
                                <span className="scenario-name">
                                    {getScenarioName(scenarioId)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {data.recommendations && data.recommendations.length > 0 && (
                <div className="scenario-recommendations mt-4">
                    <h4>推奨シナリオ</h4>
                    <div className="row">
                        {data.recommendations.slice(0, 3).map((scenarioId, index) => (
                            <div key={index} className="col-md-4">
                                <div className="recommendation-card">
                                    <h6>{getScenarioName(scenarioId)}</h6>
                                    <button className="btn btn-primary btn-sm mt-2">
                                        このシナリオで練習
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// 比較分析タブコンポーネント
const ComparisonTab = ({ data }) => {
    if (!data || data.error) {
        return (
            <div className="comparison-tab">
                <p className="text-muted">比較分析データがまだありません。</p>
            </div>
        );
    }

    return (
        <div className="comparison-tab">
            <div className="comparison-info mb-4">
                <p>
                    <strong>分析対象:</strong> {data.total_users}人のユーザー
                    <span className="ms-3">
                        <strong>期間:</strong> {data.analysis_period}
                    </span>
                </p>
            </div>

            <h4>スキル別の相対的位置</h4>
            <div className="skill-comparison">
                {Object.entries(data.comparison || {}).map(([skill, stats]) => (
                    <div key={skill} className="comparison-item mb-3">
                        <h6>{getSkillName(skill)}</h6>
                        <div className="comparison-stats">
                            <div className="row align-items-center">
                                <div className="col-md-6">
                                    <div className="percentile-bar">
                                        <div className="percentile-label">
                                            上位 {100 - stats.percentile}%
                                        </div>
                                        <div className="progress">
                                            <div 
                                                className="progress-bar bg-success"
                                                style={{width: `${stats.percentile}%`}}
                                                role="progressbar"
                                            >
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-md-6">
                                    <small className="text-muted">
                                        あなた: {stats.user_score}点 / 
                                        平均: {stats.average}点
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="row mt-4">
                <div className="col-md-6">
                    <h5>相対的な強み</h5>
                    <ul className="strengths-list">
                        {data.strengths?.map((skill, index) => (
                            <li key={index}>{getSkillName(skill)}</li>
                        ))}
                    </ul>
                </div>
                <div className="col-md-6">
                    <h5>改善の余地がある領域</h5>
                    <ul className="improvement-list">
                        {data.areas_for_improvement?.map((skill, index) => (
                            <li key={index}>{getSkillName(skill)}</li>
                        ))}
                    </ul>
                </div>
            </div>
        </div>
    );
};

// ヘルパー関数
const getSkillName = (skill) => {
    const skillNames = {
        'empathy': '共感力',
        'clarity': '明確性',
        'active_listening': '傾聴力',
        'adaptability': '適応力',
        'positivity': '前向きさ',
        'professionalism': 'プロフェッショナリズム'
    };
    return skillNames[skill] || skill;
};

// スキルごとの色を取得
const getSkillColor = (skill, alpha = 1) => {
    const colors = {
        'empathy': `rgba(255, 99, 132, ${alpha})`,      // 赤
        'clarity': `rgba(54, 162, 235, ${alpha})`,      // 青
        'active_listening': `rgba(255, 206, 86, ${alpha})`,  // 黄
        'adaptability': `rgba(75, 192, 192, ${alpha})`,  // 緑
        'positivity': `rgba(153, 102, 255, ${alpha})`,   // 紫
        'professionalism': `rgba(255, 159, 64, ${alpha})` // オレンジ
    };
    return colors[skill] || `rgba(201, 203, 207, ${alpha})`; // デフォルト: 灰色
};

// 通知表示
const showNotification = (message, type = 'info') => {
    const alertClass = {
        'info': 'alert-info',
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning'
    }[type] || 'alert-info';

    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    const container = document.getElementById('notification-container') || document.body;
    const alertElement = document.createElement('div');
    alertElement.innerHTML = alertHtml;
    container.appendChild(alertElement.firstElementChild);

    // 5秒後に自動的に削除
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
};

// エクスポート
window.AnalyticsDashboard = AnalyticsDashboard;