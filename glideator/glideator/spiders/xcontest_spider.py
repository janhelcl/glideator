from pathlib import Path
from datetime import datetime, timedelta, timezone
import re
import random

import scrapy
from scrapy.selector import Selector
from scrapy_playwright.page import PageMethod


class FlightsSpider(scrapy.Spider):
    name = 'flights'
    start_urls = ["https://www.xcontest.org/world/en/flights/daily-score-pg/"]
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        # Add more user agents as needed
    ]

    
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                headers={'User-Agent': random.choice(self.user_agents)},
                errback=self.errback_close_page,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context": "new",
                    "playwright_context_kwargs": {
                        "proxy": {"server": "http://35.185.196.38:3128"} # "http://163.172.33.137:4671" "http://35.185.196.38:3128"
                    },
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', '#flights > div.XCslotFilter > form'),
                        PageMethod('select_option', '//*[@id="flights"]/div[1]/form/fieldset/table/tbody/tr/td[1]/select', '2024-07-19'),
                        PageMethod('select_option', '//*[@id="flights"]/div[1]/form/fieldset/table/tbody/tr/td[2]/select', 'CZ'),
                        PageMethod('select_option', '//*[@id="flights"]/div[1]/form/fieldset/table/tbody/tr/td[3]/select', 'FAI3'),
                        PageMethod('wait_for_timeout', 5000),
                    ]
                }
            )

    async def parse(self, response):
        page = response.meta['playwright_page']
        content = await page.content()
        selector = Selector(text=content)
        await page.close()
        date_str = re.search(r'filter\[date\]=(\d{4}-\d{2}-\d{2})', response.url).group(1)
        table = selector.xpath('//table[contains(@class, "XClist")]')
        flights = table.xpath('.//tbody/tr')
        for flight in flights:
            yield { 
                'start_time': _parse_start_time(flight, date_str),
                'pilot': flight.xpath('./td[3]/div/a/b/text()').get().strip(),
                'launch': flight.xpath('.//td[4]//div[@class="full"]/a/text()').get().strip(),
                'type': flight.xpath('.//td[5]//text()').get().strip(),
                'lenght': float(flight.xpath('.//td[6]//text()').get().strip()),
                'points': float(flight.xpath('.//td[7]//text()').get().strip()),
                # 'duration': _parse_duration(flight),
                'glider_cat': flight.xpath('.//td[9]//text()').get().strip(),
                'glider': flight.xpath('.//td[9]//div/@title').get().strip()
            }

    async def errback_close_page(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()


def _parse_start_time(flight, date_str):
    """
    #TODO
    """
    time_part = flight.xpath('.//td[2]//div/em/text()').get().strip()
    utc_offset = flight.xpath('.//td[2]//div/span[@class="XCutcOffset"]/text()').get().strip()
    datetime_str = f"{date_str} {time_part}"
    tz = _parse_time_zone(utc_offset)
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=tz)


def _parse_time_zone(timezone_str):
    """
    #TODO
    """
    timezone_str = timezone_str[1:]
    sign = timezone_str[3]
    hours = int(timezone_str[4:6])
    minutes = int(timezone_str[7:])
    total_minutes = hours * 60 + minutes
    if sign == '-':
        total_minutes = -total_minutes
    offset = timedelta(minutes=total_minutes)
    return timezone(offset)


def _parse_duration(flight):
    """
    #TODO
    """
    dur_str1 = flight.xpath('.//td[8]//span[@class="d0"]//text()').get()
    dur_str2 = flight.xpath('.//td[8]//span[@class="d1"]//text()').get()
    dur_str = dur_str1 + dur_str2
    hours, minutes = dur_str.replace(" ", "").split(':')
    return int(hours) * 60 + int(minutes)
    
