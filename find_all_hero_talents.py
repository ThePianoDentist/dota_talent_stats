import json

import os

from constants import MINIMUM_TALENT_ID
from get_data import connect_postgres


def main():
    connection, session = connect_postgres()
    # Start with nearest matches as patches have tweaked talent stuff
    session.execute("SELECT data FROM matches order by id desc")
    match_dicts = [row[0] for row in session.fetchall()]
    # with open(os.getcwd() + "/hero_ids.json", "r+") as f:
    #     heroes = json.loads(f.read())

    print("Adding new talent")
    session.execute("SELECT hero, COUNT(*) FROM talents GROUP BY hero")
    counts = session.fetchall()
    filled_heros = [row[0] for row in counts if row[1] == 8]
    print("Filled heros: %s" % filled_heros)
    for d in match_dicts:
        for player in d["players"]:
            if player["hero_id"] in filled_heros:
                continue

            ability_upgrades = player["ability_upgrades_arr"]
            if not ability_upgrades:
                continue
            talent_upgrades = [upgrade for upgrade in ability_upgrades if upgrade >= MINIMUM_TALENT_ID]
            for i, talent in enumerate(talent_upgrades):
                # TODO should I need to index any of these columns?
                try:
                    print(player["hero_id"])
                    print("talent: ", talent)
                    with open("ability_ids.json", "r+") as f:
                        talent_json = json.loads(f.read())
                        talent_str = talent_json[str(talent)]

                    with open("abilities.json", "r+") as f:
                        abilities = json.loads(f.read())
                        talent_long = abilities[talent_str]["dname"]
                except:
                    import pdb;
                    pdb.set_trace()
                session.execute("INSERT INTO talents (hero, level, id, name, long_name) SELECT {0}, {1}, {2}, '{3}', '{4}' "
                                "WHERE NOT EXISTS(SELECT * FROM talents WHERE "
                                "hero = {0} AND level = {1} AND id = {2})".format
                                (player["hero_id"], i + 1, talent, talent_str, talent_long))
                connection.commit()

                session.execute("SELECT COUNT(*) FROM talents WHERE hero = %s" % player["hero_id"])
                count = session.fetchall()[0][0]
                if count == 8:
                    print("Filled talents for hero %s" % player["hero_id"])
                    filled_heros.append(player["hero_id"])

if __name__ == "__main__":
    main()
