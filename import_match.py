from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
import pickle
import os
import json
import click
import od_python


SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Copy of PMP Stats
SPREADSHEET_ID = '1aeku-3psdQNzpi_zQbSQ-hR5g2Xge2hWaRqMONqvmok'


def get_sheets():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    return service.spreadsheets()  # pylint: disable=no-member


def analyze(match, selected_team, heroes):
    def get_player(account_id):
        for p in selected_team:
            if account_id == p['id']:
                return p
        return None

    def get_hero_name(hero_id):
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

    metrics = {
        'date': datetime.fromtimestamp(match.start_time),
        'win': None,
        'players': {}
    }
    for p in match.players:
        if not get_player(p.account_id):
            continue
        if metrics['win'] is None:
            metrics['win'] = bool(p.win)

        metrics['players'][p.account_id] = {}
        metrics['players'][p.account_id]['friendly_name'] = get_player(p.account_id)['friendly_name']
        metrics['players'][p.account_id]['hero'] = get_hero_name(p.hero_id)
        metrics['players'][p.account_id]['kills'] = p.kills
        metrics['players'][p.account_id]['deaths'] = p.deaths
        metrics['players'][p.account_id]['assists'] = p.assists
        metrics['players'][p.account_id]['kda'] = (p.kills + p.assists) / p.deaths if p.deaths != 0 else p.kills + p.assists

    return metrics


@click.command()
@click.option('--spreadsheet-id', default=SPREADSHEET_ID, help='ID of spreadsheet to import match data to')
@click.argument('match_id')
def cli(spreadsheet_id, match_id):
    sheet = get_sheets()
    teams = json.load(open('teams.json'))
    heroes = json.load(open('heroes.json'))
    selected_team = teams['pmp']

    match_api = od_python.MatchesApi()

    m = match_api.matches_match_id_get(match_id)
    metrics = analyze(m, selected_team, heroes)
    print(metrics)

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
