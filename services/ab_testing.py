"""
A/Bテストフレームワーク

機能の価値検証と最適化のためのA/Bテストシステム
"""
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
from flask import current_app
import redis

from models import db

logger = logging.getLogger(__name__)


@dataclass
class ExperimentVariant:
    """A/Bテストのバリアント定義"""
    name: str
    description: str
    config: Dict[str, Any]
    weight: float = 1.0  # 割り当ての重み


@dataclass
class Experiment:
    """A/Bテストの定義"""
    name: str
    description: str
    variants: List[ExperimentVariant]
    metrics: List[str]
    start_date: datetime
    end_date: Optional[datetime] = None
    target_sample_size: int = 1000
    active: bool = True


@dataclass
class ExperimentConfig:
    """A/Bテスト設定（テスト用）"""
    name: str
    control_percentage: float
    enabled: bool
    start_date: datetime
    end_date: Optional[datetime] = None


class ExperimentationFramework:
    """
A/Bテストと機能フラグの管理
    """
    
    def __init__(self):
        # Redisはオプション、接続できなくてもエラーにしない
        self.redis_client = None
        try:
            self.redis_client = self._get_redis_client()
            # Redisに接続してping送信してみる
            if self.redis_client:
                self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory fallback: {e}")
            self.redis_client = None
        
        self.experiments = self._initialize_experiments()
        self.metrics_buffer = defaultdict(list)  # メトリクスのバッファ
        self.user_assignments = {}  # テスト用のユーザー割り当て記録
        self.metrics = []  # テスト用のメトリクス記録
    
    def _get_redis_client(self):
        """Redisクライアントを取得"""
        try:
            from config.config import get_config
            config = get_config()
            return redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB + 1,  # A/Bテスト用に別のDBを使用
                decode_responses=True
            )
        except Exception as e:
            current_app.logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
            return None
    
    def _initialize_experiments(self) -> Dict[str, Experiment]:
        """実験の初期化"""
        experiments = {}
        
        # リアルタイムコーチング実験
        realtime_coaching_variants = [
            ExperimentVariant(
                name='control',
                description='コーチングなし（コントロール）',
                config={'coaching_enabled': False},
                weight=0.3
            ),
            ExperimentVariant(
                name='basic_hints',
                description='基本ヒントのみ',
                config={
                    'coaching_enabled': True, 
                    'hint_level': 'basic',
                    'hint_frequency': 'normal'
                },
                weight=0.4
            ),
            ExperimentVariant(
                name='advanced_hints',
                description='高度なヒントとリアルタイムフィードバック',
                config={
                    'coaching_enabled': True, 
                    'hint_level': 'advanced',
                    'hint_frequency': 'high',
                    'realtime_feedback': True
                },
                weight=0.3
            )
        ]
        
        experiments['realtime_coaching'] = Experiment(
            name='realtime_coaching',
            description='リアルタイムコーチング機能の効果検証',
            variants=realtime_coaching_variants,
            metrics=[
                'session_completion_rate',
                'skill_improvement_rate', 
                'user_satisfaction_score',
                'hint_interaction_rate',
                'session_duration',
                'message_score',
                'hint_acceptance_rate'
            ],
            start_date=datetime.utcnow(),
            target_sample_size=500
        )
        
        # 未来の実験のためのテンプレート
        experiments['ui_redesign'] = Experiment(
            name='ui_redesign',
            description='UIリデザインの効果検証',
            variants=[
                ExperimentVariant(
                    name='current_ui',
                    description='現在のUI',
                    config={'ui_version': 'current'},
                    weight=0.5
                ),
                ExperimentVariant(
                    name='new_ui',
                    description='新しいUIデザイン',
                    config={'ui_version': 'new'},
                    weight=0.5
                )
            ],
            metrics=['user_engagement', 'task_completion_rate'],
            start_date=datetime.utcnow() + timedelta(days=30),
            active=False
        )
        
        return experiments
    
    def assign_variant(self, user_id: int, experiment_name: str) -> Dict[str, Any]:
        """
        ユーザーにA/Bテストのバリアントを割り当て
        
        Args:
            user_id: ユーザーID
            experiment_name: 実験名
            
        Returns:
            割り当てられたバリアントの設定
        """
        # 既に割り当てがあるかチェック
        cache_key = f"variant:{experiment_name}:{user_id}"
        if self.redis_client:
            try:
                cached_variant = self.redis_client.get(cache_key)
                if cached_variant:
                    return json.loads(cached_variant)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        experiment = self.experiments.get(experiment_name)
        if not experiment or not experiment.active:
            # 実験が非アクティブの場合はデフォルトを返す
            return self._get_default_config(experiment_name)
        
        # 一貫性のあるバリアント割り当て
        hash_input = f"{user_id}:{experiment_name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        # 重みづけされたランダム選択
        total_weight = sum(v.weight for v in experiment.variants)
        normalized_hash = (hash_value % 10000) / 10000.0  # 0.0-1.0の範囲
        
        cumulative_weight = 0
        selected_variant = experiment.variants[0]  # フォールバック
        
        for variant in experiment.variants:
            cumulative_weight += variant.weight / total_weight
            if normalized_hash <= cumulative_weight:
                selected_variant = variant
                break
        
        # 結果をキャッシュ
        variant_config = {
            'name': selected_variant.name,
            'experiment': experiment_name,
            **selected_variant.config
        }
        
        if self.redis_client:
            try:
                # 24時間キャッシュ
                self.redis_client.setex(cache_key, 86400, json.dumps(variant_config))
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        # 割り当てを記録
        self._record_assignment(user_id, experiment_name, selected_variant.name)
        
        return variant_config
    
    def _get_default_config(self, experiment_name: str) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        defaults = {
            'realtime_coaching': {
                'name': 'control',
                'experiment': experiment_name,
                'coaching_enabled': False
            },
            'ui_redesign': {
                'name': 'current_ui',
                'experiment': experiment_name,
                'ui_version': 'current'
            }
        }
        return defaults.get(experiment_name, {'name': 'default'})
    
    def track_metric(self, user_id: int, metric_name: str, value: float, 
                    experiment_name: str = None, metadata: Dict[str, Any] = None):
        """
        メトリクスを記録
        
        Args:
            user_id: ユーザーID
            metric_name: メトリクス名
            value: 値
            experiment_name: 実験名（省略時は自動推定）
            metadata: 追加メタデータ
        """
        timestamp = datetime.utcnow()
        
        # 実験名が指定されていない場合は、関連する実験を推定
        if not experiment_name:
            experiment_name = self._infer_experiment_from_metric(metric_name)
        
        if not experiment_name:
            current_app.logger.warning(f"Could not infer experiment for metric: {metric_name}")
            return
        
        # ユーザーのバリアントを取得
        variant_config = self.get_user_variant(user_id, experiment_name)
        if not variant_config:
            return
        
        metric_data = {
            'user_id': user_id,
            'experiment': experiment_name,
            'variant': variant_config['name'],
            'metric': metric_name,
            'value': value,
            'timestamp': timestamp.isoformat(),
            'metadata': metadata or {}
        }
        
        # Redisに記録
        if self.redis_client:
            try:
                metric_key = f"metrics:{experiment_name}:{metric_name}:{timestamp.strftime('%Y%m%d')}"
                self.redis_client.lpush(metric_key, json.dumps(metric_data))
                # 30日間保存
                self.redis_client.expire(metric_key, 86400 * 30)
            except Exception as e:
                logger.warning(f"Redis metric tracking failed: {e}")
        
        # バッファに追加（即座解析用）
        buffer_key = f"{experiment_name}:{metric_name}"
        self.metrics_buffer[buffer_key].append(metric_data)
        
        # バッファのサイズ制限
        if len(self.metrics_buffer[buffer_key]) > 1000:
            self.metrics_buffer[buffer_key] = self.metrics_buffer[buffer_key][-500:]
        
        # テスト用にメトリクスをリストに追加
        self.metrics.append({
            'user_id': user_id,
            'metric_name': metric_name,
            'value': value,
            'experiment': experiment_name
        })
    
    def _infer_experiment_from_metric(self, metric_name: str) -> Optional[str]:
        """メトリクス名から実験を推定"""
        metric_to_experiment = {
            'hint_acceptance_rate': 'realtime_coaching',
            'hint_interaction_rate': 'realtime_coaching',
            'message_score': 'realtime_coaching',
            'session_duration': 'realtime_coaching',
            'user_engagement': 'ui_redesign',
            'task_completion_rate': 'ui_redesign'
        }
        return metric_to_experiment.get(metric_name)
    
    def get_user_variant(self, user_id: int, experiment_name: str) -> Optional[Dict[str, Any]]:
        """
        ユーザーのバリアントを取得
        
        Args:
            user_id: ユーザーID
            experiment_name: 実験名
            
        Returns:
            ユーザーのバリアント設定、またはNone
        """
        cache_key = f"variant:{experiment_name}:{user_id}"
        if self.redis_client:
            cached_variant = self.redis_client.get(cache_key)
            if cached_variant:
                return json.loads(cached_variant)
        
        return None
    
    def _record_assignment(self, user_id: int, experiment_name: str, variant_name: str):
        """バリアント割り当てを記録"""
        if not self.redis_client:
            return
        
        assignment_data = {
            'user_id': user_id,
            'experiment': experiment_name,
            'variant': variant_name,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        assignment_key = f"assignments:{experiment_name}:{datetime.utcnow().strftime('%Y%m%d')}"
        self.redis_client.lpush(assignment_key, json.dumps(assignment_data))
        self.redis_client.expire(assignment_key, 86400 * 90)  # 90日間保存
    
    def get_experiment_results(self, experiment_name: str, days: int = 7) -> Dict[str, Any]:
        """
        実験結果の集計と分析
        
        Args:
            experiment_name: 実験名
            days: 分析期間（日数）
            
        Returns:
            実験結果の分析
        """
        experiment = self.experiments.get(experiment_name)
        if not experiment:
            return {'error': f'Experiment {experiment_name} not found'}
        
        results = {
            'experiment': experiment_name,
            'period_days': days,
            'variants': {},
            'statistical_significance': {},
            'recommendations': []
        }
        
        # 各バリアントのメトリクスを集計
        for variant in experiment.variants:
            variant_metrics = self._aggregate_variant_metrics(
                experiment_name, variant.name, experiment.metrics, days
            )
            results['variants'][variant.name] = variant_metrics
        
        # 統計的有意性の計算
        for metric in experiment.metrics:
            significance = self._calculate_statistical_significance(
                results['variants'], metric
            )
            results['statistical_significance'][metric] = significance
        
        # 推奨事項の生成
        results['recommendations'] = self._generate_recommendations(
            results['variants'], results['statistical_significance']
        )
        
        return results
    
    def _aggregate_variant_metrics(self, experiment_name: str, variant_name: str, 
                                  metrics: List[str], days: int) -> Dict[str, Any]:
        """バリアントのメトリクスを集計"""
        variant_data = {
            'sample_size': 0,
            'metrics': {}
        }
        
        if not self.redis_client:
            return variant_data
        
        # 指定期間のデータを収集
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        all_data_points = []
        
        for metric in metrics:
            for day_offset in range(days):
                date = start_date + timedelta(days=day_offset)
                date_str = date.strftime('%Y%m%d')
                metric_key = f"metrics:{experiment_name}:{metric}:{date_str}"
                
                # Redisからデータを取得
                raw_data = self.redis_client.lrange(metric_key, 0, -1)
                
                for data_json in raw_data:
                    try:
                        data_point = json.loads(data_json)
                        if data_point['variant'] == variant_name:
                            all_data_points.append(data_point)
                    except json.JSONDecodeError:
                        continue
        
        # ユニークユーザー数をカウント
        unique_users = set(dp['user_id'] for dp in all_data_points)
        variant_data['sample_size'] = len(unique_users)
        
        # メトリクス別に集計
        for metric in metrics:
            metric_values = [dp['value'] for dp in all_data_points if dp['metric'] == metric]
            
            if metric_values:
                variant_data['metrics'][metric] = {
                    'count': len(metric_values),
                    'mean': sum(metric_values) / len(metric_values),
                    'min': min(metric_values),
                    'max': max(metric_values),
                    'values': metric_values[:100]  # サンプルのみ保存
                }
            else:
                variant_data['metrics'][metric] = {
                    'count': 0,
                    'mean': 0,
                    'min': 0,
                    'max': 0,
                    'values': []
                }
        
        return variant_data
    
    def _calculate_statistical_significance(self, variants_data: Dict[str, Any], 
                                          metric: str) -> Dict[str, Any]:
        """統計的有意性の計算（簡単版）"""
        # 実際の統計テストの代わりに簡単な比較
        variant_names = list(variants_data.keys())
        if len(variant_names) < 2:
            return {'significant': False, 'confidence': 0}
        
        # コントロールと他のバリアントを比較
        control_name = 'control' if 'control' in variant_names else variant_names[0]
        control_data = variants_data[control_name]['metrics'].get(metric, {})
        control_mean = control_data.get('mean', 0)
        control_count = control_data.get('count', 0)
        
        results = {}
        
        for variant_name in variant_names:
            if variant_name == control_name:
                continue
            
            variant_data = variants_data[variant_name]['metrics'].get(metric, {})
            variant_mean = variant_data.get('mean', 0)
            variant_count = variant_data.get('count', 0)
            
            # 簡単な有意性判定（実際にはt検定などを使用すべき）
            if control_count > 30 and variant_count > 30:
                improvement = ((variant_mean - control_mean) / control_mean * 100) if control_mean > 0 else 0
                
                # 簡単な闾値設定
                significant = abs(improvement) > 5 and min(control_count, variant_count) > 50
                confidence = 0.95 if significant else 0.5
            else:
                improvement = 0
                significant = False
                confidence = 0.1
            
            results[f'{control_name}_vs_{variant_name}'] = {
                'improvement_percent': improvement,
                'significant': significant,
                'confidence': confidence,
                'sample_sizes': {
                    'control': control_count,
                    'variant': variant_count
                }
            }
        
        return results
    
    def _generate_recommendations(self, variants_data: Dict[str, Any], 
                                significance_data: Dict[str, Any]) -> List[str]:
        """実験結果に基づく推奨事項を生成"""
        recommendations = []
        
        # サンプルサイズのチェック
        total_sample = sum(v['sample_size'] for v in variants_data.values())
        if total_sample < 100:
            recommendations.append('サンプルサイズが不十分です。より多くのデータが必要です。')
        
        # 有意な改善があるバリアントを特定
        significant_improvements = []
        for comparison, data in significance_data.items():
            if isinstance(data, dict):
                for test_name, test_data in data.items():
                    if test_data.get('significant') and test_data.get('improvement_percent', 0) > 0:
                        significant_improvements.append({
                            'comparison': test_name,
                            'improvement': test_data['improvement_percent']
                        })
        
        if significant_improvements:
            best_improvement = max(significant_improvements, key=lambda x: x['improvement'])
            recommendations.append(
                f"{best_improvement['comparison']}で{best_improvement['improvement']:.1f}%の改善が確認されました。"
            )
        else:
            recommendations.append('統計的に有意な改善は確認されませんでした。')
        
        return recommendations
    
    def force_variant(self, user_id: int, experiment_name: str, variant_name: str, 
                     duration_hours: int = 24):
        """
        特定のユーザーに強制的にバリアントを割り当て
        
        Args:
            user_id: ユーザーID
            experiment_name: 実験名
            variant_name: バリアント名
            duration_hours: 強制割り当ての有効時間
        """
        experiment = self.experiments.get(experiment_name)
        if not experiment:
            raise ValueError(f"Experiment {experiment_name} not found")
        
        variant = next((v for v in experiment.variants if v.name == variant_name), None)
        if not variant:
            raise ValueError(f"Variant {variant_name} not found in experiment {experiment_name}")
        
        forced_config = {
            'name': variant.name,
            'experiment': experiment_name,
            'forced': True,
            **variant.config
        }
        
        if self.redis_client:
            cache_key = f"variant:{experiment_name}:{user_id}"
            self.redis_client.setex(
                cache_key, 
                duration_hours * 3600, 
                json.dumps(forced_config)
            )
        
        current_app.logger.info(
            f"Forced variant {variant_name} for user {user_id} in experiment {experiment_name}"
        )
    
    def assign_user_to_experiment(self, user_id: int, experiment_name: str) -> str:
        """
        ユーザーを実験に割り当て（テスト用の簡易版）
        
        Args:
            user_id: ユーザーID
            experiment_name: 実験名
            
        Returns:
            'control' または 'treatment'
        """
        # テスト用の簡易実装
        if user_id not in self.user_assignments:
            self.user_assignments[user_id] = {}
        
        # 実験が存在しない場合はデフォルト設定を作成
        if experiment_name not in self.experiments:
            self.experiments[experiment_name] = ExperimentConfig(
                name=experiment_name,
                control_percentage=50,
                enabled=True,
                start_date=datetime.utcnow()
            )
        
        # ユーザーIDに基づいて割り当て
        if user_id % 2 == 0:
            group = 'treatment'
        else:
            group = 'control'
        
        self.user_assignments[user_id][experiment_name] = group
        return group