
import unittest
import tempfile
import json
import os
from main import HeartbeatMonitor, load_events_from_file


class TestHeartbeatMonitor(unittest.TestCase):
  

    def test_basic_functionality(self):
        events = [
            {"service": "email", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:02:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:06:00Z"},
        ]
        
        monitor = HeartbeatMonitor(60, 3)
        alerts = monitor.monitor_heartbeats(events)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["service"], "email")

    def test_no_alerts(self):
        events = [
            {"service": "api", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:02:00Z"},
        ]
        
        monitor = HeartbeatMonitor(60, 3)
        alerts = monitor.monitor_heartbeats(events)
        
        self.assertEqual(len(alerts), 0)

    def test_multiple_services(self):
        events = [
            {"service": "email", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:06:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:01:00Z"},
        ]
        
        monitor = HeartbeatMonitor(60, 3)
        alerts = monitor.monitor_heartbeats(events)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["service"], "email")

    def test_malformed_events(self):
        events = [
            {"service": "valid", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "missing_timestamp"},
            {"timestamp": "2025-08-04T10:00:00Z"},
            {"service": "invalid_timestamp", "timestamp": "not-a-timestamp"},
            {"service": "", "timestamp": "2025-08-04T10:00:00Z"},
            "not a dict",
            None,
            [],
        ]
        
        monitor = HeartbeatMonitor(60, 3)
        alerts = monitor.monitor_heartbeats(events)
        
        
        self.assertEqual(len(alerts), 0)

    def test_parse_timestamp_valid(self):
        monitor = HeartbeatMonitor(60, 3)
        
        valid_timestamps = [
            "2025-08-04T10:00:00Z",
            "2025-08-04T10:00:00+00:00",
            "2025-08-04T10:00:00.123Z",
            "2025-08-04T10:00:00.123+05:30",
        ]
        
        for ts in valid_timestamps:
            parsed = monitor.parse_timestamp(ts)
            self.assertIsNotNone(parsed)
            self.assertTrue(parsed.tzinfo is not None)

    def test_parse_timestamp_invalid(self):
        monitor = HeartbeatMonitor(60, 3)
        
        invalid_timestamps = [
            "not-a-timestamp",
            "2025-13-01T00:00:00Z",  
            "2025-02-30T00:00:00Z",  
            "2025-08-04T25:00:00Z",  
            "",
            None,
            123,
        ]
        
        for ts in invalid_timestamps:
            parsed = monitor.parse_timestamp(ts)
            self.assertIsNone(parsed)

    def test_validate_event_valid(self):
        
        monitor = HeartbeatMonitor(60, 3)
        
        valid_events = [
            {"service": "test", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "test", "timestamp": "2025-08-04T10:00:00.123Z"},
            {"service": "test", "timestamp": "2025-08-04T10:00:00+05:30"},
        ]
        
        for event in valid_events:
            self.assertTrue(monitor.validate_event(event))

    def test_validate_event_invalid(self):
        
        monitor = HeartbeatMonitor(60, 3)
        
        invalid_events = [
            {"service": "", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "   ", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "test", "timestamp": "invalid"},
            {"service": "test"},
            {"timestamp": "2025-08-04T10:00:00Z"},
            None,
            [],
            "not a dict",
        ]
        
        for event in invalid_events:
            self.assertFalse(monitor.validate_event(event))

    def test_duplicate_events(self):
        events = [
            {"service": "duplicate", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "duplicate", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "duplicate", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "duplicate", "timestamp": "2025-08-04T10:01:00Z"},
        ]
        
        monitor = HeartbeatMonitor(60, 3)
        alerts = monitor.monitor_heartbeats(events)
        
        
        self.assertEqual(len(alerts), 0)

    def test_large_time_gaps(self):
        events = [
            {"service": "restart", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "restart", "timestamp": "2025-08-04T12:00:00Z"},  
        ]
        
        monitor = HeartbeatMonitor(60, 3)
        alerts = monitor.monitor_heartbeats(events)
        
        self.assertIsInstance(alerts, list)

    def test_parameter_validation(self):
        
       
        monitor = HeartbeatMonitor(60, 3)
        self.assertEqual(monitor.interval_seconds, 60)
        self.assertEqual(monitor.allowed_misses, 3)
        
       
        with self.assertRaises(ValueError):
            HeartbeatMonitor(0, 3)
        with self.assertRaises(ValueError):
            HeartbeatMonitor(-1, 3)
        with self.assertRaises(ValueError):
            HeartbeatMonitor(60, 0)
        with self.assertRaises(ValueError):
            HeartbeatMonitor(60, -1)
        with self.assertRaises(ValueError):
            HeartbeatMonitor(3601, 3)
        with self.assertRaises(ValueError):
            HeartbeatMonitor(60, 11)

    def test_custom_parameters(self):
        
        monitor = HeartbeatMonitor(30, 2, tolerance=0.2, future_limit=600, gap_limit=5)
        
        self.assertEqual(monitor.interval_seconds, 30)
        self.assertEqual(monitor.allowed_misses, 2)
        self.assertEqual(monitor.tolerance, 0.2)
        self.assertEqual(monitor.future_limit, 600)
        self.assertEqual(monitor.gap_limit, 5)

    def test_load_events_from_file(self):
        
        events = [
            {"service": "test", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "test", "timestamp": "2025-08-04T10:01:00Z"},
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(events, f)
            filename = f.name
        
        try:
            loaded_events = load_events_from_file(filename)
            self.assertEqual(loaded_events, events)
        finally:
            os.unlink(filename)

    def test_load_events_from_nonexistent_file(self):
        
        events = load_events_from_file("nonexistent_file.json")
        self.assertEqual(events, [])

    def test_edge_cases(self):
        
        monitor = HeartbeatMonitor(60, 3)
        
        
        alerts = monitor.monitor_heartbeats([])
        self.assertEqual(alerts, [])
        
       
        alerts = monitor.monitor_heartbeats([{"service": "single", "timestamp": "2025-08-04T10:00:00Z"}])
        self.assertEqual(len(alerts), 0)
        
       
        alerts = monitor.monitor_heartbeats("not a list")
        self.assertEqual(alerts, [])

    def create_sample_test_file(self):
        
        sample_events = [
            {"service": "email", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:02:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:06:00Z"},
            
            {"service": "database", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "database", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "database", "timestamp": "2025-08-04T10:04:00Z"},
            
            {"service": "api", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:02:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:03:00Z"},
        ]
        
        with open("heartbeat_events.json", "w") as f:
            json.dump(sample_events, f, indent=2)
        
        print("Created heartbeat_events.json with sample data")


if __name__ == '__main__':
    unittest.main()