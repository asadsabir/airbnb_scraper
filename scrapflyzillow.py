import asyncio
import json
import re
from random import randint
from typing import List
from urllib.parse import urlencode
import pandas as pd
from loguru import logger as log
from parsel import Selector
from scrapfly import ScrapeConfig, ScrapflyClient


async def _search(query: str, session: ScrapflyClient, filters: dict = None, categories=("cat1", "cat2")) -> List[dict]:
    """base search function which is used by sale and rent search functions"""
    html_result = await session.async_scrape(
        ScrapeConfig(
            url=f"https://www.zillow.com/homes/{query}_rb/",
            proxy_pool="public_residential_pool",
            country="US",
            asp=True,
        )
    )
    query_data = json.loads(re.findall(r'"queryState":(\{.+}),\s*"filter', html_result.content)[0])
    if filters:
        query_data["filterState"] = filters
    url = "https://www.zillow.com/search/GetSearchPageState.htm?"
    found = []
    # cat1 - Agent Listings
    # cat2 - Other Listings
    for category in categories:
        full_query = {
            "searchQueryState": query_data,
            "wants": {category: ["mapResults"]},
            "requestId": randint(2, 10),
        }
        api_result = await session.async_scrape(
            ScrapeConfig(
                url=url + urlencode(full_query),
                proxy_pool="public_residential_pool",
                country="US",
                asp=True,
            )
        )
        data = json.loads(api_result.content)
        _total = data["categoryTotals"][category]["totalResultCount"]
        if _total > 500:
            log.warning(f"query has more results ({_total}) than 500 result limit ")
        else:
            log.info(f"found {_total} results for query: {query}")
        map_results = data[category]["searchResults"]["mapResults"]
        found.extend(map_results)
    return found


async def search_sale(query: str, session: ScrapflyClient) -> List[dict]:
    """search properties that are for sale"""
    log.info(f"scraping sale search for: {query}")
    return await _search(query=query, session=session)


async def search_rent(query: str, session: ScrapflyClient) -> List[dict]:
    """search properites that are for rent"""
    log.info(f"scraping rent search for: {query}")
    filters = {
        "isForSaleForeclosure": {"value": False},
        "isMultiFamily": {"value": False},
        "isAllHomes": {"value": True},
        "isAuction": {"value": False},
        "isNewConstruction": {"value": False},
        "isForRent": {"value": True},
        "isLotLand": {"value": False},
        "isManufactured": {"value": False},
        "isForSaleByOwner": {"value": False},
        "isComingSoon": {"value": False},
        "isForSaleByAgent": {"value": False},
    }
    return await _search(query=query, session=session, filters=filters, categories=["cat1"])


def parse_property(data: dict) -> dict:
    """parse zillow property"""
    # zillow property data is massive, let's take a look just
    # at the basic information to keep this tutorial brief:
    parsed = {
        "address": data["address"],
        "description": data["description"],
        "photos": [photo["url"] for photo in data["galleryPhotos"]],
        "zipcode": data["zipcode"],
        "phone": data["buildingPhoneNumber"],
        "name": data["buildingName"],
        # floor plans include price details, availability etc.
        "floor_plans": data["floorPlans"],
    }
    return parsed


async def scrape_properties(urls: List[str], session: ScrapflyClient):
    """scrape zillow properties"""

    async def scrape(url):
        result = await session.async_scrape(
            ScrapeConfig(url=url, asp=True, country="US", proxy_pool="public_residential_pool")
        )
        response = result.upstream_result_into_response()
        sel = Selector(text=response.text)
        data = sel.css("script#__NEXT_DATA__::text").get()
        data = json.loads(data)
        return parse_property(data["props"]["initialReduxState"]["gdp"]["building"])

    return await asyncio.gather(*[scrape(url) for url in urls])


async def run():
    with ScrapflyClient(key="4ab31e27b5434b7d94c3fb126e380912", max_concurrency=10) as session:
        rentals = await search_rent("Richardson, TX", session)
        sales = await search_sale("Richarcdson, TX", session)
        property_data = await scrape_properties(
            ["https://www.zillow.com/b/aalto57-new-york-ny-5twVDd/"], session=session
        )
        rentaldf = pd.DataFrame(rentals)
        salesdf = pd.DataFrame(sales)
        propertydf = pd.DataFrame(property_data)
        
        rentaldf.to_csv('rentals.csv')
        salesdf.to_csv('sales.csv')
        propertydf.to_csv('properties.csv')
        print(len(rentaldf))
        print(len(salesdf))
        print(len(propertydf))

asyncio.run(run())