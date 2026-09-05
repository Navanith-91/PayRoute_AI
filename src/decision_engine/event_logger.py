"""
Real-Time Routing Intelligence Event Logger for PayRoute AI.
Maintains a chronological stream of infrastructure and decision events for the live UI feed.
"""

from collections import deque
from dataclasses import asdict, dataclass
import datetime
import threading
from typing import Any, Deque, Dict, List, Optional


@dataclass
class RoutingEvent:
    """Represents an intelligent routing or infrastructure telemetry event."""
    event_id: str
    timestamp: str
    event_type: str  # e.g. "TRAFFIC_SURGE", "ROUTE_SWITCHED", "CIRCUIT_TRIPPED", "RECOVERY_PROBE", "OUTAGE_DETECTED"
    route_id: Optional[str]
    severity: str    # "INFO", "WARNING", "CRITICAL", "SUCCESS"
    title: str
    description: str


class EventLogger:
    """
    Thread-safe in-memory event stream with bounded history.
    """

    def __init__(self, maxlen: int = 50) -> None:
        self._lock = threading.Lock()
        self._events: Deque[RoutingEvent] = deque(maxlen=maxlen)
        self._counter = 0

        # Seed initial system startup event
        self.log_event(
            event_type="SYSTEM_INITIALIZED",
            route_id=None,
            severity="INFO",
            title="PayRoute AI Engine Online",
            description="Smart router, calibrated ML models, and 3-state circuit breakers initialized.",
        )

    def log_event(
        self,
        event_type: str,
        title: str,
        description: str,
        route_id: Optional[str] = None,
        severity: str = "INFO",
    ) -> RoutingEvent:
        """Appends a new intelligence event to the active stream."""
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._counter += 1
            evt = RoutingEvent(
                event_id=f"evt_{self._counter:05d}",
                timestamp=now_str,
                event_type=event_type,
                route_id=route_id,
                severity=severity,
                title=title,
                description=description,
            )
            self._events.appendleft(evt)
            return evt

    def get_recent_events(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns the most recent events as serializable dictionaries."""
        with self._lock:
            return [asdict(evt) for evt in list(self._events)[:limit]]
