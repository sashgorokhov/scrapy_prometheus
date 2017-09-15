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

Scrapy stats collector that exports scrapy stats as prometheus metrics through pushgateway service.

Installation
============

Via pip:

.. code-block:: console

    pip install scrapy_prometheus


Usage
=====

To start using, add ``scrapy_prometheus.PrometheusStatsCollector`` to STATS_CLASS setting:

.. code-block:: python

    STATS_CLASS = 'scrapy_prometheus.PrometheusStatsCollector'


This stats collector works exactly like the vanilla one (because it subclasses it), but also
creates prometheus metrics and pushes them to pushgateway service on spider close signal.

It supports two metric types: ``Counter`` and ``Gauge``. Stat metric type is determined by operation used on
the stat: ``stats.inc_value`` will create a ``Counter`` metric, while other methods,
``stats.set_value``, ``stats.max_value``, ``stats.min_value``, will create ``Gauge``.

All metrics will have a `spider` label attached with spider name.

Stat value must be either ``int`` or ``float``.

Note, that trying to perform action on a metric, that is not supposed to be used with this
action (set_value on Counter or inc_value on Gauge) will produce
``scrapy_prometheus.InvalidMetricType`` error. To suppress it, set ``PROMETHEUS_SUPPRESS_TYPE_CHECK`` to True.

If you want to create custom metrics, you can access your spider's CollectorRegistry by using ``stats.get_registry(spider)``.

Available settings
==================

.. code-block:: python

    # Prometheus pushgateway host
    PROMETHEUS_PUSHGATEWAY = 'localhost:9091'  # default

    # Metric name prefix
    PROMETHEUS_METRIC_PREFIX = 'scrapy_prometheus'  # default
    
    # Timeout for pushing metrics to pushgateway
    PROMETHEUS_PUSH_TIMEOUT = 5  # default
    
    # Method to use when pushing metrics
    # Read https://github.com/prometheus/pushgateway#put-method
    PROMETHEUS_PUSH_METHOD = 'POST'  # default

    # Do not raise scrapy_prometheus.InvalidMetricType when stat is accessed as different type metric.
    # For example, doing stats.inc_value('foo', 1) and then stats.set_value('foo', 2) will raise an error,
    # Because metric of type Counter was already created for stat foo.
    PROMETHEUS_SUPPRESS_TYPE_CHECK = False

    # job label value, applied to all metrics.
    PROMETHEUS_JOB = 'scrapy'  # default

    # grouping label dict, applied to all metrics.
    # by default it is an instance key with hostname value.
    PROMETHEUS_GROUPING_KEY = {'instance': <hostname>}


How metrics are created
=======================

Metric name is build from ``PROMETHEUS_METRIC_PREFIX`` and stat name, where all ``/`` are replaced with ``_``.

For example:

* stat ``foo: 67`` whill produce metric ``scrapy_prometheus_foo{instance="...",job="scrapy",spider="..."} 67``
* stat ``foo/bar: 67`` whill produce metric ``scrapy_prometheus_foo_bar{instance="...",job="scrapy",spider="..."} 67``
* stat ``foo/bar/baz: 67`` whill produce metric ``scrapy_prometheus_foo_bar_baz{instance="...",job="scrapy",spider="..."} 67``
