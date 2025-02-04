import time

import requests
from bs4 import BeautifulSoup, ResultSet, Tag


def advs():
    p = 0
    j = 0
    for i in range(1, 6):
        p +=1
        response = requests.get(f"https://www.olx.ua/uk/list/?page={i}", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        adv_cards: ResultSet[Tag] = soup.select('div[data-testid="l-card"]')
        print(f"Response page {p} status code: {response.status_code}")
        for card in adv_cards:
            j += 1
            ad_url = card.select_one('div[data-cy="ad-card-title"] a')
            if ad_url:
                title = card.select_one('div[data-cy="ad-card-title"] a > h4').text
                # print(ad_url)

                print(f"Page {p} :", f"Ad {j} {title} {ad_url.get('href')}")
        time.sleep(1)


if __name__ == "__main__":
    advs()
