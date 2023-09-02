import logging

from prometheus_client.twisted import MetricsResource
from prometheus_client import Counter, Summary, Gauge
from twisted.web.server import Site
from twisted.web import server, resource
from twisted.internet import task
from scrapy.exceptions import NotConfigured
from scrapy.utils.reactor import listen_tcp
from scrapy import signals

logger = logging.getLogger(__name__)


class ScrapyPrometheusWebServiceMixin(Site):
    """
    This class definition handles all of the hosting side of things.
    """
    def __init__(self, crawler, **kwargs):
        # Collect locals
        self.tasks = []
        self.crawler = crawler
        # self.stats = self.crawler.stats # problematic as this gets removed later on...
        self.stats = self # The singularity cometh

        # Add signals hooks
        crawler.signals.connect(self.spider_opened, signals.spider_opened)
        crawler.signals.connect(self.spider_closed, signals.spider_closed)
        crawler.signals.connect(self.item_scraped, signals.item_scraped)
        crawler.signals.connect(self.item_dropped, signals.item_dropped)
        crawler.signals.connect(self.response_received,
                                signals.response_received)

        # Set prometheus settings
        self.name = crawler.settings.get('BOT_NAME')
        self.port = crawler.settings.get('PROMETHEUS_PORT', [9410])
        self.host = crawler.settings.get('PROMETHEUS_HOST', '0.0.0.0')
        self.path = crawler.settings.get('PROMETHEUS_PATH', 'metrics')
        self.interval = crawler.settings.get('PROMETHEUS_UPDATE_INTERVAL', 30)
        self._start_server()


    def _start_server(self):
        if self.crawler.settings.getbool('PROMETHEUS_ENDPOINT_ENABLED', True):
            root = resource.Resource()
            self.promtheus = None

            registry = self.get_registry(spider=None)
            self._prom_metrics_resource = MetricsResource(registry=registry)
            root.putChild(self.path.encode('utf-8'), self._prom_metrics_resource)
            server.Site.__init__(self, root)

    def _start_prometheus_endpoint(self):
        if self.crawler.settings.getbool('PROMETHEUS_ENDPOINT_ENABLED', True):
            self.promtheus = listen_tcp(self.port, self.host, self)

            # Periodically update the metrics
            # no need to do this anymore..
            # tsk = task.LoopingCall(self.update)
            # self.tasks.append(tsk)
            # tsk.start(self.interval, now=True)

    def _stop_prometheus_endpoint(self):
        # Stop all periodic tasks
        for tsk in self.tasks:
            if tsk.running:
                tsk.stop()

        # Stop metrics exporting
        self.promtheus.stopListening()
