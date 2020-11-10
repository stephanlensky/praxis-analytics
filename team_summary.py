from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
import pickle
import os
import json
import click
import requests
from enum import Enum
from time import sleep


# some OAuth Google Sheets stuff goes here eventually
class Lane(Enum):
    SAFE = 1
    MID = 2
    OFF = 3


def get_hero_name(heroes, hero_id):
    # abbreviations... "Abyssal Underlord"? lol
    abbreviated = {
        108: 'Underlord'
    }

    if hero_id in abbreviated:
        return abbreviated[hero_id]
    for h in heroes['heroes']:
        if hero_id == h['id']:
            return h['localized_name']
    return None


def summarize_players(match_ids, team_player_ids, heroes):
    # INFO WE WANT:
    count = 0
    
    def process_match(summaries, match_id):
        out = requests.get(f'http://api.opendota.com/api/matches/{match_id}')
        match_data = json.loads(out.text)
        sleep(1)
        print(out.status_code)
        print(count)
        for match_player_data in match_data['players']:
            player_id = match_player_data['account_id']

            #ignore players not on the team we're looking at
            if player_id not in team_player_ids:
                continue

            player_lane = Lane(match_player_data['lane_role'])
            player_hero = get_hero_name(heroes, match_player_data['hero_id'])

            # set player name if not already set
            if 'name' not in summaries[match_player_data['account_id']]:
                summaries[player_id]['name'] = match_player_data['personaname']

            # Update lane stats in player_summaries
            summaries[player_id]['lane_stats'][player_lane]['count'] += 1

            if player_hero not in summaries[player_id]['lane_stats'][player_lane]['heroes']:
                summaries[player_id]['lane_stats'][player_lane]['heroes'][player_hero] = 1
            else:
                summaries[player_id]['lane_stats'][player_lane]['heroes'][player_hero] += 1

    player_summaries = dict()
    for pid in team_player_ids:
        player_summaries[pid] = {
            'badge': 0,
            'lane_stats': dict(),
        }
        for lane in [Lane.SAFE, Lane.MID, Lane.OFF]:
            player_summaries[pid]['lane_stats'][lane] = {'count': 0, 'heroes': dict()}

    for match in match_ids:
        process_match(player_summaries, match)
        count += 1

    return player_summaries


@click.command()
@click.option('--patch', default=46, help='ID of patch to search (e.g. patch 7.27 -> 46')
@click.argument('team_name', default='pmp')
def cli(patch, team_name):
    teams = json.load(open('teams.json'))
    heroes = json.load(open('heroes.json'))
    selected_team = teams[team_name]
    team_players = [p['id'] for p in selected_team]
    team_payload = {'patch': patch, 'included_account_id': team_players}
    api_response = json.loads(
        requests.get(f'http://api.opendota.com/api/players/{team_players[1]}/matches', params=team_payload).text)

    team_match_ids = [match['match_id'] for match in api_response]

    print(summarize_players(team_match_ids,team_players, heroes))


    # TODO: add to spreadsheet

    # result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
    #                             range=SAMPLE_RANGE_NAME).execute()
    # values = result.get('values', [])

    # if not values:
    #     print('No data found.')
    # else:
    #     print('Name, Major:')
    #     for row in values:
    #         # Print columns A and E, which correspond to indices 0 and 4.
    #         print('%s, %s' % (row[0], row[4]))


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
