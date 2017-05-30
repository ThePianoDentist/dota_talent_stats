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
    current_match_id = None
    our_team = None
    current_match_players = []
    for _match_id, _win, _hero_id, _ability_upgrades in match_dicts:
        if _hero_id == our_hero.id:
            outputs.append(1.0 if _win else 0.0)
            our_team = _win
        if _match_id != current_match_id:
            # 113 possible friendly heroes. 113 possible enemies. 4 talent choices
            single_input = numpy.empty(230)
            single_input.fill(-1.0)
            for player in current_match_players:
                if our_team is None:
                    continue
                friendly = our_team == player["win"]
                # if player["hero_id"] != our_hero.id:
                single_input[DiscreteHeroModel.hero_id_to_index(player["hero_id"], our_hero.id, friendly)] = 1.0

                # TODO is it possible in the game to upgrade abilities out of order?
                if not player["ability_upgrades"]:
                    #print("No ability upgrades!!!!!")
                    continue
                talent_upgrades = [upgrade for upgrade in player["ability_upgrades"] if upgrade >= MINIMUM_TALENT_ID]

                if player["hero_id"] != our_hero.id:
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
                    #print("No. of 1's in hero slots: ", numpy.count_nonzero(single_input[:-4] == 1))
                    continue
                    #raise Exception("Invalid number of players set")  # think have 1v1s in db
                else:
                    inputs.append(single_input)
            current_match_players = []
            our_team = None

        current_match_id = _match_id

        player = {"win": _win, "hero_id": _hero_id, "ability_upgrades": _ability_upgrades}
        current_match_players.append(player)
    return inputs[1:-1], outputs[1:]  # hack for now. work out why one getting missed


def main():

    parser = argparse.ArgumentParser("Find best talent-tree for this match")
    parser.add_argument('hero_id', default=44, help="Id of hero you are playing",
                        type=int, nargs='?')
    args = parser.parse_args()
    model_attempts = 1
    # keras extends theano
    # http://machinelearningmastery.com/introduction-python-deep-learning-library-keras/
    # http://machinelearningmastery.com/tutorial-first-neural-network-python-keras/
    connection, session = connect_postgres()
    data_query = """select player->'match_id' as match_id,
     ((player->>'isRadiant')::boolean = (player->>'radiant_win')::boolean) as win,
      player->'hero_id' as hero_id,
       player->'ability_upgrades_arr' as ability_upgrades_arr
        from (select jsonb_array_elements(data->'players') as player
         from matches limit 500000) as t;"""

    session.execute(data_query)
    query_results = session.fetchall()
    # with open(os.getcwd() + "/open_dota_example.json", "r+") as f:
    #     match_dicts = [json.loads(f.read())]
    our_hero = Hero(args.hero_id, "pa", session)
    print("Analysing best talents for %s" % our_hero.name)
    inputs, outputs = filter_useful_data(query_results, our_hero)

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
