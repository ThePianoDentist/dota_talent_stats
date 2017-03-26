import json
import os
import time
from urllib.request import urlopen, Request

import psycopg2

APIKEY = os.environ.get("APIKEY")
if not APIKEY:
    print("Set your APIKEY environment variable")
LEAGUE_LISTING = "http://api.steampowered.com/IDOTA2Match_570/GetLeagueListing/v0001?key=%s" % APIKEY
MIN_START = 1483228800

class MissingMatchException(Exception):
    pass

def dont_piss_off_valve_but_account_for_sporadic_failures(req_url):
    succeeded = False
    sleep_time = 3  # valve say no more than 1 per second. be safe
    while not succeeded:
        #try:
            time.sleep(sleep_time)
            print("Requesting: %s" % req_url)
            request = Request(req_url)
            request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36')
            response = urlopen(request)
            succeeded = True
        # except Exception as e:
        #     if "404" in e:
        #         raise
        #     sleep_time += 30  # incase script breaks dont want to spam
        #     print(e)
        #     print("Request failed. sleeping more")
        #     continue
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


def get_vhigh_skill_matches(match_seq_min, hero_id, game_mode=1, skill=3):
    # game_mode 1 allpick, 2 captains
    req = "http://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v0001?" \
          "key=%s&skill=%s&game_mode=%s&date_min=%s&start_at_match_id=%s" %\
          (APIKEY, skill, game_mode, MIN_START, match_seq_min - 1)
    print(req)
    return dont_piss_off_valve_but_account_for_sporadic_failures(req)

def get_match_sequence(match_seq_min=None):
    if match_seq_min:
        req = "http://api.steampowered.com/IDOTA2Match_570/GetMatchHistoryBySequenceNum/v0001?" \
              "key=%s&start_at_match_seq_num=%s&matches_requested=25" %\
              (APIKEY, match_seq_min)

    else:
        req = "http://api.steampowered.com/IDOTA2Match_570/GetMatchHistoryBySequenceNum/v0001?" \
              "key=%s&matches_requested=25" % APIKEY
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


def add_matches(session, connection, match_list_json, existing_match_ids=None, match_seq_min=0):
    # TODO filter out ridiculous games
    # this includes not 5v5
    # games with abandoned player
    # maybe have some way to filter stomps out of model, but keep data?
    # TODO filter out lobby_type 1, 3, 4 practice, coop and tutorial
    existing_match_ids = existing_match_ids or []
    matches = [match["match_id"] for match in match_list_json["result"]["matches"]
               if match["start_time"] > MIN_START and match["match_id"] not in existing_match_ids]
    if not matches:
        print("All were existing matches")
    #matches = [3066069898]
    for match_id in matches:
        try:
            match_data = get_match_details_open_dota(match_id)
        except:  # seems opendota just doesnt have some games
            print("Open dota 404 for match: ", match_id)
            continue


        # Seems that may be hitting a max_size issue with postgres json?
        # It just silently fails executing the insert for 3066016949...why?
        match_seq_min = max(match_seq_min, match_data["match_seq_num"])
        with open("/home/jdog/Documents/starttimes", "a+") as f:
            f.write(str(match_seq_min))
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
        existing_match_ids.append(match_id)
    # TODO feels bad returning these. seems a very 'side-effecty' function
    # maybe make match consumer object with these attributes?
    return match_seq_min, existing_match_ids


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
    #leagues = get_all_leagues()
    #match_seq_min = 3078157620
    match_seq_min = 2684125270
    # TODO progromatically save what match_seq_num I stopped at. (cannot just query latest match_id in db)
    while True:
        allpick_matches = get_match_sequence(match_seq_min)
        #allpick_matches = get_vhigh_skill_matches(match_seq_min, 44, game_mode=1)
        #print(allpick_matches)
        new_match_seq_min, existing_match_ids = add_matches(session, connection, allpick_matches, existing_match_ids,
                                                           match_seq_min)
        if new_match_seq_min == match_seq_min:
            #print("No new results. probably reached the present")
            # usually actually because all the results in 500 block didnt meet our criteria
            #break
            match_seq_min += 25
        else:
            match_seq_min = new_match_seq_min
        print("new min start: %s" % match_seq_min)
    # for league in reversed(leagues):
        # match_list_json = get_league_match_list(league["leagueid"])
    #     add_matches(session, connection, league["leagueid"], existing_match_ids, 1483228800)  #2017-01-01

if __name__ == "__main__":
    main()
