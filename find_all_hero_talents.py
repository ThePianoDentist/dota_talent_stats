import json

import os

from constants import MINIMUM_TALENT_ID
from get_data import connect_postgres


def main():
    connection, session = connect_postgres()
    session.execute("SELECT data FROM matches")
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
                #     INSERT
                #     INTO
                #     example_table
                #     (id, name)
                # SELECT
                # 1, 'John'
                # WHERE
                # NOT
                # EXISTS(
                #     SELECT
                # id
                # FROM
                # example_table
                # WHERE
                # id = 1
                # );
                # TODO should I need to index any of these columns?
                session.execute("INSERT INTO talents (hero, level, talent) SELECT {0}, {1}, {2} "
                                "WHERE NOT EXISTS(SELECT * FROM talents WHERE "
                                "hero = {0} AND level = {1} AND talent = {2})".format
                                (player["hero_id"], i + 1, talent))
                connection.commit()

                session.execute("SELECT COUNT(*) FROM talents WHERE hero = %s" % player["hero_id"])
                count = session.fetchall()[0][0]
                if count == 8:
                    print("Filled talents for hero %s" % player["hero_id"])
                    filled_heros.append(player["hero_id"])

if __name__ == "__main__":
    main()
