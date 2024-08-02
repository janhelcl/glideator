# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html


class UrlDecoderDownloaderMiddleware(object):

    def process_request(self, request, spider):
        request._url = request.url.replace("%5B", "[")
        request._url = request.url.replace("%5D", "]")
