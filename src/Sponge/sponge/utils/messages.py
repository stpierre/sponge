import logging
from django.contrib import messages

logger = logging.getLogger(__name__)

def error(request, msg):
    logger.error(msg)
    messages.error(request, msg)

def warning(request, msg):
    logger.warn(msg)
    messages.warning(request, msg)

def success(request, msg):
    logger.info(msg)
    messages.success(request, msg)

def info(request, msg):
    logger.info(msg)
    messages.info(request, msg)

def debug(request, msg):
    logger.debug(msg)
    messages.debug(request, msg)

def add_message(request, lvl, msg):
    logger.info(msg)
    messages.add_message(request, lvl, msg)
