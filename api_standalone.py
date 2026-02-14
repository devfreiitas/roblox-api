import logging
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from database_supabase import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = Flask(__name__)
CORS(app)

db = Database()

@app.before_request
def before_first_request():
    if not hasattr(app, 'db_initialized'):
        import asyncio
        asyncio.run(db.connect())
        app.db_initialized = True

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

@app.route('/api/player/<int:roblox_user_id>', methods=['GET'])
def get_player_data(roblox_user_id):
    try:
        result = db.client.table('players').select(
            'class, team, total'
        ).eq('roblox_user_id', roblox_user_id).execute()
        
        if result.data and len(result.data) > 0:
            player_data = result.data[0]
            return jsonify({
                'success': True,
                'data': {
                    'Class': player_data.get('class') or 'Unknown',
                    'Team': player_data.get('team') or 'FREE-AGENT',
                    'Over': player_data.get('total') or 0
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'Class': 'Unknown',
                    'Team': 'FREE-AGENT',
                    'Over': 0
                }
            })
    except Exception as e:
        logging.error(f"Error fetching player data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    import asyncio
    asyncio.run(db.connect())
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)