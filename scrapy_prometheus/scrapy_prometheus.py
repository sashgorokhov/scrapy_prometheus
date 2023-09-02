import functools
import socket
from collections import defaultdict

import prometheus_client
from scrapy import statscollectors, signals

from .scrapy_prometheus_endpoint import ScrapyPrometheusWebServiceMixin

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


class PrometheusStatsCollector(ScrapyPrometheusWebServiceMixin, statscollectors.StatsCollector):
    def __init__(self, crawler, **kwargs):
        """
        :param scrapy.crawler.Crawler crawler:
        """
        self.crawler = crawler
        self.registries = defaultdict(lambda: prometheus_client.CollectorRegistry())
        self.crawler.signals.connect(self.engine_stopped, signal=signals.engine_stopped)

        # Signals monitoring. Useful...
        crawler.signals.connect(self.engine_started, signals.engine_started)

        self.prometheus_default_labels = self.crawler.settings.getdict('PROMETHEUS_DEFAULT_LABELS', {})
        if 'instance' not in self.prometheus_default_labels:
            try:
                self.prometheus_default_labels['instance'] = socket.gethostname()
            except:
                self.prometheus_default_labels['instance'] = ""

        # Init all superclasses
        statscollectors.StatsCollector.__init__(self, crawler=crawler, **kwargs)
        ScrapyPrometheusWebServiceMixin.__init__(self, crawler=crawler, **kwargs)


    @classmethod
    def from_crawler(cls, crawler):
        stats = cls(crawler)
        # Replace the default crawler.stats object with this, so that we collect
        # metrics in Prometheus as well as a built-in collector.
        crawler.stats = stats
        return stats

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
        # Hosting a Prometheus endpoint doesn't work well with multiple registries.
        # So I think the spider name should just go into the metric label instead.

        # reg_name = getattr(spider, 'name', None)
        reg_name = "default"
        return self.registries[reg_name]

    # noinspection PyProtectedMember
    def get_metric(self, key, metric_type, spider=None, labels={}):
        prefix = self.crawler.settings.get('PROMETHEUS_METRIC_PREFIX', 'scrapy_prometheus')
        name = '%s_%s' % (prefix, key.replace('/', '_'))

        registry = self.get_registry(spider)
        _labels = labels if labels else self.prometheus_default_labels

        if name not in registry._names_to_collectors:
            metric, created = metric_type(name, key, _labels, registry=registry), True
        else:
            metric, created = registry._names_to_collectors[name], False

        return metric, created
    
    def _get_metric(self, key, value, spider=None, labels={}, metric_type=METRIC_GAUGE):
        if isinstance(value, (int, float)):
            if not labels:
                labels = self.get_labels(spider)
            metric, _ = self.get_metric(key, metric_type, spider=spider, labels=labels)
            if metric:
                specific_metric = metric.labels(**labels)
                return specific_metric


    @_forced_spider
    def set_value(self, key, value, spider=None, labels={}):
        super(PrometheusStatsCollector, self).set_value(key, value, spider)
        metric = self._get_metric(key, value, spider=spider, labels=labels, metric_type=METRIC_GAUGE)
        if metric:
            metric.set(value)

    @_forced_spider
    def inc_value(self, key, count=1, start=0, spider=None, labels={}):
        super(PrometheusStatsCollector, self).inc_value(key, count, start, spider)
        metric = self._get_metric(key, start, spider=spider, labels=labels, metric_type=METRIC_COUNTER)
        if metric:
            metric.inc(count)

    @_forced_spider
    def max_value(self, key, value, spider=None, labels={}):
        super(PrometheusStatsCollector, self).max_value(key, value, spider)
        metric = self._get_metric(key, value, spider=spider, labels=labels, metric_type=METRIC_GAUGE)
        if metric:
            metric.set(max(metric._value.get(), value))

    @_forced_spider
    def min_value(self, key, value, spider=None, labels={}):
        super(PrometheusStatsCollector, self).min_value(key, value, spider)
        metric = self._get_metric(key, value, spider=spider, labels=labels, metric_type=METRIC_GAUGE)
        if metric:
            metric._value.set(min(metric._value.get(), value))

    def get_labels(self, spider=None):
        labels = {
            'spider': spider.name if spider else ''
        }
        labels.update(self.prometheus_default_labels)
        return labels

    def _persist_stats(self, stats, spider=None):
        super(PrometheusStatsCollector, self)._persist_stats(stats, spider)

        if spider and spider.name not in self.registries:
            spider.logger.warning('%s spider not found in collector registries', spider.name)
            return

        try:
            push_to_gateway(
                pushgateway=self.crawler.settings.get('PROMETHEUS_PUSHGATEWAY', '127.0.0.1:9091'),
                registry=self.registries[spider.name if spider else "default"],
                method=self.crawler.settings.get('PROMETHEUS_PUSH_METHOD', 'POST'),
                timeout=self.crawler.settings.get('PROMETHEUS_PUSH_TIMEOUT', 5),
                job=self.crawler.settings.get('PROMETHEUS_JOB', 'scrapy'),
                grouping_key=self.get_labels(spider)
            )
        except:
            if spider:
                spider.logger.exception('Failed to push "%s" spider metrics to pushgateway', spider.name)
        else:
            if spider:
                spider.logger.info('Pushed "%s" spider metrics to pushgateway', spider.name)

    def engine_started(self):
        self._start_prometheus_endpoint()

    def engine_stopped(self):
        self._persist_stats(self._stats, None)
        self._stop_prometheus_endpoint()

    def spider_opened(self, spider):
        if self.crawler.settings.getbool('PROMETHEUS_DEFAULT_METRICS', True):
            self.inc_value("spider_opened", spider=self)

    def spider_closed(self, spider, reason):
        if self.crawler.settings.getbool('PROMETHEUS_DEFAULT_METRICS', True):
            self.inc_value("spider_closed", spider=self)

    def item_scraped(self, item, spider):
        if self.crawler.settings.getbool('PROMETHEUS_DEFAULT_METRICS', True):
            self.inc_value("item_scraped", spider=self)

    def response_received(self, spider):
        if self.crawler.settings.getbool('PROMETHEUS_DEFAULT_METRICS', True):
            self.inc_value("response_received", spider=self)

    def item_dropped(self, item, spider, exception):
        if self.crawler.settings.getbool('PROMETHEUS_DEFAULT_METRICS', True):
            self.inc_value("item_dropped", spider=self)
