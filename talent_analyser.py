import json

import os
import itertools

import argparse
import random

import numpy

from constants import MINIMUM_TALENT_ID
from get_data import connect_postgres
from machine_learner import Net, DiscreteHeroModel



class Talent:
    # TODO issue: when patches occur. talent 'updates' get whole new ids.
    # simple solution. only use latest patch as dataset
    # not viable right after patches

    # Until sorted this only test models on 'unpatched' heroes
    def __init__(self, hero_id, level, id, name, long_name):
        self.hero_id = hero_id
        self.level = level
        self.id = id
        self.name = name
        self.long_name = long_name


class Hero:

    def __init__(self, hero_id, name, session):
        self.id = hero_id
        self.name = name
        self.talents = self.get_talents_for_hero(session)

    def get_talents_for_hero(self, session):
        session.execute("SELECT level, id, name, long_name FROM talents WHERE hero = %s ORDER BY level, id" % self.id)
        rows = session.fetchall()
        return [
            (Talent(self.id, *rows[0]), Talent(self.id, *rows[1])),
            (Talent(self.id, *rows[2]), Talent(self.id, *rows[3])),
            (Talent(self.id, *rows[4]), Talent(self.id, *rows[5])),
            (Talent(self.id, *rows[6]), Talent(self.id, *rows[7]))
        ]


def filter_useful_data(match_dicts, our_hero):
    inputs = []
    outputs = []
    for d in match_dicts:
        # hmmmmm turns out open dota api has null values (that shouldnt be null) for loads of fields
        # this is usually null! I should bug report
        # in meantime can work around as can still access hero_id
        # if not d["picks_bans"]:  # TODO why no pickbans????
        #     print("No pickban!!!")
        #     continue
        players = d["players"]
        our_team = None
        for p in players:
            if p["hero_id"] == our_hero.id:
                our_team = p["isRadiant"]
                break
        # picks = [pb for pb in d["picks_bans"] if pb["is_pick"]]
        # our_team = None
        # for pick in picks:
        #     if pick["hero_id"] == our_hero.id:
        #         our_team = pick["team"]  # 0 for radiant? 1 for dire I think
        #         break
        if our_team:
            # 113 possible friendly heros. 113 possible enemies. 4 talent choices
            single_input = numpy.empty(230)
            single_input.fill(-1.0)
            for p in players:
                friendly = (p["isRadiant"] == our_team)
                if p["hero_id"] != our_hero.id:
                    single_input[DiscreteHeroModel.hero_id_to_index(p["hero_id"], our_hero.id, friendly)] = 1.0

            # TODO is it possible in the game to upgrade abilities out of order?
            ability_upgrades = [player["ability_upgrades_arr"] for player in d["players"]
                                if player["hero_id"] == our_hero.id][0]
            if not ability_upgrades:
                #print("No ability upgrades!!!!!")
                continue
            talent_upgrades = [upgrade for upgrade in ability_upgrades if upgrade >= MINIMUM_TALENT_ID]
            single_input[-4:] = 0.0
            for i, talent in enumerate(talent_upgrades):
                if talent == our_hero.talents[i][0].id:
                    single_input[226 + i] = -1.0
                elif talent == our_hero.talents[i][1].id:
                    single_input[226 + i] = 1.0
                else:
                    # This case it seems you can skill talents out of order
                    # i dont think we want these weeeeeeird builds in results anyway
                    continue
                    # raise Exception("Talent: %s did not match any registered for hero: %s" %
                    #                 (talent, our_hero.name))

            if numpy.count_nonzero(single_input[:-4] == 1) != 9:
                print("No. of 1's in hero slots: ", numpy.count_nonzero(single_input[:-4] == 1))
                continue
                #raise Exception("Invalid number of players set")  # think have 1v1s in db
            else:
                inputs.append(single_input)

            outputs.append(1.0 if (d["radiant_win"] == our_team) else 0.0) # todo our_team to isradiant

    return inputs, outputs


def main():

    parser = argparse.ArgumentParser("Find best talent-tree for this match")
    parser.add_argument('hero_id', default=44, help="Id of hero you are playing",
                        type=int, nargs='?')
    args = parser.parse_args()
    model_attempts = 5
    # keras extends theano
    # http://machinelearningmastery.com/introduction-python-deep-learning-library-keras/
    # http://machinelearningmastery.com/tutorial-first-neural-network-python-keras/
    connection, session = connect_postgres()
    session.execute("SELECT data FROM matches")
    match_dicts = [row[0] for row in session.fetchall()]
    # with open(os.getcwd() + "/open_dota_example.json", "r+") as f:
    #     match_dicts = [json.loads(f.read())]
    our_hero = Hero(args.hero_id, "pa", session)
    print("Analysing best talents for %s" % our_hero.name)
    inputs, outputs = filter_useful_data(match_dicts, our_hero)

    def split_training_data(inputs, outputs):
        zipped = list(zip(inputs, outputs))
        random.shuffle(zipped)  # do I need to check this is random enough
        training_data = zipped[:len(zipped)//2]
        test_data = zipped[len(zipped)//2:]
        inputs, outputs = zip(*training_data)
        test_inputs, test_outputs = zip(*test_data)
        return inputs, outputs, test_inputs, test_outputs

    model_inaccuracies = []
    for i in range(model_attempts):
        _inputs, _outputs, _test_inputs, _test_outputs = split_training_data(inputs, outputs)
        net = DiscreteHeroModel(_inputs, _outputs, test_inputs=_test_inputs, test_outputs=_test_outputs)
        net.evaluate()

        print("Neuron recommended upper limit: ", net.neuron_upper_limit)

        friendly_heroes = [1, 18, 17, 14]  # TODO heroes should be arguments
        enemy_heroes = [5, 80, 7, 66, 20]
        net.predict(our_hero, friendly_heroes, enemy_heroes)
        average_innac = net.test()
        model_inaccuracies.append(average_innac)
        print("Inaccuracy: ", average_innac)
    overall_inaccuracy = sum(model_inaccuracies) / len(model_inaccuracies)
    std_dev = numpy.std(model_inaccuracies)
    print("Average Inaccuracy: ", overall_inaccuracy)
    print("std_dev: ", std_dev)  # i believe a higher std dev will indicate just lack of samples
    # rather than model flaw

    # extra params for future consideration:
    """
    are we ahead or behind when we go to level up the talent?
    what talents did our team-mates get?
    what items do we and our opponents have?
    what players are we playing against?
    """

if __name__ == "__main__":
    main()
