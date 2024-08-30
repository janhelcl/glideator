# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html


class UrlDecoderDownloaderMiddleware(object):
    """
    A Scrapy downloader middleware for decoding URL-encoded characters in request URLs.

    This middleware specifically targets the square bracket characters ('[' and ']')
    which are often encoded in URLs. It replaces their encoded representations
    ('%5B' and '%5D') with the actual characters.

    Attributes:
        None

    Methods:
        process_request(self, request, spider): Decodes the URL of each request.
    """

    def process_request(self, request, spider):
        request._url = request.url.replace("%5B", "[")
        request._url = request.url.replace("%5D", "]")
