import json
import os
import time
from urllib.request import urlopen

import psycopg2

APIKEY = os.environ.get("APIKEY")
if not APIKEY:
    print("Set your APIKEY environment variable")
LEAGUE_LISTING = "http://api.steampowered.com/IDOTA2Match_570/GetLeagueListing/v0001?key=%s" % APIKEY
MIN_START = 1483228800


def dont_piss_off_valve_but_account_for_sporadic_failures(req_url):
    fuck = True  # no idea why this failing. im waiting long enough to not piss off valve?
    sleep_time = 5  # valve say no more than 1 per second. be safe
    while fuck:
        try:
            time.sleep(sleep_time)
            response = urlopen(req_url)
            print("Requesting: %s" % req_url)
            fuck = False
        except:
            sleep_time += 30  # incase script breaks dont want to spam
            print("Request failed. sleeping more")
            continue
    data = json.load(response)
    return data


def get_all_leagues():
    return dont_piss_off_valve_but_account_for_sporadic_failures(LEAGUE_LISTING)["result"]["leagues"]


def get_league_match_list(league_id):
    return dont_piss_off_valve_but_account_for_sporadic_failures(
        "http://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v0001?" \
        "key=%s&league_id=%s" % (APIKEY, league_id))


def get_match_details(match_id):
    return dont_piss_off_valve_but_account_for_sporadic_failures(
        "http://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/v0001?" \
        "key=%s&match_id=%s" % (APIKEY, match_id))


def get_match_details_open_dota(match_id):
    return dont_piss_off_valve_but_account_for_sporadic_failures(
        "https://api.opendota.com/api/matches/%s" % match_id)


def get_vhigh_skill_matches(date_max, hero_id, game_mode=1, skill=3):
    # game_mode 1 allpick, 2 captains
    req = "http://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v0001?" \
          "key=%s&skill=%s&date_max=%s&date_min=%s" %\
          (APIKEY, skill, date_max, MIN_START)
    print(req)
    return dont_piss_off_valve_but_account_for_sporadic_failures(req)

def connect_postgres():
    connect_str = "dbname='dota_stats' user='%s' host='localhost' password='%s'" % \
                  (os.environ.get("USER"), os.environ.get("PG_PWORD"))
    # use our connection values to establish a connection
    conn = psycopg2.connect(connect_str)
    # create a psycopg2 cursor that can execute queries
    cursor = conn.cursor()
    return conn, cursor


def add_matches(session, connection, match_list_json, existing_match_ids=None, tstamp_from=0):
    # TODO filter out ridiculous games
    existing_match_ids = existing_match_ids or []

    matches = [match["match_id"] for match in match_list_json["result"]["matches"]
               if match["start_time"] > MIN_START and match["match_id"] not in existing_match_ids]
    #matches = [3066069898]
    max_start = tstamp_from
    for match_id in matches:

        match_data = get_match_details_open_dota(match_id)
        # Seems that may be hitting a max_size issue with postgres json?
        # It just silently fails executing the insert for 3066016949...why?
        print("old max start: %d" % max_start)
        max_start = min(match_data["start_time"], max_start)
        print("new max start: %d" % max_start)
        with open("/home/jdog/Documents/starttimes", "a+") as f:
            f.write(str(max_start))
        del match_data["chat"]
        del match_data["objectives"]
        del match_data["cosmetics"]
        del match_data["teamfights"]
        for player in match_data["players"]:
            del player["lane_pos"]
            del player["cosmetics"]
        #session.add(Match())
        #import pdb; pdb.set_trace()
        # if match_id == 3066016949:
        #     with open(os.getcwd() + "/buggy_match.json", "w+") as f:
        #         f.write(json.dumps(match_data).replace("'", ""))
        #     continue
        print("Adding match: %s" % match_id)
        # I think ' only used in chat. we dont care about this
        data_str = json.dumps(match_data).replace("'", "")
        try:
            session.execute("INSERT INTO matches VALUES (%s, '%s')" % (match_id, data_str))
        except Exception as e:
            print(e)
        connection.commit()
    return max_start


def main():
    # http://clarkdave.net/2013/06/what-can-you-do-with-postgresql-and-json/
    connection, session = connect_postgres()
    try:
        session.execute("""SELECT id from matches""")
    except:
        print("Select id failed")
    rows = session.fetchall()
    existing_match_ids = [row[0] for row in rows]
    print("Already have %s matches! :)" % len(existing_match_ids))
    #44
    leagues = get_all_leagues()
    max_start = int(time.time())
    while True:
        allpick_matches = get_vhigh_skill_matches(max_start, 44, skill=0, game_mode=1)
        #print(allpick_matches)
        new_max_start = add_matches(session, connection, allpick_matches, existing_match_ids, max_start)
        if new_max_start == max_start:
            print("No new results. probably reached the present")
            break
        else:
            max_start = new_max_start
        print("new min start: %s" % max_start)
    # for league in reversed(leagues):
        # match_list_json = get_league_match_list(league["leagueid"])
    #     add_matches(session, connection, league["leagueid"], existing_match_ids, 1483228800)  #2017-01-01

if __name__ == "__main__":
    main()
