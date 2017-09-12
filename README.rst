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


