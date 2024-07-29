from pathlib import Path
from datetime import datetime, timedelta
import re
import random

import scrapy
from scrapy.selector import Selector
from scrapy_playwright.page import PageMethod
from scrapy.utils.response import response_status_message
from twisted.internet.error import TimeoutError
from scrapy import signals
from scrapy.spiders import Spider


class FlightsPlaySpider(scrapy.Spider):
    name = 'flights_play'
    base_url = "https://www.xcontest.org/world/en/flights/daily-score-pg/"
    fragment_tmplt = "#filter[date]={date}@filter[country]=CZ@filter[detail_glider_catg]=FAI3"
    
    def get_response_spec(self, url, dont_filter):
        return scrapy.Request(
            url=url,
            callback=self.parse,
            errback=self.errback_close_page,
            dont_filter=dont_filter,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context": "new",
                "playwright_context_kwargs": {
                    "proxy": {"server": "http://35.185.196.38:3128"} # "http://35.185.196.38:3128" "http://163.172.33.137:4671" "http://35.185.196.38:3128"
                },
                'playwright_page_methods': [
                    PageMethod('wait_for_selector', '//table[contains(@class, "XClist")]'),
                ]
            }
        )

    def start_requests(self):
        start_date = getattr(self, "start_date", None)
        end_date = getattr(self, "end_date", None)
        for date in date_range(start_date, end_date):
            url = self.base_url + self.fragment_tmplt.format(date=date)
            yield self.get_response_spec(url, True)

    async def parse(self, response):
        page = response.meta['playwright_page']
        content = await page.content()
        selector = Selector(text=content)
        date_str = re.search(r'filter\[date\]=(\d{4}-\d{2}-\d{2})', response.url).group(1)
        table = selector.xpath('//table[contains(@class, "XClist")]')
        flights = table.xpath('.//tbody/tr')
        flight_counter = 0
        for flight in flights:
            flight_counter += 1
            yield {
                'date': date_str,
                'start_time': flight.xpath('.//td[2]//div/em/text()').get().strip(),
                'pilot': flight.xpath('./td[3]/div/a/b/text()').get().strip(),
                'launch': flight.xpath('.//td[4]//div[@class="full"]/a/text()').get().strip(),
                'type': flight.xpath('.//td[5]//text()').get().strip(),
                'lenght': float(flight.xpath('.//td[6]//text()').get().strip()),
                'points': float(flight.xpath('.//td[7]//text()').get().strip()),
                'glider_cat': flight.xpath('.//td[9]//text()').get().strip(),
                'glider': flight.xpath('.//td[9]//div/@title').get().strip(),
                'flight_id': int(flight.xpath('./@id').get().strip().replace("flight-", "")),
            }
        await page.close()
        if flight_counter == 100:
            next_url = increment_start_filter(response.url)
            yield self.get_response_spec(next_url, True)         

    async def errback_close_page(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()


def date_range(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    date_list = []
    current_date = start
    while current_date <= end:
        date_list.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    return date_list


def increment_start_filter(url):
    match = re.search(r'(\d+)$', url)
    if match:
        number = int(match.group(1))
        incremented_number = number + 100
        return url[:match.start()] + str(incremented_number)
    else:
        return url