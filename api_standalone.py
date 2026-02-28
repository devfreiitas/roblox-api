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
            'roblox_user_id, roblox_username, class, team, wage, cup_tied, penalty, role, discord_id'
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
                    'RoleTeam': player.get('role') or 'Player',
                    'DiscordId': player.get('discord_id') or None
                })
            return jsonify({'success': True, 'data': players_list})
        else:
            return jsonify({'success': True, 'data': []})
    except Exception as e:
        logging.error(f"Error fetching all players: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bans/check/<int:roblox_user_id>', methods=['GET'])
def check_ban_by_roblox(roblox_user_id):
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
            return jsonify({'success': True, 'is_banned': False, 'data': None})

    except Exception as e:
        logging.error(f"Error checking ban for roblox_user_id {roblox_user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blacklist/check/<int:roblox_user_id>', methods=['GET'])
def check_player_blacklist(roblox_user_id):
    try:
        result = (
            db.client.table('bans')
            .select('id, ban_type, reason, is_active')
            .eq('roblox_user_id', roblox_user_id)
            .eq('ban_type', 'blacklist_player')
            .eq('is_active', True)
            .limit(1)
            .execute()
        )

        if result.data and len(result.data) > 0:
            ban = result.data[0]
            return jsonify({
                'success': True,
                'is_blacklisted': True,
                'data': {
                    'ban_type': ban.get('ban_type'),
                    'reason': ban.get('reason'),
                }
            })
        else:
            return jsonify({'success': True, 'is_blacklisted': False, 'data': None})

    except Exception as e:
        logging.error(f"Error checking blacklist for roblox_user_id {roblox_user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blacklist/league/<int:league_group_id>', methods=['GET'])
def check_league_blacklist(league_group_id):
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

        return jsonify({'success': True, 'count': len(blacklisted), 'data': blacklisted})

    except Exception as e:
        logging.error(f"Error fetching player blacklist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/blacklist/league-groups', methods=['GET'])
def get_blacklisted_league_groups():
    """
    Returns all unique league group IDs that currently have active blacklist entries.
    Used by Roblox scripts so they don't need hardcoded group ID lists.
    Response: { "success": true, "count": N, "data": [{ "league_group_id": 123 }, ...] }
    """
    try:
        result = (
            db.client.table('bans')
            .select('league_group_id')
            .eq('ban_type', 'blacklist_league')
            .eq('is_active', True)
            .execute()
        )

        seen = set()
        groups = []
        for row in (result.data or []):
            gid = row.get('league_group_id')
            if gid and gid not in seen:
                seen.add(gid)
                groups.append({'league_group_id': gid})

        return jsonify({'success': True, 'count': len(groups), 'data': groups})

    except Exception as e:
        logging.error(f"Error fetching blacklisted league groups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/teams', methods=['GET'])
def get_all_teams():
    try:
        result = db.client.table('teams').select(
            'team_name, manager_id, abbreviation, created_at'
        ).execute()

        if result.data:
            teams_list = []
            for team in result.data:
                teams_list.append({
                    'TeamName': team.get('team_name') or 'Unknown',
                    'ManagerId': team.get('manager_id'),
                    'Abbreviation': team.get('abbreviation') or '',
                    'CreatedAt': team.get('created_at'),
                })
            return jsonify({'success': True, 'count': len(teams_list), 'data': teams_list})
        else:
            return jsonify({'success': True, 'count': 0, 'data': []})
    except Exception as e:
        logging.error(f"Error fetching all teams: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/teams/<string:team_name>', methods=['GET'])
def get_team_by_name(team_name):
    try:
        result = db.client.table('teams').select(
            'team_name, manager_id, abbreviation, created_at'
        ).ilike('team_name', team_name).limit(1).execute()

        if result.data and len(result.data) > 0:
            team = result.data[0]
            return jsonify({
                'success': True,
                'data': {
                    'TeamName': team.get('team_name') or 'Unknown',
                    'ManagerId': team.get('manager_id'),
                    'Abbreviation': team.get('abbreviation') or '',
                    'CreatedAt': team.get('created_at'),
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Team not found'}), 404
    except Exception as e:
        logging.error(f"Error fetching team '{team_name}': {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/teams/manager/<int:manager_id>', methods=['GET'])
def get_team_by_manager(manager_id):
    try:
        result = db.client.table('teams').select(
            'team_name, manager_id, abbreviation, created_at'
        ).eq('manager_id', manager_id).limit(1).execute()

        if result.data and len(result.data) > 0:
            team = result.data[0]
            return jsonify({
                'success': True,
                'data': {
                    'TeamName': team.get('team_name') or 'Unknown',
                    'ManagerId': team.get('manager_id'),
                    'Abbreviation': team.get('abbreviation') or '',
                    'CreatedAt': team.get('created_at'),
                }
            })
        else:
            return jsonify({'success': False, 'error': 'No team found for this manager'}), 404
    except Exception as e:
        logging.error(f"Error fetching team for manager_id {manager_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    import asyncio
    asyncio.run(db.connect())

    start_keepalive()

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)