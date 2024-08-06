import scrapy


class LaunchesSpider(scrapy.Spider):
    name = "launches"
    base_url = "https://www.paragliding-mapa.cz/startovacky/detail/{i}"
    
    def start_requests(self):
        for i in range(1, 350):
            url = self.base_url.format(i=i)
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        yield {
            'name': response.xpath("/html/body/div[3]/div[1]/div[1]/h1/text()").get().strip().removeprefix("Startovačky - "),
            'point': response.xpath("/html/body/div[3]/div[2]/div[1]/div[2]/div[1]/h4/text()").get().strip(),
            'wind_direction': response.xpath("/html/body/div[3]/div[2]/div[1]/div[1]/div[2]/h4/text()").get().strip(),
            'altitude': int(response.xpath("/html/body/div[3]/div[2]/div[1]/div[1]/div[3]/h4/text()").get().strip().removesuffix(" m n. m.")),
            'superelevation': int(response.xpath("/html/body/div[3]/div[2]/div[1]/div[1]/div[4]/h4/text()").get().strip().removesuffix(" m")),
            'status': response.xpath("/html/body/div[3]/div[2]/div[1]/div[2]/div[2]/h4/text()").get().strip()
        }