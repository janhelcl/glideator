# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import logging
import time

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from playwright.async_api import TimeoutError

logger = logging.getLogger(__name__)


class UrlDecoderDownloaderMiddleware(object):

    def process_request(self, request, spider):
        request._url = request.url.replace("%5B", "[")
        request._url = request.url.replace("%5D", "]")


class PlaywrightRetryMiddleware(RetryMiddleware):

    MAX_RETRIES = 3
    SLEEP_ON_TIMEOUT = 60 * 5

    def process_exception(self, request, exception, spider):
        if isinstance(exception, (TimeoutError,)):
            retries = request.meta.get('retry_times', 0) + 1
            logger.error(f'TimeoutError on date: {request.meta["date"]}, url: {request.url}')
            logger.error(repr(exception))
            if retries <= self.MAX_RETRIES:
                logger.info(f'Sleeping after TimeoutError on {request.url} for {self.SLEEP_ON_TIMEOUT}s')
                time.sleep(self.SLEEP_ON_TIMEOUT)
                logger.debug(f"Retrying {request} (failed {retries} times) due to timeout.")
                retry_req = request.copy()
                retry_req.meta['retry_times'] = retries
                
                return retry_req
            else:
                logger.debug(f"Gave up retrying {request} (failed {retries} times) due to timeout.")
        else:
            logger.error(f'Error on date: {request.meta["date"]}, url: {request.url}')
            logger.error(repr(exception))
            logger.error('Not retrying.')
        return None