"""Suppress successful health probes without hiding failures or other requests."""
import logging


class HealthProbeFilter(logging.Filter):
    def filter(self, record):
        args = record.args
        if isinstance(args, tuple) and len(args) == 5:
            _, method, path, _, status = args
            if method in ('GET', 'HEAD') and str(path).split('?', 1)[0] == '/health':
                try:
                    return not 200 <= int(status) < 300
                except (TypeError, ValueError):
                    pass
        return True


def configure():
    logger = logging.getLogger('uvicorn.access')
    if not any(isinstance(f, HealthProbeFilter) for f in logger.filters):
        logger.addFilter(HealthProbeFilter())
