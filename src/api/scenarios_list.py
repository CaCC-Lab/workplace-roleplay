"""
シナリオ一覧取得API
ページネーション、フィルタリング、検索機能をサポート
"""
from flask import jsonify, request
from typing import Dict, Any, List
import math


def get_paginated_scenarios():
    """
    ページネーション対応のシナリオ一覧を返す
    
    クエリパラメータ:
    - page: ページ番号（デフォルト: 1）
    - per_page: 1ページあたりの件数（デフォルト: 12、最大: 50）
    - difficulty: 難易度フィルター（初級/中級/上級）
    - tag: タグフィルター
    - search: 検索キーワード
    - sort: ソート順（scenario_num/difficulty_asc/difficulty_desc）
    """
    try:
        # scenarios をインポート
        from app import scenarios
        
        # パラメータ取得
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, max(1, int(request.args.get('per_page', 12))))
        difficulty = request.args.get('difficulty', '')
        tag = request.args.get('tag', '')
        search = request.args.get('search', '').lower()
        sort_order = request.args.get('sort', 'scenario_num')
        
        # フィルタリング
        filtered_scenarios = []
        for scenario_id, scenario_data in scenarios.items():
            # 難易度フィルター
            if difficulty and scenario_data.get('difficulty') != difficulty:
                continue
            
            # タグフィルター
            if tag and tag not in scenario_data.get('tags', []):
                continue
            
            # 検索フィルター
            if search:
                title = scenario_data.get('title', '').lower()
                description = scenario_data.get('description', '').lower()
                if search not in title and search not in description:
                    continue
            
            filtered_scenarios.append({
                'id': scenario_id,
                'data': scenario_data
            })
        
        # ソート
        if sort_order == 'scenario_num':
            # シナリオIDの数値部分でソート
            filtered_scenarios.sort(key=lambda x: int(x['id'].replace('scenario', '')))
        elif sort_order == 'difficulty_asc':
            difficulty_order = {'初級': 1, '中級': 2, '上級': 3}
            filtered_scenarios.sort(key=lambda x: difficulty_order.get(x['data'].get('difficulty', '初級'), 1))
        elif sort_order == 'difficulty_desc':
            difficulty_order = {'初級': 3, '中級': 2, '上級': 1}
            filtered_scenarios.sort(key=lambda x: difficulty_order.get(x['data'].get('difficulty', '初級'), 3))
        
        # ページネーション計算
        total_count = len(filtered_scenarios)
        total_pages = math.ceil(total_count / per_page)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # ページのシナリオを取得
        page_scenarios = filtered_scenarios[start_idx:end_idx]
        
        # レスポンス形式に変換
        scenarios_list = []
        for item in page_scenarios:
            scenario_data = item['data']
            scenarios_list.append({
                'id': item['id'],
                'title': scenario_data.get('title', ''),
                'description': scenario_data.get('description', ''),
                'difficulty': scenario_data.get('difficulty', '初級'),
                'category': scenario_data.get('category', 'communication'),
                'tags': scenario_data.get('tags', []),
                'duration': scenario_data.get('duration', '5-10分'),
                'learning_points': scenario_data.get('learning_points', [])
            })
        
        return jsonify({
            'scenarios': scenarios_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            },
            'filters': {
                'difficulty': difficulty,
                'tag': tag,
                'search': search,
                'sort': sort_order
            }
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid parameter value', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


def get_scenario_tags():
    """
    すべてのユニークなタグを返す
    """
    try:
        from app import scenarios
        
        all_tags = set()
        for scenario_data in scenarios.values():
            tags = scenario_data.get('tags', [])
            all_tags.update(tags)
        
        return jsonify({
            'tags': sorted(list(all_tags))
        })
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500