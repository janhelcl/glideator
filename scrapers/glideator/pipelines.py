# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import os
import json
from datetime import datetime

from itemadapter import ItemAdapter


class MultiJsonlWriterPipeline:
    directory = 'outputs'
    filename_tmpl = 'flights_{date}.jsonl'
    
    def open_spider(self, spider):
        os.makedirs(self.directory, exist_ok=True)
        subdirectory = f'outputs_{datetime.now().strftime("%Y%m%d%H%M%S%f")}'
        os.makedirs(f'{self.directory}/{subdirectory}')
        self.subdirectory = subdirectory

    def process_item(self, item, spider):
        filename = self.filename_tmpl.format(date=item['date'].replace('-', ''))
        full_path = f'{self.directory}/{self.subdirectory}/{filename}'
        line = json.dumps(ItemAdapter(item).asdict(), ensure_ascii=False) + '\n'
        with open(full_path, 'a') as f:
            f.write(line)
        return item