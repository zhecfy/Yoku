import re
from urllib import parse
from bs4 import BeautifulSoup
import requests
from typing import List, Dict
import logging
import datetime

from yoku.consts import KEY_TITLE, KEY_BUYNOW_PRICE, KEY_CURRENT_PRICE, KEY_END_TIMESTAMP, KEY_IMAGE, KEY_ITEM_ID, KEY_POST_TIMESTAMP, KEY_START_PRICE, KEY_START_TIMESTAMP, KEY_URL

YAHUOKU_SEARCH_TEMPLATE = r"https://auctions.yahoo.co.jp/search/search?{query}"

# Auctions posted before ~2016 may use the user id in the image url, such as [userid]-img500x500-[unixtimestamp][randomstr].jpg
# Newer auctions used 'i' instead.
# POST_TIMESTAMP_REGEX = r"^.*i-img\d+x\d+-(\d{10}).*$"
POST_TIMESTAMP_REGEX = r"^.*-img\d+x\d+-(\d{10}).*$"
AUCTION_TIMESTAMP_REGEX = r"^.*etm=(\d{10}),stm=(\d{10}).*$"

def prettify_timestamp(timestamp: int) -> str:
    dt_object = datetime.datetime.fromtimestamp(timestamp).astimezone()
    formatted_date_time = dt_object.strftime("%Y-%m-%d %H:%M:%S %Z")
    return formatted_date_time

def get_raw_results(parameters: dict) -> str:
    """
    Return raw html page content of the results from the search query
    """

    if 'p' not in parameters:
        raise ValueError("No query provided")

    # Default search sorted by recommended
    if 's1' not in parameters and 'o1' not in parameters:
        parameters['s1'] = 'score2'
        parameters['o1'] = 'd'
    
    # start cannot be more than 15000
    parameters['b'] = 1
    parameters['n'] = 100

    parameters_list = []
    for key, value in parameters.items():
        if key == 'p':
            str_value = parse.quote_plus(value)
        else:
            str_value = str(value)
        parameters_list.append(str(key) + "=" + str_value)
    query = '&'.join(parameters_list)

    print (query)

    input()

    url = YAHUOKU_SEARCH_TEMPLATE.format(query=query)
    print(f"[GET] {url}")

    r = requests.get(url)

    return r.text


def parse_raw_results(raw: str) -> List[Dict]:
    """
    Parse a raw html page of search results and return a list of result dicts
    """

    if r"に一致する商品はありません。キーワードの一部を利用した結果を表示しています" in raw:
        # This happens when there are no exact matches and the query contained more than one space-seperated keyword.
        # Yahoo! Auctions will try searching using some of the keywords, so the result are usually useless.
        return []

    results = []
    soup = BeautifulSoup(raw, "lxml")

    product_details = soup.find_all("div", class_="Product__detail")
    for product_detail in product_details:
        product_bonuses = product_detail.find_all(
            "div", class_="Product__bonus")
        product_titlelinks = product_detail.find_all(
            "a", class_="Product__titleLink")

        if not product_bonuses or not product_titlelinks:
            # haven't seen this happen
            logging.error(f"Product__bonus or Product__titleLink not found. product_detail: {product_detail}")
            continue

        product_bonus = product_bonuses[0]
        product_titlelink = product_titlelinks[0]

        auction_title = product_titlelink["data-auction-title"]
        auction_img = product_titlelink["data-auction-img"]
        href = product_titlelink["href"]
        cl_params = product_titlelink["data-cl-params"]

        match = re.match(POST_TIMESTAMP_REGEX, auction_img)
        if not match:
            # print(auction_title, href)
            # print(f"POST_TIMESTAMP_REGEX not match, auction_img={auction_img}")
            # could happen to very old auctions
            post_timestamp = 0

        post_timestamp = int(match.group(1))

        match = re.match(AUCTION_TIMESTAMP_REGEX, cl_params)
        if not match:
            # haven't seen this happen
            logging.error(f"AUCTION_TIMESTAMP_REGEX not match, href={href}, cl_params={cl_params}")
            continue

        end_timestamp = int(match.group(1))
        start_timestamp = int(match.group(2))

        auction_id = product_bonus["data-auction-id"]
        auction_buynowprice = product_bonus["data-auction-buynowprice"]
        auction_price = product_bonus["data-auction-price"]
        auction_startprice = product_bonus["data-auction-startprice"]

        result = {
            KEY_TITLE: auction_title,
            KEY_IMAGE: auction_img,
            KEY_URL: href,

            KEY_POST_TIMESTAMP: prettify_timestamp(post_timestamp),
            KEY_END_TIMESTAMP: prettify_timestamp(end_timestamp),
            KEY_START_TIMESTAMP: prettify_timestamp(start_timestamp),

            KEY_ITEM_ID: auction_id,
            KEY_BUYNOW_PRICE: auction_buynowprice,
            KEY_CURRENT_PRICE: auction_price,
            KEY_START_PRICE: auction_startprice,
        }

        results.append(result)

    return results


def search(parameters: dict) -> List[Dict]:
    """
    Search for query and return a list of result dicts
    """

    raw = get_raw_results(parameters)

    return parse_raw_results(raw)
