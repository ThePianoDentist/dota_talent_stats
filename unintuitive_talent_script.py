import time

import json
from selenium import webdriver

chrome_opts = webdriver.ChromeOptions()
# needed because of insane ad-js on dotabuff pretty much just breaking selenium
chrome_opts.add_extension('ublock_1_11_4.crx')
driver = webdriver.Chrome(chrome_options=chrome_opts)


def main():
    driver.get("http://www.dotabuff.com/heroes")
    hero_links = driver.find_elements_by_xpath("//div[@class='hero-grid']/a")
    hero_hrefs = [anchor.get_attribute("href") for anchor in hero_links]
    underpicked_talents = []
    overpicked_talents = []
    best_relative_winrate = []
    for hero_href in hero_hrefs:
        check_talent_winrates(hero_href, underpicked_talents, overpicked_talents, best_relative_winrate)
        print(underpicked_talents)
        print(overpicked_talents)
        time.sleep(3)
    driver.quit()
    underpicked_talents = sorted(underpicked_talents, key=lambda x: x["winrate"], reverse=True)
    overpicked_talents = sorted(overpicked_talents, key=lambda x: x["winrate"])
    out_json = {"underpicked": underpicked_talents,
                "overpicked": overpicked_talents,
                "best": best_relative_winrate
                }

    for tal in overpicked_talents:
        tal["overall_choice"] = round(((tal["winrate"]) * (tal["pick_rate"] - 50)), 2)
    out_json["overall_choice"] = sorted(overpicked_talents, key=lambda x: x["overall_choice"])
    out = json.dumps(out_json)
    with open("/home/jdog/Documents/unintuitive_talents4", "w+") as f:
        f.write(out)


def check_talent_winrates(hero_href, underpicked_talents, overpicked_talents, best_relative_winrate):
    driver.get(hero_href)
    time.sleep(10)
    driver.find_elements_by_xpath("//a[text()='Ability Builds']")[0].click()
    time.sleep(10)
    talent_box = None
    while not talent_box:
        try:
            talent_box = driver.find_elements_by_xpath("//article[@class='show-hero-talents']")[0]
        except:
            continue
    talent_rows = talent_box.find_elements_by_class_name("talent-data-row")
    hero_name = hero_href.split("/")[~0]
    for row in talent_rows:
        both_talents = row.find_elements_by_class_name("talent-pw-data")
        for i, data in enumerate(both_talents):
            pick_rate = data.find_elements_by_class_name("talent-pick-rate")[0].text
            pick_rate = float(pick_rate.split("%")[0])
            name = data.find_elements_by_class_name("talent-name")[0].text
            other_name = both_talents[~i].find_elements_by_class_name("talent-name")[0].text
            winrate = data.find_elements_by_class_name("talent-win-rate")[0].text  # cb-enabled"
            winrate = winrate.split("%")[0]
            winrate = float(winrate[1:]) if winrate[0] == "+" else - float(winrate[1:])
            pick_dic = {
                "hero": hero_name,
                "name": name,
                "winrate": winrate,
                "pick_rate": pick_rate,
                "other_choice": other_name,
            }
            if winrate > 0 and pick_rate < 50:
                underpicked_talents.append(pick_dic)
            elif winrate < 0 and pick_rate > 50:
                overpicked_talents.append(pick_dic)

            if len(best_relative_winrate) < 5:
                best_relative_winrate.append(pick_dic)
            # this isnt efficient. but its a throaway script. and small sizes
            elif winrate > min(best_relative_winrate, key=lambda x: x["winrate"])["winrate"]:
                best_relative_winrate.remove(min(best_relative_winrate, key=lambda x: x["winrate"]))
                best_relative_winrate.append(pick_dic)

if __name__ == '__main__':
    main()
