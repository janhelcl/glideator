# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import os
import json
from datetime import datetime

from itemadapter import ItemAdapter


class MultiJsonlWriterPipeline:
    """
    A pipeline for writing scraped items to multiple JSONL files.

    This pipeline creates a new subdirectory for each spider run and writes items
    to separate JSONL files based on their date.

    Attributes:
        directory (str): The base directory for output files.
        filename_tmpl (str): A template for generating filenames.
        subdirectory (str): The name of the subdirectory for the current spider run.
    """
    directory = 'outputs'
    filename_tmpl = 'flights_{date}.jsonl'
    
    def open_spider(self, spider):
        """
        Called when the spider is opened.

        This method creates the base directory if it doesn't exist,
        and creates a new subdirectory for the current spider run.

        Args:
            spider: The spider instance that was opened.
        """
        os.makedirs(self.directory, exist_ok=True)
        subdirectory = f'outputs_{datetime.now().strftime("%Y%m%d%H%M%S%f")}'
        os.makedirs(f'{self.directory}/{subdirectory}')
        self.subdirectory = subdirectory

    def process_item(self, item, spider):
        """
        Process a scraped item.

        This method writes the item to a JSONL file. The filename is determined
        by the item's date.

        Args:
            item: The scraped item to process.
            spider: The spider that scraped the item.

        Returns:
            The processed item.
        """
        filename = self.filename_tmpl.format(date=item['date'].replace('-', ''))
        full_path = f'{self.directory}/{self.subdirectory}/{filename}'
        line = json.dumps(ItemAdapter(item).asdict(), ensure_ascii=False) + '\n'
        with open(full_path, 'a') as f:
            f.write(line)
        return item