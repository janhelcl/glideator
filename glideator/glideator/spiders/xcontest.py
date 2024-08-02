from datetime import datetime, timedelta
import re
import random
import time

import scrapy
from scrapy.selector import Selector
from scrapy_playwright.page import PageMethod
from playwright.async_api import TimeoutError


class FlightsSpider(scrapy.Spider):
    name = 'flights'
    base_url = "https://www.xcontest.org/{year}world/en/flights/daily-score-pg/"
    fragment = "#filter[date]={date}@filter[country]=CZ@filter[detail_glider_catg]=FAI3"
    max_retries = 5
    sleep_on_timeout = 60 * 5
    dates_in_process = []
    failed_rls = []
    
    def resolve_url(self, date):
        dt = datetime.strptime(date, "%Y-%m-%d")
        dt_now = datetime.now()
        if dt.month >= 10:
            year = dt.year+1
        else:
            year = dt.year
        if year == dt_now.year:
            year = ""
        else:
            year = f"{year}/"
        return self.base_url.format(year=year) + self.fragment.format(date=date)

    def get_request_spec(self, url, date, retry_times=0):
        return scrapy.Request(
            url=url,
            callback=self.parse,
            errback=self.errback_close_page,
            dont_filter=True,
            meta={
                "date": date,
                "retry_times": retry_times,
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context": "XC",
                "playwright_context_kwargs": {
                    "proxy": {"server": "http://35.185.196.38:3128"} # "http://35.185.196.38:3128" "http://163.172.33.137:4671" "http://34.122.187.196:80"
                },
                'playwright_page_methods': [
                    PageMethod('wait_for_selector', '//table[contains(@class, "XClist")]'),
                    PageMethod('wait_for_timeout', random.uniform(15, 30) * 1000)
                ]
            }
        )

    def start_requests(self):
        start_date = getattr(self, "start_date", None)
        end_date = getattr(self, "end_date", None)
        for date in date_range(start_date, end_date):
            self.dates_in_process.append(date)
            time.sleep(random.uniform(3, 5))
            url = self.resolve_url(date)
            yield self.get_request_spec(url, date)

    async def parse(self, response):
        page = response.meta['playwright_page']
        content = await page.content()
        selector = Selector(text=content)
        date = response.meta['date']
        table = selector.xpath('//table[contains(@class, "XClist")]')
        flights = table.xpath('.//tbody/tr')
        flight_counter = 0
        for flight in flights:
            flight_counter += 1
            yield {
                'date': date,
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
            yield self.get_request_spec(next_url, date)
        else:
            self.dates_in_process.remove(date)
   
    async def errback_close_page(self, failure):
        page = failure.request.meta["playwright_page"]
        date = failure.request.meta["date"]
        await page.close()
        if failure.check(TimeoutError):
            self.logger.error(f'TimeoutError on date: {failure.request.meta["date"]}, url: {failure.request.url}')
            self.logger.error(repr(failure))
            retries = failure.request.meta.get('retry_times', 0) + 1
            if retries <= self.max_retries:
                self.logger.info(f'Sleeping after TimeoutError on {failure.request.url} for {self.sleep_on_timeout}s')
                time.sleep(self.sleep_on_timeout)
                self.logger.debug(f"Retrying {failure.request} (failed {retries} times) due to timeout.")
                yield self.get_request_spec(failure.request.url, date, retry_times=retries)
            else:
                self.logger.debug(f"Gave up retrying {failure.request} (failed {retries} times) due to timeout.")
                self.failed_rls.append((date, failure.request.url))
        else:
            self.logger.error(f'Error on date: {date}, url: {failure.request.url}')
            self.logger.error(repr(failure))
            self.failed_rls.append((date, failure.request.url))

    def closed(self, reason):
        self.logger.info(f'Unprocessed requests: {sorted(self.failed_rls)}')
        self.logger.info(f'Days in processing: {sorted(self.dates_in_process)}')


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
    pattern = r'@flights\[start\]=(\d+)'
    match = re.search(pattern, url)
    if match:
        number = int(match.group(1))
        new_number = number + 100
        updated_url = re.sub(pattern, f'@flights[start]={new_number}', url)
    else:
        updated_url = url + '@flights[start]=100'
    return updated_url
