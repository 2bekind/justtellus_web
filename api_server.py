"""
API сервер для мини-приложения Telegram
Предоставляет статистику пользователей через HTTP API
"""
import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import pytz

load_dotenv()

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с любых доменов (для Telegram WebApp)

moscow_tz = pytz.timezone('Europe/Moscow')

# Загружаем данные из файла
def load_stats():
    """Загружает статистику из bot_data.json"""
    if not os.path.exists('bot_data.json'):
        return {}
    
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('recipient_stats', {})
    except Exception as e:
        print(f"Ошибка загрузки статистики: {e}")
        return {}


@app.route('/api/stats/<int:user_id>', methods=['GET'])
def get_stats(user_id):
    """
    Получает статистику для пользователя
    
    Параметры:
    - user_id: ID пользователя Telegram
    
    Возвращает JSON с статистикой
    """
    try:
        stats_data = load_stats()
        
        # Проверяем, является ли пользователь владельцем
        is_owner = user_id in [7654953677, 8109892353]
        
        if is_owner and str(user_id) in stats_data:
            # Для владельцев возвращаем полную статистику
            user_stats = stats_data[str(user_id)]
            return jsonify({
                'success': True,
                'owner': True,
                'stats': {
                    'received': user_stats.get('received', 0),
                    'sent': user_stats.get('sent', 0),
                    'choosers': len(user_stats.get('choosers', [])),
                    'max_streak': user_stats.get('max_streak', 0)
                }
            })
        else:
            # Для обычных пользователей возвращаем общую статистику
            total_sent = sum(s.get('sent', 0) for s in stats_data.values())
            total_max_streak = max((s.get('max_streak', 0) for s in stats_data.values()), default=0)
            
            return jsonify({
                'success': True,
                'owner': False,
                'stats': {
                    'sent': total_sent,
                    'max_streak': total_max_streak
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности API"""
    return jsonify({
        'status': 'ok',
        'message': 'API работает'
    })


if __name__ == '__main__':
    # Запускаем сервер на порту 5000
    # В продакшене используйте другой порт или настройте через переменные окружения
    port = int(os.getenv('API_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

