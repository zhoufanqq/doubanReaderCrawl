# doubanReaderCrawl
Scrapy编写的豆瓣阅读爬虫
> * 使用Mysql存储数据（Redis也可以用来任性）
> * Scrapy初始化时加载自定义的扩展。主要是查询数据库获取已经爬取的数据，保存在内存中用于后续去重
> * Scrapy 筛选出未爬取页面，进行递归爬取
> * **Scrapy 在Items中去重，使用pyv8引擎运行js解析豆瓣加密数据**
> * 将解析到的数据保存在数据库中
