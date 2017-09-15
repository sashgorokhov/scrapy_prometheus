import socket

import prometheus_client
from scrapy import statscollectors

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


# noinspection PyProtectedMember,PyTypeChecker
class PrometheusStatsCollector(statscollectors.StatsCollector, prometheus_client.CollectorRegistry):
    def __init__(self, crawler):
        """
        :param scrapy.crawler.Crawler crawler:
        """
        self.crawler = crawler
        statscollectors.StatsCollector.__init__(self, crawler)
        prometheus_client.CollectorRegistry.__init__(self)

    def get_metric(self, key, metric_type):
        prefix = self.crawler.settings.get('PROMETHEUS_METRIC_PREFIX', 'scrapy_prometheus')
        name = '%s_%s' % (prefix, key.replace('/', '_'))

        if name not in self._names_to_collectors:
            metric, created = metric_type(name, key, registry=self), True
        else:
            metric, created = self._names_to_collectors[name], False
            if not hasattr(metric_type, '__wrapped__') or hasattr(metric_type, '__wrapped__') and not isinstance(metric,
                                                                                                                 metric_type.__wrapped__):
                if not self.crawler.settings.getbool('PROMETHEUS_SUPPRESS_TYPE_CHECK', False):
                    raise InvalidMetricType('Wrong type %s for metric %s, which is %s' % (
                        metric_type.__wrapped__.__name__, name, metric.__class__.__name__
                    ))
                else:
                    return None, created

        return metric, created

    def set_value(self, key, value, spider=None):
        super(PrometheusStatsCollector, self).set_value(key, value, spider)

        if isinstance(value, (int, float)):
            metric, _ = self.get_metric(key, METRIC_GAUGE)  # type: prometheus_client.Gauge
            if metric:
                metric.set(value)

    def inc_value(self, key, count=1, start=0, spider=None):
        super(PrometheusStatsCollector, self).inc_value(key, count, start, spider)

        if isinstance(count, (int, float)):
            metric, _ = self.get_metric(key, METRIC_COUNTER)  # type: prometheus_client.Counter
            if metric:
                metric.inc(count)

    def max_value(self, key, value, spider=None):
        super(PrometheusStatsCollector, self).max_value(key, value, spider)

        if isinstance(value, (int, float)):
            metric, _ = self.get_metric(key, METRIC_GAUGE)  # type: prometheus_client.Gauge
            if metric:
                metric._value.set(max(metric._value.get(), value))

    def min_value(self, key, value, spider=None):
        super(PrometheusStatsCollector, self).min_value(key, value, spider)

        if isinstance(value, (int, float)):
            metric, _ = self.get_metric(key, METRIC_GAUGE)  # type: prometheus_client.Gauge
            if metric:
                metric._value.set(min(metric._value.get(), value))

    def get_grouping_key(self, spider):
        grouping_key = {'spider': spider.name}
        try:
            grouping_key['instance'] = socket.gethostname()
        except:
            pass

        return grouping_key

    def _persist_stats(self, stats, spider):
        super(PrometheusStatsCollector, self)._persist_stats(stats, spider)

        try:
            push_to_gateway(
                pushgateway=self.crawler.settings.get('PROMETHEUS_PUSHGATEWAY', '127.0.0.1:9091'),
                registry=self,
                method=self.crawler.settings.get('PROMETHEUS_PUSH_METHOD', 'POST'),
                timeout=self.crawler.settings.get('PROMETHEUS_PUSH_TIMEOUT', 5),
                job=self.crawler.settings.get('PROMETHEUS_JOB', 'scrapy'),
                grouping_key=self.crawler.settings.get('PROMETHEUS_GROUPING_KEY', self.get_grouping_key(spider))
            )
        except:
            spider.logger.exception('Failed to push metrics to pushgateway')
        else:
            spider.logger.info('Pushed metrics to pushgateway')
