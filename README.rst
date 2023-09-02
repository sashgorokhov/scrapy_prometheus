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
You can optionally pass a `labels` array into all of these function calls, which will be passed
through to the new Prometheus metric.

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

    # If you want a set of labels to be applied to all of your metrics then you can assign a dictionary to this variable.
    PROMETHEUS_DEFAULT_LABELS = {'instance': <hostname>}


Installation
============

Install scrapy-prometheus-exporter using ``pip``::

    $ pip install scrapy-prometheus-exporter

Configuration
=============

First, you need to include the extension to your ``EXTENSIONS`` dict in
``settings.py``, for example::

    EXTENSIONS = {
        'scrapy_prometheus_exporter.prometheus.WebService': 500,
    }

By default the extension is enabled. To disable the extension you need to
set `PROMETHEUS_ENABLED`_ to ``False``.

The web server will listen on a port specified in `PROMETHEUS_PORT`_
(by default, it will try to listen on port 9410)

The endpoint for accessing exported metrics is::

    http://0.0.0.0:9410/metrics



Prometheus endpoint ettings
========

These are the settings that control the metrics exporter:

PROMETHEUS_ENDPOINT_ENABLED
------------------

Default: ``True``

A boolean which specifies if the exporter will be enabled (provided its
extension is also enabled).


PROMETHEUS_PORT
---------------

Default: ``[9410]``

The port to use for the web service. If set to ``None`` or ``0``, a
dynamically assigned port is used.

PROMETHEUS_HOST
---------------

Default: ``'0.0.0.0'``

The interface the web service should listen on.


PROMETHEUS_PATH
---------------

Default: ``'metrics'``

The url path to access exported metrics Example::

    http://0.0.0.0:9410/metrics


PROMETHEUS_UPDATE_INTERVAL
--------------------------

Default: ``30``

This extensions periodically collects stats for exporting. The interval in
seconds between metrics updates can be controlled with this setting.

How metrics are created
=======================

Metric name is build from ``PROMETHEUS_METRIC_PREFIX`` and stat name, where all ``/`` are replaced with ``_``.

For example:

* stat ``foo: 67`` whill produce metric ``scrapy_prometheus_foo{instance="...",job="scrapy",spider="..."} 67``
* stat ``foo/bar: 67`` whill produce metric ``scrapy_prometheus_foo_bar{instance="...",job="scrapy",spider="..."} 67``
* stat ``foo/bar/baz: 67`` whill produce metric ``scrapy_prometheus_foo_bar_baz{instance="...",job="scrapy",spider="..."} 67``
