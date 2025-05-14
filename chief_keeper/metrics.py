import os
import time
import logging
import threading
from prometheus_client import Counter, Gauge, start_http_server

logger = logging.getLogger(__name__)

# Initialize Prometheus metrics with labels
chief_new_hat_event = Counter('chief_new_hat_event', 'Counter for new hat events', 
                             ['old_hat_address', 'new_hat_address'])
chief_valid_hat = Gauge('chief_valid_hat', 'Gauge for valid hat status (1=valid, 0=invalid)',
                       ['hat_address'])
chief_schedule_called = Counter('chief_schedule_called', 'Counter for schedule function calls',
                              ['spell_address'])
chief_lift_called = Counter('chief_lift_called', 'Counter for lift function calls',
                          ['old_hat_address', 'new_hat_address'])
chief_invalid_lift_called = Counter('chief_invalid_lift_called', 'Counter for invalid lift attempts',
                                  ['old_hat_address', 'attempted_address'])

class MetricsServer:
    """Prometheus metrics server for the Chief Keeper"""
    
    def __init__(self, host='0.0.0.0', port=9090):
        self.host = host
        self.port = int(os.environ.get('METRICS_PORT', port))
        self.server_thread = None
        self.is_running = False
        
    def start(self):
        """Start the metrics server in a separate thread"""
        if self.is_running:
            return
            
        def run_server():
            logger.info(f"Starting Prometheus metrics server on {self.host}:{self.port}")
            start_http_server(self.port, self.host)
            self.is_running = True
            
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
def record_new_hat_event(old_hat_address, new_hat_address):
    """Record a new hat event"""
    chief_new_hat_event.labels(old_hat_address=old_hat_address, new_hat_address=new_hat_address).inc()
    logger.info(f"METRIC: New hat event recorded - Old hat: {old_hat_address}, New hat: {new_hat_address}")
    
def set_hat_validity(is_valid, hat_address):
    """Set the hat validity (1 for valid, 0 for invalid)"""
    value = 1 if is_valid else 0
    chief_valid_hat.labels(hat_address=hat_address).set(value)
    logger.info(f"METRIC: Hat validity set to {value} for address {hat_address}")
    
def record_schedule_called(spell_address):
    """Record a schedule function call"""
    chief_schedule_called.labels(spell_address=spell_address).inc()
    logger.info(f"METRIC: Schedule function call recorded for spell {spell_address}")
    
def record_lift_called(old_hat_address, new_hat_address):
    """Record a lift function call"""
    chief_lift_called.labels(old_hat_address=old_hat_address, new_hat_address=new_hat_address).inc()
    logger.info(f"METRIC: Lift function call recorded - Old hat: {old_hat_address}, New hat: {new_hat_address}")
    
def record_invalid_lift_called(old_hat_address, attempted_address):
    """Record an invalid lift attempt"""
    chief_invalid_lift_called.labels(old_hat_address=old_hat_address, attempted_address=attempted_address).inc()
    logger.info(f"METRIC: Invalid lift attempt recorded - Old hat: {old_hat_address}, Attempted: {attempted_address}")
