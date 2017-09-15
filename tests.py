import logging
import os
import re

import mock
import prometheus_client
import pytest
import requests
import scrapy.crawler
import scrapy.settings

import scrapy_prometheus


@pytest.fixture
def pushgateway():
    pushgateway_host = os.environ.get('PUSHGATEWAY_HOST', 'localhost:9091')
    try:
        yield pushgateway_host
    finally:
        r = requests.delete('http://%s/metrics/job/%s' % (pushgateway_host, 'test_scrapy_prometheus'))
        assert r.status_code == 202, r.text


@pytest.fixture
def registry():
    return prometheus_client.CollectorRegistry()


@pytest.fixture
def settings(pushgateway):
    s = scrapy.settings.Settings()
    s.set('PROMETHEUS_PUSHGATEWAY', pushgateway)
    s.set('PROMETHEUS_JOB', 'test_scrapy_prometheus')
    return s


@pytest.fixture
def crawler(settings):
    c = mock.Mock(spec=scrapy.crawler.Crawler)()
    c.settings = settings
    c.stats = scrapy_prometheus.PrometheusStatsCollector(c)
    return c


@pytest.fixture
def spider():
    logger = logging.getLogger('test')
    logger.setLevel('INFO')
    logger.addHandler(logging.StreamHandler())
    spider = mock.Mock()
    spider.logger.return_value = logger
    spider.name = 'test'
    return spider


@pytest.mark.parametrize(['stat_name', 'metric_name'], [
    ['foo', 'scrapy_prometheus_foo'],
    ['foo/bar', 'scrapy_prometheus_foo_bar'],
    ['foo/bar/baz', 'scrapy_prometheus_foo_bar_baz'],
])
def test_metric_name_and_substat(stat_name, metric_name, crawler):
    metric, created = crawler.stats.get_metric(stat_name, scrapy_prometheus.METRIC_COUNTER)
    metric.inc()

    assert created
    assert metric_name in crawler.stats.get_registry(None)._names_to_collectors


def test_invalid_metric_type(crawler):
    crawler.stats.inc_value('foo', 1)

    with pytest.raises(scrapy_prometheus.InvalidMetricType):
        crawler.stats.set_value('foo', 1)


@pytest.mark.parametrize(['key', 'value', 'metric_type', 'metric_name', 'metric_value'], [
    ['foo', 1, scrapy_prometheus.METRIC_COUNTER, 'scrapy_prometheus_foo', 1],
    ['foo/bar', 2, scrapy_prometheus.METRIC_COUNTER, 'scrapy_prometheus_foo_bar', 2],
    ['foo/bar/baz', 3, scrapy_prometheus.METRIC_GAUGE, 'scrapy_prometheus_foo_bar_baz', 3],
])
def test_pushgateway_report(key, value, metric_type, metric_name, metric_value, crawler, spider):
    if scrapy_prometheus.METRIC_COUNTER == metric_type:
        crawler.stats.inc_value(key, value, spider=spider)
    elif scrapy_prometheus.METRIC_GAUGE == metric_type:
        crawler.stats.set_value(key, value, spider=spider)
    else:
        raise ValueError()

    crawler.stats.close_spider(spider, 'test')

    response = requests.get('http://%s/metrics' % crawler.settings.get('PROMETHEUS_PUSHGATEWAY'))
    assert response.status_code == 200

    try:
        regexp = '%s{.*?job="%s".*?} %s' % (metric_name, crawler.settings.get('PROMETHEUS_JOB'), metric_value)
        assert re.search(regexp, response.text), regexp

        if scrapy_prometheus.METRIC_GAUGE == metric_type:
            assert re.search(r'# TYPE %s gauge' % metric_name, response.text)
        elif scrapy_prometheus.METRIC_COUNTER == metric_type:
            assert re.search(r'# TYPE %s counter' % metric_name, response.text)
    except AssertionError:
        print(response.text)
        raise
