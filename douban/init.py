# -*- coding: utf-8 -*-
import logging
from scrapy import signals
from scrapy.exceptions import NotConfigured
from twisted.enterprise import adbapi

class GetOldUid(object):

    dbargs = {}
    @classmethod
    def from_crawler(cls, crawler):

        cls.dbargs = dict(
            host=crawler.settings['MYSQL_HOST'],
            db=crawler.settings['MYSQL_DBNAME'],
            user=crawler.settings['MYSQL_USER'],
            passwd=crawler.settings['MYSQL_PASSWD'],
            charset='utf8',
            use_unicode=True,
        )

        # connect the extension object to signals
        ext=cls()
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)

        # return the extension object

        return ext

    def spider_opened(self, spider):
    
        dbpool = adbapi.ConnectionPool('MySQLdb', **self.dbargs)
        d = dbpool.runInteraction(self._get_all_uid, spider)

        logging.warning("opened spider %s", spider.name)

    def spider_closed(self, spider):
        logging.warning("closed spider %s", spider.name)


    def _get_all_uid(self, conn, spider):

        conn.execute("SELECT uid FROM huodong")
        spider.olduid = [item[0] for item in conn.fetchall()]


