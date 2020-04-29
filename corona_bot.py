import datetime
import json
import requests
import argparse
import logging
from bs4 import BeautifulSoup
from tabulate import tabulate
from slack_client import slacker

FORMAT = '[%(asctime)-15s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG, filename='bot.log', filemode='a')

URL = 'http://covid19tracker.gov.bd/api/district'
SHORT_HEADERS = ['Sno', 'State','In']
FILE_NAME = 'corona_bd_data.json'


def save(x):
    with open(FILE_NAME, 'w') as f:
        json.dump(x, f)


def load():
    res = {}
    with open(FILE_NAME, 'r') as f:
        res = json.load(f)
    return res
    

if __name__ == '__main__':
   
    parser  = argparse.ArgumentParser()
    parser.add_argument('--states', default=',')
    args = parser.parse_args()
    interested_states = args.states.split(',')
    
    current_time = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    info = []

    try:
        response = requests.get(URL)
        data = response.json()
        stats = []
        for row,dict in enumerate(data["features"]):
            datas = data["features"][row]["properties"]
            if datas["confirmed"]=="":
                stat = ['',str(row+1),str(datas["name"]),str(0)]
            else:
                stat = ['',str(row+1),str(datas["name"]),str(datas["confirmed"])]
            if len(stat) == 4:
                stats.append(stat)
            elif any([s.lower() in stat[1].lower() for s in interested_states]):
                stats.append(stat)
        cur_data = {x[2]: {current_time: x[3]} for x in stats}
        past_data = load()
   
        changed = False

        for state in cur_data:
            if state not in past_data:
                # new state has emerged
                info.append(f'NEW_STATE {state} got corona virus: {cur_data[state][current_time]}')
                past_data[state] = {}
                changed = True
            else:
                past = past_data[state]['latest']
                cur = cur_data[state][current_time]
                if past != cur:
                    changed = True
                    info.append(f'Change for {state}: {past}->{cur}')
        
        events_info = ''
        for event in info:
            logging.warning(event)
            events_info += '\n - ' + event.replace("'", "")
        if changed:
            # override the latest one now
            for state in cur_data:
                past_data[state]['latest'] = cur_data[state][current_time]
                past_data[state][current_time] = cur_data[state][current_time]
            save(past_data)
            
            table = tabulate(stats, headers=SHORT_HEADERS, tablefmt='psql')
            slack_text = f'Please find CoronaVirus Summary for Bangladesh below:\n{events_info}\n```{table}```'
            slacker()(slack_text)
    except Exception as e:
        logging.exception('oops, corono script failed.')
        slacker()(f'Exception occured: [{e}]')