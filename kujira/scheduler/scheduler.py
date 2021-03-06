# -*- coding: utf-8 -*-
"""Tasks' scheduler"""

import logging
from threading import Lock
from kujira.scheduler.plugins.config import PLUGINS
from kujira.store.tasks import Mongodb
from kujira.scheduler import scheduler_config

LOG = logging.getLogger(__name__)

class Scheduler(object):
    """Scheduler class

    Check if task can be queued and if so, enqueue that task"""
    instance = None

    def __init__(self):
        self.lock = Lock()
        self.mongo = Mongodb()
        self.mongo.connect(scheduler_config.MONGO_DB,
                           scheduler_config.MONGO_COLLECTION,
                           scheduler_config.MONGO_AUDIT_COLLECTION)

    @staticmethod
    def get_instance():
        """Return the only instance of scheduler

        Return the only instance of Scheduler. In case it doesn't exist
        it creates one."""
        if not Scheduler.instance:
            Scheduler.instance = Scheduler()

        return Scheduler.instance

    def add_task(self, name, **params):
        """Add task to database

        :param name: string which identifies scheduler's plugin
        :param params: dictionary with plugin's parameters"""
        try:
            self.lock.acquire()
            if not name in PLUGINS.keys():
                return (False, "Could not find plugin: {0}".format(name))

            plugin = PLUGINS[name](**params)

            plugin.set_db_instance(self.mongo)

            is_valid_result = plugin.is_valid()
            if not is_valid_result[0]:
                LOG.error(is_valid_result[1])
                return is_valid_result

            can_run_result = plugin.can_run()
            if not can_run_result[0]:
                LOG.error(can_run_result[1])
                return can_run_result

            self.mongo.insert_task(plugin.data())
            LOG.info("Task '%s' added to queue!", plugin.title())

            return (True, None)
        except NotImplementedError as exc:
            LOG.error("Plugin '%s' is not complete: '%s'", name, str(exc))
        finally:
            self.lock.release()
