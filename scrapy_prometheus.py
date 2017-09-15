import functools
import socket
from collections import defaultdict

import prometheus_client
from scrapy import statscollectors, signals

METRIC_COUNTER = prometheus_client.Counter
METRIC_GAUGE = prometheus_client.Gauge


def push_to_gateway(pushgateway, registry, method='POST', timeout=5, job='scrapy', grouping_key=None):
    if method.upper() == 'POST':
        push = prometheus_client.pushadd_to_gateway
    else:
        push = prometheus_client.push_to_gateway

    return push(pushgateway, job=job, grouping_key=grouping_key, timeout=timeout, registry=registry)


class InvalidMetricType(TypeError):
    pass


def _forced_spider(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        :param PrometheusStatsCollector self:
        """
        spider = getattr(self, '_forced_spider', None)
        if spider:
            kwargs.setdefault('spider', spider)
        return func(self, *args, **kwargs)

    return wrapper


class PrometheusStatsCollector(statscollectors.StatsCollector):
    def __init__(self, crawler):
        """
        :param scrapy.crawler.Crawler crawler:
        """
        self.crawler = crawler
        self.registries = defaultdict(lambda: prometheus_client.CollectorRegistry())
        self.crawler.signals.connect(self.engine_stopped, signal=signals.engine_stopped)
        super(PrometheusStatsCollector, self).__init__(crawler)

    def forced_spider(self, spider):
        """
        Force this spider to be used when writing metrics.

        :param scrapy.spider.Spider spider:
        """
        self._forced_spider = spider

    def get_registry(self, spider):
        """
        Return CollectorRegistry associated with spider. To get default CollectorRegistry, pass None.

        :param scrapy.spider.Spider spider:
        :rtype: prometheus_client.CollectorRegistry
        """
        return self.registries[getattr(spider, 'name', None)]

    # noinspection PyProtectedMember
    def get_metric(self, key, metric_type, spider=None, labels=None):
        prefix = self.crawler.settings.get('PROMETHEUS_METRIC_PREFIX', 'scrapy_prometheus')
        name = '%s_%s' % (prefix, key.replace('/', '_'))

        registry = self.get_registry(spider)

        if name not in registry._names_to_collectors:
            metric, created = metric_type(name, key, labels, registry=registry), True
        else:
            metric, created = registry._names_to_collectors[name], False
            if not hasattr(metric_type, '__wrapped__') or hasattr(metric_type, '__wrapped__') and not isinstance(metric,
                                                                                                                 metric_type.__wrapped__):
                if not self.crawler.settings.getbool('PROMETHEUS_SUPPRESS_TYPE_CHECK', False):
                    raise InvalidMetricType('Wrong type %s for metric %s, which is %s' % (
                        metric_type.__wrapped__.__name__, name, metric.__class__.__name__
                    ))
                else:
                    return None, created

        return metric, created

    @_forced_spider
    def set_value(self, key, value, spider=None):
        super(PrometheusStatsCollector, self).set_value(key, value, spider)

        if isinstance(value, (int, float)):
            metric, _ = self.get_metric(key, METRIC_GAUGE, spider=spider)
            if metric:
                metric.set(value)

    @_forced_spider
    def inc_value(self, key, count=1, start=0, spider=None):
        super(PrometheusStatsCollector, self).inc_value(key, count, start, spider)

        if isinstance(count, (int, float)):
            metric, _ = self.get_metric(key, METRIC_COUNTER, spider=spider)
            if metric:
                metric.inc(count)

    @_forced_spider
    def max_value(self, key, value, spider=None):
        super(PrometheusStatsCollector, self).max_value(key, value, spider)

        if isinstance(value, (int, float)):
            metric, _ = self.get_metric(key, METRIC_GAUGE, spider=spider)
            if metric:
                metric._value.set(max(metric._value.get(), value))

    @_forced_spider
    def min_value(self, key, value, spider=None):
        super(PrometheusStatsCollector, self).min_value(key, value, spider)

        if isinstance(value, (int, float)):
            metric, _ = self.get_metric(key, METRIC_GAUGE, spider=spider)
            if metric:
                metric._value.set(min(metric._value.get(), value))

    def get_grouping_key(self, spider=None):
        grouping_key = {
            'spider': spider.name if spider else ''
        }

        try:
            grouping_key['instance'] = socket.gethostname()
        except:
            grouping_key['instance'] = ""

        return grouping_key

    def _persist_stats(self, stats, spider=None):
        super(PrometheusStatsCollector, self)._persist_stats(stats, spider)

        if spider and spider.name not in self.registries:
            spider.logger.warning('%s spider not found in collector registries', spider.name)
            return

        try:
            push_to_gateway(
                pushgateway=self.crawler.settings.get('PROMETHEUS_PUSHGATEWAY', '127.0.0.1:9091'),
                registry=self.registries[spider.name if spider else None],
                method=self.crawler.settings.get('PROMETHEUS_PUSH_METHOD', 'POST'),
                timeout=self.crawler.settings.get('PROMETHEUS_PUSH_TIMEOUT', 5),
                job=self.crawler.settings.get('PROMETHEUS_JOB', 'scrapy'),
                grouping_key=self.crawler.settings.get('PROMETHEUS_GROUPING_KEY', self.get_grouping_key(spider))
            )
        except:
            if spider:
                spider.logger.exception('Failed to push "%s" spider metrics to pushgateway', spider.name)
        else:
            if spider:
                spider.logger.info('Pushed "%s" spider metrics to pushgateway', spider.name)

    def engine_stopped(self):
        self._persist_stats(self._stats, None)
