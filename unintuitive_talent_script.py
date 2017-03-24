import time

from selenium import webdriver
driver = webdriver.Chrome()


def main():
    driver.get("http://www.dotabuff.com/heroes")
    hero_links = driver.find_elements_by_xpath("//div[@class='hero-grid']/a")
    hero_hrefs = [anchor.get_attribute("href") for anchor in hero_links]
    underpicked_talents = overpicked_talents = []
    for hero_href in hero_hrefs:
        check_talent_winrates(hero_href, underpicked_talents, overpicked_talents)
        print(underpicked_talents)
        print(overpicked_talents)
        time.sleep(20)
    driver.quit()


def check_talent_winrates(hero_href, underpicked_talents, overpicked_talents):
    driver.get(hero_href)
    time.sleep(15)
    driver.find_elements_by_xpath("//a[text()='Ability Builds']")[0].click()
    time.sleep(10)
    talent_box = driver.find_elements_by_xpath("//article[@class='show-hero-talents']")[0]
    talent_rows = talent_box.find_elements_by_xpath("talent-data-row")
    hero_name = hero_href.split("/")[~1]
    for row in talent_rows:
        data = row.find_elements_by_class("talent-pw-data")
        pick_rate = data.find_elements_by_class("talent-pick-rate").text()
        pick_rate = pick_rate.split("%")[0]
        name = data.find_elements_by_class("talent-name").text()
        winrate = data.find_elements_by_class("talent-win-rate").text() # cb-enabled"
        winrate = winrate.split("%")[0]
        winrate = float(winrate[1:]) if winrate[0] == "+" else - float(winrate[1:])
        pick_dic = {
            "winrate": winrate,
            "pick_rate": pick_rate,
            "name": name,
            "hero": hero_name
        }
        if winrate > 0 and pick_rate < 50:
            underpicked_talents.append(pick_dic)
        elif winrate < 0 and pick_rate > 50:
            overpicked_talents.append(pick_dic)

if __name__ == '__main__':
    main()
