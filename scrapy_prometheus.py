import prometheus_client
from scrapy import signals, exceptions


class PrometheusStatsReport(object):
    """
    :param scrapy.crawler.Crawler crawler:
    :param str pushgateway: Prometheus' pushgateway host. Default is localhost:9091
    :param prometheus_client.CollectorRegistry registry: Registry to write metrics to.
    """
    crawler = None
    pushgateway = None

    def __init__(self, crawler, registry=None, pushgateway=None):
        self.crawler = crawler
        self.pushgateway = pushgateway or 'localhost:9091'
        self.registry = registry or prometheus_client.CollectorRegistry()

    @classmethod
    def from_crawler(cls, crawler):
        """
        :param scrapy.crawler.Crawler crawler:
        :return: PrometheusStatsReport
        """
        if not crawler.settings.getbool('PROMETHEUS_EXPORT_ENABLED'):
            raise exceptions.NotConfigured('PROMETHEUS_EXPORT_ENABLED flag is not set')

        pushgateway = crawler.settings.get('PROMETHEUS_PUSHGATEWAY', None)
        registry = crawler.settings.get('PROMETHEUS_REGISTRY', prometheus_client.CollectorRegistry())
        if registry is not None and not isinstance(registry, prometheus_client.CollectorRegistry):
            raise exceptions.NotConfigured('PROMETHEUS_REGISTRY is not a CollectorRegistry')

        ext = cls(crawler, registry=registry, pushgateway=pushgateway)

        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)

        return ext

    def spider_closed(self, spider):
        """
        :param scrapy.spider.Spider spider:
        """
        registry = self.metrics_from_stats(self.crawler.stats.get_stats(), registry=self.registry)
        self.push_to_gateway(spider, pushgateway=self.pushgateway, registry=registry)

    def make_gauge_name(self, key):
        prefix = self.crawler.settings.get('PROMETHEUS_METRIC_PREFIX', 'scrapy_prometheus')
        parts = key.split('/')
        return '%s_%s' % (prefix, parts[0])

    def make_gauge_labelvalue(self, key):
        return '/'.join(key.split('/')[1:])

    def metrics_from_stats(self, stats, registry=None):
        """
        Parses stats dict and populates either provided CollectorRegistry or creates a new empty one.

        :param dict stats: Scrapy stats dict
        :param prometheus_client.CollectorRegistry|None registry:
        :rtype: prometheus_client.CollectorRegistry
        :return: Registry with filled metrics
        """
        if not isinstance(stats, dict):
            raise TypeError('stats is not dict, but %s' % stats.__class__.__name__)

        registry = registry or prometheus_client.CollectorRegistry()

        gauges = dict()

        for key, value in stats.copy().items():
            if not isinstance(value, (int, float)):
                continue
            name = self.make_gauge_name(key)

            if name not in gauges:
                # noinspection PyArgumentList
                gauges[name] = prometheus_client.Gauge(
                    name=name,
                    documentation=key,
                    labelnames=['substat'],
                    registry=registry)

            gauges[name].labels(substat=self.make_gauge_labelvalue(key)).set(value)

        return registry

    def push_to_gateway(self, spider, pushgateway=None, registry=None, job='scrapy', grouping_key=None, push_method=None):
        """
        :param scrapy.spider.Spider spider:
        :param str pushgateway:
        :param prometheus_client.CollectorRegistry registry:
        :param str job:
        :param str grouping_key:
        """
        grouping_key = grouping_key or prometheus_client.instance_ip_grouping_key()
        timeout = self.crawler.settings.getint('PROMETHEUS_PUSH_TIMEOUT', 5)
        pushgateway = pushgateway or self.pushgateway
        registry = registry or self.registry
        push_method = push_method or self.crawler.settings.get('PROMETHEUS_PUSH_METHOD', 'POST')

        try:
            if push_method.upper() == 'POST':
                method = prometheus_client.pushadd_to_gateway
            else:
                method = prometheus_client.push_to_gateway

            method(pushgateway, job=job, grouping_key=grouping_key, timeout=timeout, registry=registry)
        except:
            spider.logger.exception('Failed to push metrics to %s', pushgateway)
        else:
            spider.logger.info('Pushed metrics to %s', pushgateway)
