# -*- coding: utf-8 -*-
from datetime import datetime
from hashlib import md5
from scrapy import log
import PyV8
import json
from scrapy.exceptions import DropItem
from twisted.enterprise import adbapi


class DoubanPipeline(object):
    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        if item['uid'] in self.ids_seen:
            raise DropItem("Duplicate item found: %s" % item)
        else:
            self.ids_seen.add(item['uid'])
            return item

class DecodePipeline(object):
    def process_item(self, item, spider):
        ctxt = PyV8.JSContext()  
        ctxt.enter() 
        ctxt.locals.data = item['content']
        data=ctxt.eval(
                """
                        function Hex64(key) {
                            this._key = [],
                            this._tbl = {};
                            for (var _i = 0; 64 > _i; ++_i)
                                this._key[_i] = _hexCHS.charAt(key[_i]),
                                this._tbl[this._key[_i]] = _i;
                            this._pad = _hexCHS.charAt(64)
                        }
                        var _hexCHS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz$_~";
                        Hex64.prototype.dec = function(s) {
                            var _n1, _n2, _n3, _n4, _sa = [], _i = 0, _c = 0;
                            for (s = s.replace(/[^0-9A-Za-z$_~]/g, ""); _i < s.length; )
                                _n1 = this._tbl[s.charAt(_i++)],
                                _n2 = this._tbl[s.charAt(_i++)],
                                _n3 = this._tbl[s.charAt(_i++)],
                                _n4 = this._tbl[s.charAt(_i++)],
                                _sa[_c++] = _n1 << 2 | _n2 >> 4,
                                _sa[_c++] = (15 & _n2) << 4 | _n3 >> 2,
                                _sa[_c++] = (3 & _n3) << 6 | _n4;
                            var _e2 = s.slice(-2);
                            return _e2.charAt(0) === this._pad ? _sa.length = _sa.length - 2 : _e2.charAt(1) === this._pad && (_sa.length = _sa.length - 1),
                            Hex64._1to2(_sa)
                        }
                        ,
                        Hex64._1to2 = function(a) {
                            for (var _rs = "", _i = 0; _i < a.length; ++_i) {
                                var _c = a[_i];
                                _rs += String.fromCharCode(256 * _c + a[++_i])
                            }
                            return _rs
                        }
                        ;
                        var _key = [37, 7, 20, 41, 59, 53, 8, 24, 5, 62, 31, 4, 32, 6, 50, 36, 63, 35, 51, 0, 13, 43, 46, 40, 15, 27, 17, 57, 28, 54, 1, 60, 21, 22, 47, 42, 30, 39, 12, 3, 9, 45, 29, 23, 56, 2, 16, 61, 52, 44, 25, 14, 49, 34, 33, 10, 58, 55, 19, 26, 11, 18, 48, 38]
                          , decrypt = new Hex64(_key);
                    content= decrypt.dec(data);
                """
            )
        jsonParse=json.loads( ctxt.locals.content)
        item['content']=jsonParse[u'posts'][0][u'contents']
        # print jsonParse.keys()

        return item


class MySQLStorePipeline(object):
    """A pipeline to store the item in a MySQL database.
    This implementation uses Twisted's asynchronous database API.
    """

    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_settings(cls, settings):
        dbargs = dict(
            host=settings['MYSQL_HOST'],
            db=settings['MYSQL_DBNAME'],
            user=settings['MYSQL_USER'],
            passwd=settings['MYSQL_PASSWD'],
            charset='utf8',
            use_unicode=True,
        )
        dbpool = adbapi.ConnectionPool('MySQLdb', **dbargs)
        return cls(dbpool)

    def process_item(self, item, spider):
        # run db query in the thread pool
        d = self.dbpool.runInteraction(self._do_upsert, item, spider)
        d.addErrback(self._handle_error, item, spider)
        # at the end return the item in case of success or failure
        d.addBoth(lambda _: item)
        # return the deferred instead the item. This makes the engine to
        # process next item (according to CONCURRENT_ITEMS setting) after this
        # operation (deferred) has finished.
        return d

    def _do_upsert(self, conn, item, spider):
        """Perform an insert or update."""

        uid = self._get_guid(item)
        conn.execute("""SELECT EXISTS(
            SELECT 1 FROM huodong WHERE uid = %s
        )""", (uid))
        ret = conn.fetchone()[0]
        
        if ret:
            conn.execute("""
                UPDATE huodong
                SET title=%s, titlepic=%s, content=%s
                WHERE uid=%s
            """,[item['title'], item['images'][0]['path'],json.dumps(item['content'],skipkeys=True), uid])
            log.msg("Item updated in db: %s %r" % (uid, item))
        else:
            conn.execute("""
                    INSERT INTO huodong (`title`,`titlepic`,`content`,`uid`)
                    VALUES (%s,%s,%s,%s)
                """ , (item['title'],item['images'][0]['path'],json.dumps(item['content'],skipkeys=True),uid))

            log.msg("Item stored in db: %s %r" % (uid, item))

    def _handle_error(self, failure, item, spider):
        """Handle occurred on db interaction."""
        # do nothing, just log
        log.msg(failure)

    def _get_guid(self, item):
        """Generates an unique identifier for a given item."""
        # hash based solely in the url field
        return item['uid']