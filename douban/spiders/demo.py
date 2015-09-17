# -*- coding: utf-8 -*-
import scrapy
import json
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from douban.items import DoubanItem

class DoubanSpider(scrapy.spiders.Spider):
    name = "douban"
    start_urls = [
        "http://read.douban.com/provider/63689290/?cat=all&sort=top&start=90"
    ]
    olduid=[]
    def parse(self, response):

            ids=[]
            # 获取数据id
            for sel in response.xpath('/html/body/div/div/section[contains(@class,"provider-ebooks")]/div[contains(@class,"bd")]/ul/li[contains(@class,"item")]'):

                price=sel.xpath('.//span[contains(@class, "price-tag")]/text()').extract()[0]
                if price==u'免费':
                    href=sel.xpath('.//div[contains(@class, "cover")]/a/@href').extract()[0]
                    ext=href.split('/')
                    if ext[2] in self.olduid:
                        continue
                    else:
                        ids.append(ext[2])
         
            # 抓取书籍数据
            for vo in ids:
                frmdata = {"aid": vo,"reader_data_version":"v10"}
                url = "http://read.douban.com/j/article_v2/get_reader_data"
                yield  scrapy.FormRequest(url=url, callback=self.parse1, meta={'uid':vo},formdata=frmdata)
            # #抓取下一页信息
            # urls=response.xpath('/html/body/div/div/section[contains(@class,"provider-ebooks")]//div[contains(@class,"pagination")]/ul/li[contains(@class,"next")]/a/@href').extract()
            # for url in urls:
            #     print url
            #     if url!='':
            #          url='http://read.douban.com/provider/63689290/'+url
            #          yield scrapy.Request(url, callback=self.parse)


    def parse1(self, response):
            jsonresponse = json.loads(response.body_as_unicode())
            item = DoubanItem()
            item['image_urls']=[jsonresponse['cover_url']]
            item['content']=jsonresponse['data']
            item['title']=jsonresponse['title']
            item['uid'] = response.meta['uid']
            yield item