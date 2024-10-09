from datetime import datetime, timedelta
import re
import random
import time

import scrapy
from scrapy.selector import Selector
from scrapy_playwright.page import PageMethod
from playwright.async_api import TimeoutError


class FlightsSpider(scrapy.Spider):
    """
    A Scrapy spider for scraping flight data from XContest.org.

    This spider crawls through daily flight records, extracting detailed information
    about each flight including pilot, launch site, flight type, distance, and more.

    Attributes:
        name (str): The name of the spider.
        base_url (str): The base URL for XContest flight data.
        fragment (str): URL fragment for filtering flights.
        max_retries (int): Maximum number of retry attempts for failed requests.
        sleep_on_timeout (int): Time to sleep (in seconds) after a timeout before retrying.
        dates_in_process (list): List of dates currently being processed.
        failed_rls (list): List of failed requests (date, URL pairs).
    """

    name = 'flights'
    base_url = "https://www.xcontest.org/{year}world/en/flights/daily-score-pg/"
    fragment = "#filter[date]={date}@filter[country]={country}@filter[detail_glider_catg]=FAI3"
    max_retries = 5
    sleep_on_timeout = 60 * 5
    dates_in_process = []
    failed_rls = []

    def current_contest_year(self):
        dt_now = datetime.now()
        if dt_now.month >= 10:
            return dt_now.year+1
        else:
            return dt_now.year
    
    def resolve_url(self, date, country):
        """
        Resolve the full URL for a given date.

        Args:
            date (str): The date in 'YYYY-MM-DD' format.

        Returns:
            str: The full URL for the given date.
        """
        dt = datetime.strptime(date, "%Y-%m-%d")
        dt_now = datetime.now()
        if dt.month >= 10:
            year = dt.year+1
        else:
            year = dt.year
        if year == self.current_contest_year():
            year = ""
        else:
            year = f"{year}/"
        return self.base_url.format(year=year) + self.fragment.format(date=date, country=country)

    def get_request_spec(self, url, date, country, retry_times=0):
        """
        Generate a Scrapy Request object with necessary metadata and Playwright configurations.

        Args:
            url (str): The URL to request.
            date (str): The date associated with the request.
            retry_times (int, optional): Number of times this request has been retried. Defaults to 0.

        Returns:
            scrapy.Request: A configured Scrapy Request object.
        """
        request = scrapy.Request(
            url=url,
            callback=self.parse,
            errback=self.errback_close_page,
            dont_filter=True,
            meta={
                "date": date,
                "country": country,
                "retry_times": retry_times,
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context": "XC",
                # "playwright_context_kwargs": {
                #     "proxy": {"server": "http://103.82.157.72:8080"}
                # },
                'playwright_page_methods': [
                    PageMethod('wait_for_selector', '//table[contains(@class, "XClist")]'),
                    PageMethod('wait_for_timeout', random.uniform(15, 30) * 1000)
                ]
            }
        )
        self.logger.debug(f"Created request for URL: {url}, meta: {request.meta}")
        return request

    def start_requests(self):
        """
        Initialize the spider by generating requests for each date in the specified range.

        Yields:
            scrapy.Request: A request for each date in the range.
        """
        start_date = getattr(self, "start_date", None)
        end_date = getattr(self, "end_date", None)
        country = getattr(self, "country", "CZ")
        for date in date_range(start_date, end_date):
            self.dates_in_process.append(date)
            time.sleep(random.uniform(3, 5))
            url = self.resolve_url(date, country)
            yield self.get_request_spec(url, date, country)

    async def parse(self, response):
        """
        Parse the response from each request, extracting flight data.

        Args:
            response (scrapy.http.Response): The response object.

        Yields:
            dict: Extracted flight data for each flight on the page.
        """
        self.logger.debug(f"Response meta: {response.meta}")
        page = response.meta['playwright_page']
        content = await page.content()
        selector = Selector(text=content)
        date = response.meta['date']
        country = response.meta['country']
        table = selector.xpath('//table[contains(@class, "XClist")]')
        flights = table.xpath('.//tbody/tr')
        flight_counter = 0
        for flight in flights:
            flight_counter += 1
            yield {
                'date': date,
                'country': country,
                'start_time': flight.xpath('.//td[2]//div/em/text()').get().strip(),
                'pilot': flight.xpath('./td[3]/div/a/b/text()').get().strip(),
                'launch': flight.xpath('.//td[4]//div[@class="full"]/a/text()').get(),
                'latitutde': extract_coordinate(flight.xpath('.//td[4]//div/a/@href').get().strip(), "latitude"),
                'longitude': extract_coordinate(flight.xpath('.//td[4]//div/a/@href').get().strip(), "longitude"),
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
            yield self.get_request_spec(next_url, date, country)
        else:
            self.dates_in_process.remove(date)
   
    async def errback_close_page(self, failure):
        """
        Handle errors during the scraping process, including timeouts and retries.

        Args:
            failure (twisted.python.failure.Failure): The failure object containing error details.

        Yields:
            scrapy.Request: A new request in case of a retry.
        """
        self.logger.debug(f"Failure meta: {failure.request.meta}")
        page = failure.request.meta["playwright_page"]
        date = failure.request.meta["date"]
        country = failure.request.meta["country"]
        await page.close()
        if failure.check(TimeoutError):
            self.logger.error(f'TimeoutError on date: {failure.request.meta["date"]}, url: {failure.request.url}')
            self.logger.error(repr(failure))
            retries = failure.request.meta.get('retry_times', 0) + 1
            if retries <= self.max_retries:
                self.logger.info(f'Sleeping after TimeoutError on {failure.request.url} for {self.sleep_on_timeout}s')
                time.sleep(self.sleep_on_timeout)
                self.logger.info(f"Retrying {failure.request} (failed {retries} times) due to timeout.")
                yield self.get_request_spec(failure.request.url, date, country, retry_times=retries)
            else:
                self.logger.info(f"Gave up retrying {failure.request} (failed {retries} times) due to timeout.")
                self.failed_rls.append((date, failure.request.url))
        else:
            self.logger.error(f'Error on date: {date}, url: {failure.request.url}')
            self.logger.error(repr(failure))
            self.failed_rls.append((date, failure.request.url))

    def closed(self, reason):
        """
        Log information about unprocessed requests and dates still in processing when the spider closes.

        Args:
            reason (str): The reason for closing the spider.
        """
        self.logger.info(f'Unprocessed requests: {sorted(self.failed_rls)}')
        self.logger.info(f'Days in processing: {sorted(self.dates_in_process)}')


def date_range(start_date, end_date):
    """
    Generate a list of dates between two given dates, inclusive.

    Args:
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        list: A list of date strings in 'YYYY-MM-DD' format, including both start and end dates.

    Example:
        >>> date_range('2023-01-01', '2023-01-05')
        ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05']
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    date_list = []
    current_date = start
    while current_date <= end:
        date_list.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    return date_list


def increment_start_filter(url):
    """
    Increment the 'flights[start]' parameter in the given URL or add it if not present.

    This function is used to paginate through flight results by updating the starting
    index for flights in the URL.

    Args:
        url (str): The URL to modify.

    Returns:
        str: The updated URL with an incremented or newly added 'flights[start]' parameter.

    Example:
        >>> url = "https://example.com/flights@flights[start]=200"
        >>> increment_start_filter(url)
        "https://example.com/flights@flights[start]=300"

        >>> url = "https://example.com/flights"
        >>> increment_start_filter(url)
        "https://example.com/flights@flights[start]=100"
    """
    pattern = r'@flights\[start\]=(\d+)'
    match = re.search(pattern, url)
    if match:
        number = int(match.group(1))
        new_number = number + 100
        updated_url = re.sub(pattern, f'@flights[start]={new_number}', url)
    else:
        updated_url = url + '@flights[start]=100'
    return updated_url


def extract_coordinate(url, coordinate):
    """
    Extract latitude or longitude coordinate from a URL.

    This function searches for coordinates in the given URL using a regex pattern
    and returns either the latitude or longitude based on the specified coordinate type.

    Args:
        url (str): The URL containing the coordinates.
        coordinate (str): The type of coordinate to extract ('latitude' or 'longitude').

    Returns:
        float: The extracted coordinate.

    Raises:
        ValueError: If the coordinate type is invalid or coordinates are not found in the URL.

    Example:
        >>> url = "https://example.com/filter[point]=48.5 14.3"
        >>> extract_coordinate(url, "latitude")
        48.5
        >>> extract_coordinate(url, "longitude")
        14.3
    """
    # Regex pattern to match coordinates
    pattern = r"filter\[point\]=(-?[\d.]+)\s(-?[\d.]+)"
    
    # Search for the pattern in the URL
    match = re.search(pattern, url)
    
    # Check if the match is found
    if match:
        if coordinate.lower() == "latitude":
            return float(match.group(1))
        elif coordinate.lower() == "longitude":
            return float(match.group(2))
        else:
            raise ValueError("Invalid coordinate type. Choose 'latitude' or 'longitude'.")
    else:
        raise ValueError("Coordinates not found in the URL.")