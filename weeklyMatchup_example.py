import json
import requests
import datetime
import csv
import numpy as np
import pandas as pd
import plotly.express as px
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

class Team:
    def __init__(self, name, id, manager_name, team_key):
        self.name = name
        self.id = id
        self.manager_name = manager_name
        self.team_key = team_key
        self.goals = 0
        self.assists = 0
        self.pim = 0
        self.ppp = 0
        self.shots = 0
        self.hits = 0
        self.blocks = 0
        self.wins = 0
        self.sho = 0
        self.svpct = 0
        self.games = 0
        self.matchup = ''
        self.matchup_calculated = False

    def calculateMatchup(self, opp_goals, opp_assists, opp_pim, opp_ppp, opp_shots, opp_hits, opp_blocks, opp_wins, opp_sho, opp_svpct, opp_games):
        home_wins = 0
        away_wins = 0

        deltas = {}
        deltas['Goals'] = self.goals - opp_goals
        deltas['Assists'] = self.assists - opp_assists
        deltas['PIM'] = self.pim - opp_pim
        deltas['PPP'] = self.ppp - opp_ppp
        deltas['Shots'] = self.shots - opp_shots
        deltas['Hits'] = self.hits - opp_hits
        deltas['Blocks'] = self.blocks - opp_blocks
        deltas['Wins'] = self.wins - opp_wins
        deltas['SHO'] = self.sho - opp_sho
        deltas['Sv%'] = self.svpct - opp_svpct
        deltas['Games'] = self.games - opp_games

        for delta_key in deltas:
            if delta_key != 'Games':
                if deltas[delta_key] > 0:
                    home_wins += 1
                elif deltas[delta_key] < 0:
                    away_wins += 1
        
        self.matchup_calculated = True

        return(home_wins, away_wins, deltas)
        

class Player:
    def __init__(self, name, id, roster_date, skater_type, team, games_week, health_status):
        self.name = name
        self.id = id
        self.team = team
        self.rostered_dates = [roster_date]
        self.games_played = 0
        self.skater_type = skater_type
        self.team_game_dates = games_week
        self.season_stats = {}
        self.week_rostered_game_count = 0
        self.health_status = health_status

    def calculateGameCount(self):
        for roster_date in self.rostered_dates:
            
            if roster_date in self.team_game_dates:
                self.week_rostered_game_count += 1



# ... Team and Player classes unchanged ...


if __name__ == '__main__':
    print_flag = False

    oauth = OAuth2(None, None, from_file='oauth2.json')

    today = datetime.date.today()
    cur_year = 2025
    cur_game = yfa.game.Game(oauth, 'nhl')
    print(cur_game.league_ids(year=cur_year))
    league_id = cur_game.league_ids(year=cur_year)[0]
    league = yfa.league.League(oauth, league_id)
    cur_week = league.current_week()
    print('League Week: {0}'.format(cur_week))

    csv_file_name = '{1}_ProjectionsWeek{0}.csv'.format(cur_week, cur_year)

    week_start_dt, week_end_dt = league.week_date_range(cur_week)
    week_start = week_start_dt.strftime("%Y-%m-%d")
    week_end = week_end_dt.strftime("%Y-%m-%d")
    print('Week Range: {0} to {1}'.format(week_start, week_end))

    teams = league.teams()
    team_dict = {}
    for team_key in teams:
        team_key = teams[team_key]['team_key']
        manager_name = teams[team_key]['managers'][0]['manager']['nickname']
        team_name = teams[team_key]['name']
        team_id = teams[team_key]['team_id']
        team_dict[team_key] = Team(team_name, team_id, manager_name, team_key)

    stat_categories = league.stat_categories()
    api_base_stats = 'https://api.nhle.com'
    api_base_games = 'https://api-web.nhle.com/v1'
    teams_api_url = api_base_stats + "/stats/rest/en/team"

    nhl_teams_r = requests.get(teams_api_url)
    nhl_teams_content = json.loads(nhl_teams_r.content)

    # --- UPDATED: add Logo URL column ---
    weekly_team_stats = [
        ('Team Name', 'Goals', 'Assists', 'PIM', 'PPP', 'Shots', 'Hits',
         'Blocks', 'Wins', 'SHO', 'Sv%', 'Games', 'Logo URL')
    ]
    matchup_stats_list = [
        ('Matchup', 'Goal', 'Assists', 'PIM', 'PPP', 'Shots', 'Hits',
         'Blocks', 'Wins', 'SHO', 'Sv%', 'Game Difference', 'Predicted Outcome')
    ]

    # Matchups mapping unchanged...
    matchups = league.matchups(cur_week)
    for matchup in matchups['fantasy_content']['league']:
        try:
            for matchup_key in (matchup['scoreboard']['0']['matchups']):
                try:
                    matchup_stats = matchup['scoreboard']['0']['matchups'][matchup_key]['matchup']

                    team_1_id = matchup_stats['0']['teams']['0']['team'][0][0]['team_key']
                    team_2_id = matchup_stats['0']['teams']['1']['team'][0][0]['team_key']

                    team_dict[team_1_id].matchup = team_2_id
                    team_dict[team_2_id].matchup = team_1_id

                except TypeError:
                    pass
        except KeyError:
            pass

    # NHL schedules
    weekly_gamedates_team = {}
    for nhl_team in nhl_teams_content['data']:
        tri = nhl_team['triCode']
        schedule_url = f'{api_base_games}/club-schedule/{tri}/week/now'
        try:
            schedule_r = requests.get(schedule_url)
            schedule_content = json.loads(schedule_r.content)
            weekly_gamedates = []
            try:
                for game_date in schedule_content.get('games', []):
                    weekly_gamedates.append(game_date['gameDate'])
                weekly_gamedates_team[tri] = weekly_gamedates
            except KeyError:
                pass
        except json.decoder.JSONDecodeError:
            pass

    # Projections per team
    for team_key in team_dict:
        cur_team = team_dict[team_key]
        print(cur_team.name)
        team_goals = 0
        team_assists = 0
        team_hits = 0
        team_ppp = 0
        team_shots = 0
        team_blocks = 0
        team_pims = 0
        team_wins = 0
        team_sho = 0
        team_games = 0

        # NEW: SV% weighting accumulators
        team_svpct_weighted_sum = 0.0
        team_svpct_weight_total = 0.0

        cur_yahoo_team = yfa.team.Team(oauth, cur_team.team_key)

        weekly_roster = {}
        cur_date = week_start_dt

        while cur_date <= week_end_dt:
            cur_roster = cur_yahoo_team.roster(day=cur_date)
            for roster_player in cur_roster:
                cur_id = roster_player['player_id']
                if roster_player['selected_position'] in ('D', 'G', 'C', 'LW', 'RW'):
                    if cur_id in weekly_roster:
                        weekly_roster[cur_id].rostered_dates.append(cur_date.strftime("%Y-%m-%d"))
                    else:
                        player_details = league.player_details(cur_id)[0]
                        try:
                            cur_status = player_details['status']
                        except:
                            cur_status = 'Healthy'

                        cur_team_abv = player_details['editorial_team_abbr']
                        if cur_team_abv == 'TB':
                            cur_team_abv = 'TBL'
                        if cur_team_abv == 'LA':
                            cur_team_abv = 'LAK'
                        if cur_team_abv == 'NJ':
                            cur_team_abv = 'NJD'
                        if cur_team_abv == 'SJ':
                            cur_team_abv = 'SJS'

                        games_this_week = weekly_gamedates_team.get(cur_team_abv, [])

                        weekly_roster[cur_id] = Player(
                            roster_player['name'],
                            cur_id,
                            cur_date.strftime("%Y-%m-%d"),
                            player_details['position_type'],
                            cur_team_abv,
                            games_this_week,
                            cur_status
                        )

            cur_date += datetime.timedelta(days=1)

        cur_players = []
        for player in weekly_roster:
            cur_players.append(player)
            weekly_roster[player].calculateGameCount()

        player_stats_season = league.player_stats(cur_players, 'season')

        for player_stat in player_stats_season:
            cur_player_id = player_stat['player_id']
            games_played = player_stat['GP']
            games_this_week = weekly_roster[cur_player_id].week_rostered_game_count

            if games_played == '-':
                cur_status = 'Out'
            else:
                cur_status = weekly_roster[cur_player_id].health_status

            if cur_status == 'Healthy':
                team_games += games_this_week

                if player_stat['position_type'] == 'P':
                    games_played = max(games_played, 1)
                    goals_pg = player_stat['G'] / games_played
                    assists_pg = player_stat['A'] / games_played
                    hits_pg = player_stat['HIT'] / games_played
                    shots_pg = player_stat['SOG'] / games_played
                    ppp_pg = player_stat['PPP'] / games_played
                    blocks_pg = player_stat['BLK'] / games_played
                    pim_pg = player_stat['PIM'] / games_played

                    goals_proj = goals_pg * games_this_week
                    assists_proj = assists_pg * games_this_week
                    hits_proj = hits_pg * games_this_week
                    shots_proj = shots_pg * games_this_week
                    ppp_proj = ppp_pg * games_this_week
                    blocks_proj = blocks_pg * games_this_week
                    pim_proj = pim_pg * games_this_week

                    team_goals += goals_proj
                    team_assists += assists_proj
                    team_hits += hits_proj
                    team_ppp += ppp_proj
                    team_shots += shots_proj
                    team_blocks += blocks_proj
                    team_pims += pim_proj

                if player_stat['position_type'] == 'G':
                    if games_played == '-' or games_played == 0:
                        continue

                    wins_pg = player_stat['W'] / games_played
                    svpct = player_stat['SV%']
                    sho_pg = player_stat['SHO'] / games_played

                    wins_proj = round(wins_pg * games_this_week)
                    sho_proj = sho_pg * games_this_week

                    team_wins += wins_proj
                    team_sho += sho_proj

                    # NEW: weight SV% by expected games this week
                    team_svpct_weighted_sum += svpct * games_this_week
                    team_svpct_weight_total += games_this_week

        if team_svpct_weight_total > 0:
            team_svpct = team_svpct_weighted_sum / team_svpct_weight_total
        else:
            team_svpct = 0.0

        print('  Projected Team Goals:   {0:0.2f}'.format(team_goals))
        # ... other prints ...
        weekly_team_stats.append((
            teams[team_key]['name'],
            '{0:0.2f}'.format(team_goals),
            '{0:0.2f}'.format(team_assists),
            '{0:0.2f}'.format(team_pims),
            '{0:0.2f}'.format(team_ppp),
            '{0:0.2f}'.format(team_shots),
            '{0:0.2f}'.format(team_hits),
            '{0:0.2f}'.format(team_blocks),
            '{0}'.format(team_wins),
            '{0:0.2f}'.format(team_sho),
            '{0:0.3f}'.format(team_svpct),
            team_games,
            teams[team_key]['team_logos'][0]['team_logo']['url']  # NEW
        ))

        # ... set team_dict fields ...

    # Matchup calculation loop unchanged ...

    matchup_header = matchup_stats_list[0]
    matchup_rows = matchup_stats_list[1:]   # IMPORTANT: skip header row

    matchup_df = pd.DataFrame(matchup_rows, columns=matchup_header)

    # Safe split of "X to Y"
    split_cols = matchup_df['Predicted Outcome'].str.split(' to ', n=1, expand=True)

    # Replace missing or malformed values with 0
    split_cols = split_cols.fillna(0)

    # Convert to integers
    split_cols = split_cols.astype(int)

    matchup_df['Home Wins'] = split_cols[0]
    matchup_df['Away Wins'] = split_cols[1]


    matchup_df = pd.DataFrame(matchup_rows, columns=matchup_header)
    matchup_df[['Home Wins', 'Away Wins']] = (
        matchup_df['Predicted Outcome']
        .str.split(' to ', expand=True)
        .astype(int)
    )

    fig_matchups = px.bar(
        matchup_df,
        x='Matchup',
        y=['Home Wins', 'Away Wins'],
        barmode='group',
        title=f'Projected Category Wins – Week {cur_week}',
        labels={'value': 'Projected Category Wins', 'variable': 'Side'}
    )
    fig_matchups.update_layout(
        xaxis_title='Matchup',
        yaxis_title='Projected Category Wins',
        xaxis_tickangle=-30
    )

    matchup_plot_file = f"{cur_year}_Week{cur_week}_ProjectedMatchups.html"
    fig_matchups.write_html(matchup_plot_file)
    print('Wrote matchup visualization to', matchup_plot_file)

    print('Writing outputs to {0}'.format(csv_file_name))
    with open(csv_file_name, "wt", newline='') as fp:
        writer = csv.writer(fp, delimiter=",")
        writer.writerows(weekly_team_stats)
        writer.writerow('')
        writer.writerow('')
        writer.writerow('')
        writer.writerows(matchup_stats_list)




