from pathlib import Path
from datetime import datetime, timedelta, timezone
import re
import random

import scrapy
from scrapy.selector import Selector
from scrapy_playwright.page import PageMethod


class FlightsSpider(scrapy.Spider):
    name = 'flights'
    base_url = "https://www.xcontest.org/world/en/flights/daily-score-pg/"
    
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
                    PageMethod('wait_for_timeout', 5000),
                ]
            }
        )

    def start_requests(self):
        url = self.base_url + f'#filter[date]=2024-07-20@filter[country]=CZ@filter[detail_glider_catg]=FAI3'
        yield self.get_response_spec(url, False)

    async def parse(self, response):
        page = response.meta['playwright_page']
        await page.wait_for_selector('//table[contains(@class, "XClist")]')
        await page.wait_for_selector('//div[contains(@class, "XCpager")]')
        content = await page.content()
        selector = Selector(text=content)
        await page.close()
        await page.context.close()
        date_str = re.search(r'filter\[date\]=(\d{4}-\d{2}-\d{2})', response.url).group(1)
        table = selector.xpath('//table[contains(@class, "XClist")]')
        flights = table.xpath('.//tbody/tr')
        for flight in flights:
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
        next_href = response.xpath('//div[contains(@class, "XCpager")]//a[contains(@title, "next page")]/@href').get().strip()
        next_url = self.base_url + next_href
        if next_url != response.url:
            yield self.get_response_spec(next_url, True)          

    async def errback_close_page(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()
        await page.context.close()
