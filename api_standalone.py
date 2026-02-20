import logging
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from database_supabase import Database
from keep_alive import start_keepalive

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
            'class, team, wage, cup_tied, penalty, role'
        ).eq('roblox_user_id', roblox_user_id).execute()
        
        if result.data and len(result.data) > 0:
            player_data = result.data[0]
            return jsonify({
                'success': True,
                'data': {
                    'Class': player_data.get('class') or 'Unknown',
                    'Team': player_data.get('team') or 'FREE-AGENT',
                    'Wage': player_data.get('wage') or 0,
                    'Cuptied': player_data.get('cup_tied') or False,
                    'Penalty': player_data.get('penalty') or 0,
                    'RoleTeam': player_data.get('role') or 'Player'
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'Class': 'Unknown',
                    'Team': 'FREE-AGENT',
                    'Wage': 0,
                    'Cuptied': False,
                    'Penalty': 0,
                    'RoleTeam': 'Player'
                }
            })
    except Exception as e:
        logging.error(f"Error fetching player data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/players', methods=['GET'])
def get_all_players():
    try:
        result = db.client.table('players').select(
            'roblox_user_id, roblox_username, class, team, wage, cup_tied, penalty, role'
        ).execute()
        
        if result.data:
            players_list = []
            for player in result.data:
                players_list.append({
                    'UserId': player.get('roblox_user_id'),
                    'Name': player.get('roblox_username') or 'Unknown',
                    'Class': player.get('class') or 'Unknown',
                    'Team': player.get('team') or 'FREE-AGENT',
                    'Wage': player.get('wage') or 0,
                    'Cuptied': player.get('cup_tied') or False,
                    'Penalty': player.get('penalty') or 0,
                    'RoleTeam': player.get('role') or 'Player'
                })
            
            return jsonify({
                'success': True,
                'data': players_list
            })
        else:
            return jsonify({
                'success': True,
                'data': []
            })
    except Exception as e:
        logging.error(f"Error fetching all players: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    import asyncio
    asyncio.run(db.connect())
    
    start_keepalive()
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
@app.route('/api/bans/check/<int:roblox_user_id>', methods=['GET'])
def check_ban_by_roblox(roblox_user_id):
    """
    Check if a Roblox user is banned/blacklisted.
    Returns ban info so the game can block them.
    """
    try:
        result = (
            db.client.table('bans')
            .select('id, ban_type, reason, expires_at, bail_amount, is_active')
            .eq('roblox_user_id', roblox_user_id)
            .eq('is_active', True)
            .limit(1)
            .execute()
        )

        if result.data and len(result.data) > 0:
            ban = result.data[0]
            return jsonify({
                'success': True,
                'is_banned': True,
                'data': {
                    'ban_type': ban.get('ban_type'),
                    'reason': ban.get('reason'),
                    'expires_at': ban.get('expires_at'),
                    'bail_amount': ban.get('bail_amount'),
                }
            })
        else:
            return jsonify({
                'success': True,
                'is_banned': False,
                'data': None
            })

    except Exception as e:
        logging.error(f"Error checking ban for roblox_user_id {roblox_user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blacklist/league/<int:league_group_id>', methods=['GET'])
def check_league_blacklist(league_group_id):
    """
    Returns all active blacklisted players for a given Roblox league group ID.
    The game uses this to prevent blacklisted users from joining matches.
    """
    try:
        result = (
            db.client.table('bans')
            .select('roblox_user_id, roblox_username, reason, discord_id')
            .eq('ban_type', 'blacklist_league')
            .eq('league_group_id', league_group_id)
            .eq('is_active', True)
            .execute()
        )

        blacklisted = []
        for row in (result.data or []):
            blacklisted.append({
                'roblox_user_id': row.get('roblox_user_id'),
                'roblox_username': row.get('roblox_username'),
                'reason': row.get('reason'),
            })

        return jsonify({
            'success': True,
            'league_group_id': league_group_id,
            'count': len(blacklisted),
            'data': blacklisted,
        })

    except Exception as e:
        logging.error(f"Error fetching league blacklist for group {league_group_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blacklist/players', methods=['GET'])
def get_player_blacklist():
    """
    Returns all globally blacklisted players (blacklist_player type).
    """
    try:
        result = (
            db.client.table('bans')
            .select('roblox_user_id, roblox_username, reason, discord_id')
            .eq('ban_type', 'blacklist_player')
            .eq('is_active', True)
            .execute()
        )

        blacklisted = []
        for row in (result.data or []):
            blacklisted.append({
                'roblox_user_id': row.get('roblox_user_id'),
                'roblox_username': row.get('roblox_username'),
                'reason': row.get('reason'),
            })

        return jsonify({
            'success': True,
            'count': len(blacklisted),
            'data': blacklisted,
        })

    except Exception as e:
        logging.error(f"Error fetching player blacklist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500