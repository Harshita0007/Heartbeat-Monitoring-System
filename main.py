

import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import sys
import re
from collections import defaultdict


class HeartbeatMonitor:
    
    def __init__(self, interval_seconds: int, allowed_misses: int, 
                 tolerance: float = 0.1, future_limit: int = 300,
                 gap_limit: int = 10):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if interval_seconds > 3600:
            raise ValueError("interval_seconds cannot exceed 3600 seconds")
        if allowed_misses <= 0:
            raise ValueError("allowed_misses must be positive")
        if allowed_misses > 10:
            raise ValueError("allowed_misses cannot exceed 10")
        if not 0 <= tolerance <= 1.0:
            raise ValueError("tolerance must be between 0.0 and 1.0")
        if future_limit < 0:
            raise ValueError("future_limit must be non-negative")
        if gap_limit <= 0:
            raise ValueError("gap_limit must be positive")
            
        self.interval_seconds = interval_seconds
        self.allowed_misses = allowed_misses
        self.tolerance = tolerance
        self.future_limit = future_limit
        self.gap_limit = gap_limit
        self.tolerance_seconds = interval_seconds * tolerance
    
    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        if not isinstance(timestamp_str, str) or not timestamp_str.strip():
            return None
            
        timestamp_str = timestamp_str.strip()
        
        try:
            dt = None
            
            if timestamp_str.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            
            elif re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}$', timestamp_str):
                dt = datetime.fromisoformat(timestamp_str)
            
            elif re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$', timestamp_str):
                dt = datetime.fromisoformat(timestamp_str + '+00:00')
            
            else:
                dt = datetime.fromisoformat(timestamp_str)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            return dt
            
        except (ValueError, AttributeError, TypeError):
            return None
    
    def validate_event(self, event: Dict[str, Any]) -> bool:
        if not isinstance(event, dict):
            return False
            
        if 'service' not in event or 'timestamp' not in event:
            return False
            
        service = event['service']
        if not isinstance(service, str) or not service.strip():
            return False
            
        if len(service.strip()) > 100:
            return False
            
        timestamp = self.parse_timestamp(event['timestamp'])
        if timestamp is None:
            return False
            
        # Allow timestamps up to 24 hours in future
        now = datetime.now(timezone.utc)
        max_future = now + timedelta(hours=24)
        if timestamp > max_future:
            return False
            
        return True
    
    def sort_events_by_service(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        services = defaultdict(list)
        malformed_count = 0
        
        for event in events:
            if not self.validate_event(event):
                print(f"Skipping malformed event: {event}", file=sys.stderr)
                malformed_count += 1
                continue
                
            service_name = event['service'].strip()
            services[service_name].append(event)
        
        # Sort and deduplicate
        for service_name in services:
            services[service_name].sort(
                key=lambda x: self.parse_timestamp(x['timestamp'])
            )
            
            # Remove duplicates
            unique_events = []
            seen_timestamps = set()
            
            for event in services[service_name]:
                timestamp = self.parse_timestamp(event['timestamp'])
                timestamp_key = timestamp.isoformat()
                
                if timestamp_key not in seen_timestamps:
                    seen_timestamps.add(timestamp_key)
                    unique_events.append(event)
                else:
                    print(f"Skipping duplicate event for service '{service_name}' at {timestamp_key}", file=sys.stderr)
            
            services[service_name] = unique_events
        
        if malformed_count > 0:
            print(f"Processed {len(events)} events, skipped {malformed_count} malformed events", file=sys.stderr)
        
        return dict(services)
    
    def detect_missed_heartbeats(self, service_events: List[Dict[str, Any]]) -> List[datetime]:
        if not service_events:
            return []
        
        alerts = []
        consecutive_misses = 0
        
        first_event_time = self.parse_timestamp(service_events[0]['timestamp'])
        current_expected = first_event_time
        event_index = 1
        
        while event_index <= len(service_events):
            next_expected = current_expected + timedelta(seconds=self.interval_seconds)
            
            gap_seconds = (next_expected - current_expected).total_seconds()
            max_gap = self.interval_seconds * self.gap_limit
            
            if gap_seconds > max_gap:
                if event_index < len(service_events):
                    current_expected = self.parse_timestamp(service_events[event_index]['timestamp'])
                    consecutive_misses = 0
                    event_index += 1
                    continue
            
            found_heartbeat = False
            current_expected = next_expected
            
            while event_index < len(service_events):
                event_time = self.parse_timestamp(service_events[event_index]['timestamp'])
                time_diff = (event_time - current_expected).total_seconds()
                
                if abs(time_diff) <= self.tolerance_seconds:
                    found_heartbeat = True
                    consecutive_misses = 0
                    event_index += 1
                    current_expected = event_time
                    break
                elif time_diff > self.tolerance_seconds:
                    break
                else:
                    event_index += 1
            
            if not found_heartbeat:
                consecutive_misses += 1
                
                if consecutive_misses >= self.allowed_misses:
                    alerts.append(current_expected)
                    consecutive_misses = 0
            
            if event_index >= len(service_events):
                last_event_time = self.parse_timestamp(service_events[-1]['timestamp'])
                time_since_last = (datetime.now(timezone.utc) - last_event_time).total_seconds()
                
                if time_since_last < self.interval_seconds * self.gap_limit:
                    while consecutive_misses < self.allowed_misses:
                        current_expected += timedelta(seconds=self.interval_seconds)
                        time_since_expected = (datetime.now(timezone.utc) - current_expected).total_seconds()
                        
                        if time_since_expected > self.tolerance_seconds:
                            consecutive_misses += 1
                            if consecutive_misses >= self.allowed_misses:
                                alerts.append(current_expected)
                                consecutive_misses = 0
                        else:
                            break
                break
        
        return alerts
    
    def monitor_heartbeats(self, events: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        if not isinstance(events, list):
            print("Error: events must be a list", file=sys.stderr)
            return []
        
        services_events = self.sort_events_by_service(events)
        all_alerts = []
        
        for service_name, service_events in services_events.items():
            alert_times = self.detect_missed_heartbeats(service_events)
            
            for alert_time in alert_times:
                all_alerts.append({
                    "service": service_name,
                    "alert_at": alert_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
        
        all_alerts.sort(key=lambda x: x["alert_at"])
        return all_alerts


def load_events_from_file(filename: str) -> List[Dict[str, Any]]:
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            if not isinstance(data, list):
                print(f"Error: File {filename} does not contain a JSON array", file=sys.stderr)
                return []
                
            return data
            
    except FileNotFoundError:
        print(f"Error loading file {filename}: File not found", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error loading file {filename}: Invalid JSON - {e}", file=sys.stderr)
        return []
    except PermissionError:
        print(f"Error loading file {filename}: Permission denied", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error loading file {filename}: {e}", file=sys.stderr)
        return []


def main():
    interval_seconds = 60
    allowed_misses = 3
    tolerance = 0.1
    future_limit = 300
    gap_limit = 10
    
    events_file = "heartbeat_events.json"
    
    try:
        events = load_events_from_file(events_file)
        
        if not events:
            print("No events loaded. Please check your JSON file.")
            return
        
        monitor = HeartbeatMonitor(
            interval_seconds=interval_seconds,
            allowed_misses=allowed_misses,
            tolerance=tolerance,
            future_limit=future_limit,
            gap_limit=gap_limit
        )
        
        alerts = monitor.monitor_heartbeats(events)
        
        print("Heartbeat Monitor Results:")
        print("=" * 30)
        print(f"Configuration:")
        print(f"  Expected interval: {interval_seconds} seconds")
        print(f"  Allowed misses: {allowed_misses}")
        print(f"  Tolerance: {tolerance * 100}%")
        print(f"  Future limit: {future_limit} seconds")
        print(f"  Gap limit: {gap_limit}x")
        print()
        
        if alerts:
            print(f"Found {len(alerts)} alert(s):")
            for alert in alerts:
                print(f"Service '{alert['service']}' missed heartbeats - Alert at: {alert['alert_at']}")
        else:
            print("No alerts detected.")
        
        print("\nJSON Output:")
        print(json.dumps(alerts, indent=2))
        
    except Exception as e:
        print(f"Error running heartbeat monitor: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())