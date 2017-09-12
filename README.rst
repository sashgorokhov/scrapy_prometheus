scrapy_prometheus
*****************

.. image:: https://img.shields.io/pypi/status/scrapy_prometheus.svg
    :target: https://github.com/sashgorokhov/scrapy_prometheus

.. image:: https://travis-ci.org/sashgorokhov/scrapy_prometheus.svg?branch=master
    :target: https://travis-ci.org/sashgorokhov/scrapy_prometheus

.. image:: https://img.shields.io/github/license/sashgorokhov/scrapy_prometheus.svg
    :target: https://raw.githubusercontent.com/sashgorokhov/scrapy_prometheus/master/LICENSE

.. image:: https://img.shields.io/pypi/pyversions/scrapy_prometheus.svg
    :target: https://pypi.python.org/pypi/scrapy-prometheus

.. image:: https://badge.fury.io/py/scrapy_prometheus.svg 
    :target: https://badge.fury.io/py/scrapy-prometheus

Exporting scrapy stats as prometheus metrics through pushgateway service.


Installation
============

Via pip:

.. code-block:: console

    pip install scrapy_prometheus


Usage
=====

To start using, add ``scrapy_prometheus.PrometheusStatsReport`` to EXTENSIONS setting:

.. code-block:: python
    
    EXTENSIONS = {
        'scrapy_prometheus.PrometheusStatsReport': 500,
    }
    
    PROMETHEUS_EXPORT_ENABLED = True # default
    
    # Prometheus pushgateway host
    PROMETHEUS_PUSHGATEWAY = 'localhost:9091' # default
    
    # Specify custom ColletorRegistry for metrics.
    # If not set, extension will create one by itself. 
    # Useful if you want to report custom metrics alongside with stats metrics.
    PROMETHEUS_REGISTRY = prometheus_client.CollectorRegistry()
    
    # Metric name prefix
    PROMETHEUS_METRIC_PREFIX = 'scrapy_prometheus' # default
    
    # Timeout for pushing metrics to pushgateway
    PROMETHEUS_PUSH_TIMEOUT = 5
    
    # Method to use when pushing metrics
    # Read https://github.com/prometheus/pushgateway#put-method
    PROMETHEUS_PUSH_METHOD = 'POST' # default
    
    
How metrics are created
=======================

Metric name is build from ``PROMETHEUS_METRIC_PREFIX`` and first part of stat name splitted by `/`, and other parts will go to the label named ``substat``. Stat value must be either `int` or `float`. 

For example:

* stat ``foo: 67`` whill produce metric ``scrapy_prometheus_foo{instance="...",job="scrapy",substat=""} 67``
* stat ``foo/bar: 67`` whill produce metric ``scrapy_prometheus_foo{instance="...",job="scrapy",substat="bar"} 67``
* stat ``foo/bar/baz: 67`` whill produce metric ``scrapy_prometheus_foo{instance="...",job="scrapy",substat="bar/baz"} 67``

Real world example
------------------

.. code-block:: text

    # HELP scrapy_prometheus_download_latency Scrapy download latency
    # TYPE scrapy_prometheus_download_latency summary
    scrapy_prometheus_download_latency_sum{instance="",job="scrapy"} 113.67475485801697
    scrapy_prometheus_download_latency_count{instance="",job="scrapy"} 34
    # HELP scrapy_prometheus_spider_lifetime Scrapy spider lifetime
    # TYPE scrapy_prometheus_spider_lifetime summary
    scrapy_prometheus_spider_lifetime_sum{cls="StorySpider",instance="",job="scrapy"} 45
    scrapy_prometheus_spider_lifetime_count{cls="StorySpider",instance="",job="scrapy"} 1
    # HELP scrapy_prometheus_stats_downloader downloader
    # TYPE scrapy_prometheus_stats_downloader gauge
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="request_bytes"} 15186
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="request_count"} 34
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="request_method_count/GET"} 15
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="request_method_count/POST"} 19
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="response_bytes"} 805171
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="response_count"} 34
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="response_status_count/200"} 31
    scrapy_prometheus_stats_downloader{instance="",job="scrapy",substat="response_status_count/406"} 3
    # HELP scrapy_prometheus_stats_httperror httperror
    # TYPE scrapy_prometheus_stats_httperror gauge
    scrapy_prometheus_stats_httperror{instance="",job="scrapy",substat="response_ignored_count"} 3
    scrapy_prometheus_stats_httperror{instance="",job="scrapy",substat="response_ignored_status_count/406"} 3
    # HELP scrapy_prometheus_stats_item_scraped_count item_scraped_count
    # TYPE scrapy_prometheus_stats_item_scraped_count gauge
    scrapy_prometheus_stats_item_scraped_count{instance="",job="scrapy",substat=""} 2792
    # HELP scrapy_prometheus_stats_log_count log_count
    # TYPE scrapy_prometheus_stats_log_count gauge
    scrapy_prometheus_stats_log_count{instance="",job="scrapy",substat="INFO"} 30
    # HELP scrapy_prometheus_stats_memusage memusage
    # TYPE scrapy_prometheus_stats_memusage gauge
    scrapy_prometheus_stats_memusage{instance="",job="scrapy",substat="max"} 7.2527872e+07
    scrapy_prometheus_stats_memusage{instance="",job="scrapy",substat="startup"} 7.2527872e+07
    # HELP scrapy_prometheus_stats_request_depth_max request_depth_max
    # TYPE scrapy_prometheus_stats_request_depth_max gauge
    scrapy_prometheus_stats_request_depth_max{instance="",job="scrapy",substat=""} 2
    # HELP scrapy_prometheus_stats_response_received_count response_received_count
    # TYPE scrapy_prometheus_stats_response_received_count gauge
    scrapy_prometheus_stats_response_received_count{instance="",job="scrapy",substat=""} 34
    # HELP scrapy_prometheus_stats_scheduler scheduler
    # TYPE scrapy_prometheus_stats_scheduler gauge
    scrapy_prometheus_stats_scheduler{instance="",job="scrapy",substat="dequeued"} 34
    scrapy_prometheus_stats_scheduler{instance="",job="scrapy",substat="dequeued/memory"} 34
    scrapy_prometheus_stats_scheduler{instance="",job="scrapy",substat="enqueued"} 34
    scrapy_prometheus_stats_scheduler{instance="",job="scrapy",substat="enqueued/memory"} 34

