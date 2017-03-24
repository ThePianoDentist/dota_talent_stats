import json

import os

import numpy

from constants import MINIMUM_TALENT_ID
from get_data import connect_postgres
from machine_learner import Net, DiscreteHeroModel


class Hero:

    def __init__(self, hero_id, name, session):
        self.id = hero_id
        self.name = name
        self.talents = self.get_talents_for_hero(session)

    def get_talents_for_hero(self, session):
        session.execute("SELECT level, talent FROM talents WHERE hero = %s ORDER BY level" % self.id)
        rows = session.fetchall()
        # TODO make sure the same level talents come ordered same way every time
        return [
            (rows[0][1], rows[1][1]), (rows[2][1], rows[3][1]),
            (rows[4][1], rows[5][1]), (rows[6][1], rows[7][1])
        ]


def hero_id_to_index(hero_id, our_hero_id, friendly):
    start = 0 if friendly else 113
    if hero_id < our_hero_id:
        return start + hero_id - 1  # hero_ids start at 1, not 0
    else:
        return start + hero_id - 2  # we 'jump over' our_hero in the array


def filter_useful_data(match_dicts, our_hero):
    inputs = []
    outputs = []
    for d in match_dicts:
        if not d["picks_bans"]:  # TODO why no pickbans????
            continue
        picks = [pb for pb in d["picks_bans"] if pb["is_pick"]]
        our_team = None
        for pick in picks:
            if pick["hero_id"] == our_hero.id:
                our_team = pick["team"]  # 0 for radiant? 1 for dire I think
                break

        if our_team:
            # 113 possible friendly heros. 113 possible enemies. 4 talent choices
            single_input = numpy.zeros(230)
            for pick in picks:
                friendly = (pick["team"] == our_team)
                single_input[hero_id_to_index(pick["hero_id"], our_hero.id, friendly)] = 1

            # TODO is it possible in the game to upgrade abilities out of order?
            ability_upgrades = [player["ability_upgrades_arr"] for player in d["players"]
                                if player["hero_id"] == our_hero.id][0]
            if not ability_upgrades:
                continue
            for x in ability_upgrades:
                print(x)
            talent_upgrades = [upgrade for upgrade in ability_upgrades if upgrade >= MINIMUM_TALENT_ID]
            single_input[~4:] = 0.5
            print("len(talent upgs): %s" % len(talent_upgrades))
            for i, talent in enumerate(talent_upgrades):
                if talent == our_hero.talents[i][0]:
                    single_input[226 + i] = 0
                elif talent == our_hero.talents[i][1]:
                    single_input[226 + i] = 1
                else:
                    raise Exception("Talent: %s did not match any registered for hero: %s" %
                                    (talent, our_hero.name))

            outputs.append(d["radiant_win"] == (our_team == 0))
            inputs.append(single_input)

    return inputs, outputs


def main():
    # keras extends theano
    # http://machinelearningmastery.com/introduction-python-deep-learning-library-keras/
    # http://machinelearningmastery.com/tutorial-first-neural-network-python-keras/
    connection, session = connect_postgres()
    #matches = session.query(Match).all()
    session.execute("SELECT data FROM matches")
    match_dicts = [row[0] for row in session.fetchall()]
    # with open(os.getcwd() + "/open_dota_example.json", "r+") as f:
    #     match_dicts = [json.loads(f.read())]
    our_hero = Hero(86, "rubick", session)
    inputs, outputs = filter_useful_data(match_dicts, our_hero)
    net = DiscreteHeroModel(inputs, outputs)
    net.evaluate()
    # extra params for future consideration:
    """
    are we ahead or behind when we go to level up the talent?
    what talents did our team-mates get?
    what items do we and our opponents have?
    what players are we playing against?
    """

if __name__ == "__main__":
    main()
