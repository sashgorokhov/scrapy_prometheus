import logging
import operator
import os
import random
import re

import mock
import prometheus_client
import pytest
import requests
import scrapy.crawler
import scrapy.settings
from scrapy import exceptions, statscollectors

import scrapy_prometheus


@pytest.fixture
def pushgateway_host():
    return os.environ.get('PUSHGATEWAY_HOST', 'localhost:9091')


@pytest.fixture
def registry():
    return prometheus_client.CollectorRegistry()


@pytest.fixture
def settings(registry, pushgateway_host):
    s = scrapy.settings.Settings()
    s.set('PROMETHEUS_EXPORT_ENABLED', True)
    s.set('PROMETHEUS_REGISTRY', registry)
    s.set('PROMETHEUS_PUSHGATEWAY', pushgateway_host)
    return s


@pytest.fixture
def crawler(settings):
    c = mock.Mock(spec=scrapy.crawler.Crawler)()
    c.settings = settings
    c.stats = statscollectors.StatsCollector(c)
    return c


@pytest.fixture
def ext(crawler):
    return scrapy_prometheus.PrometheusStatsReport.from_crawler(crawler)


JOB_TEST_NAME = 'test_scrapy_prometheus'


@pytest.fixture
def pushgateway_clear(pushgateway_host):
    try:
        yield
    finally:
        r = requests.delete('http://%s/metrics/job/%s' % (pushgateway_host, JOB_TEST_NAME))
        assert r.status_code == 202, r.text


@pytest.fixture
def spider():
    logger = logging.getLogger('test')
    logger.setLevel('INFO')
    logger.addHandler(logging.StreamHandler())
    spider = mock.Mock()
    spider.logger.return_value = logger
    return spider


def test_invalid_extension_not_enabled(crawler, settings):
    settings.set('PROMETHEUS_EXPORT_ENABLED', False)

    with pytest.raises(exceptions.NotConfigured, match='PROMETHEUS_EXPORT_ENABLED.*'):
        scrapy_prometheus.PrometheusStatsReport.from_crawler(crawler)


def test_invalid_registry(crawler, settings):
    settings.set('PROMETHEUS_REGISTRY', 'Foo')

    with pytest.raises(exceptions.NotConfigured, match='PROMETHEUS_REGISTRY.*'):
        scrapy_prometheus.PrometheusStatsReport.from_crawler(crawler)


def test_extension_created(ext, registry):
    assert ext.registry is registry


@pytest.mark.parametrize(['stat_name', 'stat_value', 'gauge_name', 'gauge_labels', 'gauge_value'], [
    ['foo', 1, 'scrapy_prometheus_foo', {'substat': ''}, 1],
    ['foo/bar', 1, 'scrapy_prometheus_foo', {'substat': 'bar'}, 1],
    ['foo/bar/baz', 1, 'scrapy_prometheus_foo', {'substat': 'bar/baz'}, 1],
])
def test_stat_to_metric(stat_name, stat_value, gauge_name, gauge_labels, gauge_value, ext):
    registry = ext.metrics_from_stats({stat_name: stat_value}, registry=ext.registry)

    assert gauge_name in registry._names_to_collectors
    collector = registry._names_to_collectors[gauge_name]
    metrics = collector.collect()
    assert len(metrics) == 1, list(map(operator.attrgetter('samples'), metrics))
    samples = metrics[0].samples
    assert len(samples) == 1, samples

    assert samples[0][0] == gauge_name
    assert samples[0][1] == gauge_labels
    assert samples[0][2] == gauge_value


@pytest.mark.parametrize(['stat_name', 'gauge_name', 'substat'], [
    ['foo', 'scrapy_prometheus_foo', ''],
    ['foo/bar', 'scrapy_prometheus_foo', 'bar'],
    ['foo/bar/baz', 'scrapy_prometheus_foo', 'bar/baz'],
])
def test_pushgateway_report(stat_name, gauge_name, substat, ext, spider, pushgateway_host, pushgateway_clear):
    stat_value = random.randint(0, 100)

    registry = ext.metrics_from_stats({stat_name: stat_value}, registry=ext.registry)

    ext.push_to_gateway(spider, pushgateway=pushgateway_host, registry=registry, job=JOB_TEST_NAME)

    response = requests.get('http://%s/metrics' % pushgateway_host)

    assert response.status_code == 200

    regexp = '%s{.*?job="%s".*?substat="%s"} %s' % (gauge_name, JOB_TEST_NAME, substat, stat_value)
    assert re.search(regexp, response.text), regexp
