from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import json
import os
from main import HeartbeatMonitor
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_html_template():
    try:
        with open('heartbeat_ui.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Heartbeat Monitor - File Not Found</title>
        </head>
        <body>
            <h1>Error: heartbeat_ui.html file not found</h1>
            <p>Please make sure heartbeat_ui.html is in the same directory as web_server.py</p>
        </body>
        </html>
        """

@app.route('/')
def index():
    return get_html_template()

@app.route('/api/process', methods=['POST'])
def process_heartbeats():
    try:
        data = request.get_json()
        
        if not data or 'events' not in data:
            return jsonify({'error': 'No events provided'}), 400
        
        events = data['events']
        interval = data.get('expectedInterval', 60)
        allowed_misses = data.get('allowedMisses', 3)
        page = data.get('page', 1)
        page_size = data.get('pageSize', 50)
        
        if interval <= 0:
            return jsonify({'error': 'Expected interval must be positive'}), 400
        if interval > 3600:
            return jsonify({'error': 'Expected interval cannot exceed 3600 seconds'}), 400
        if allowed_misses <= 0:
            return jsonify({'error': 'Allowed misses must be positive'}), 400
        if allowed_misses > 10:
            return jsonify({'error': 'Allowed misses cannot exceed 10'}), 400
        if page < 1 or page_size < 1:
            return jsonify({'error': 'Invalid pagination parameters'}), 400
        
        monitor = HeartbeatMonitor(interval, allowed_misses)
        all_alerts = monitor.monitor_heartbeats(events)
        
        services_events = monitor.sort_events_by_service(events)
        service_stats = {}
        malformed_count = 0
        
        for service_name, service_events in services_events.items():
            service_alerts = monitor.detect_missed_heartbeats(service_events)
            service_stats[service_name] = {
                'totalEvents': len(service_events),
                'alerts': len(service_alerts)
            }
        
        for event in events:
            if not monitor.validate_event(event):
                malformed_count += 1
        
        total_alerts = len(all_alerts)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_alerts = all_alerts[start_idx:end_idx]
        
        response = {
            'alerts': paginated_alerts,
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'totalAlerts': total_alerts,
                'totalPages': (total_alerts + page_size - 1) // page_size,
                'hasNext': end_idx < total_alerts,
                'hasPrevious': page > 1
            },
            'serviceStats': service_stats,
            'malformedCount': malformed_count,
            'totalServices': len(services_events),
            'totalEvents': len(events)
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/reset', methods=['POST'])
def reset_data():
    try:
        return jsonify({
            'message': 'Data reset successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'Reset failed: {str(e)}'}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 50, type=int)
        
        if page < 1 or page_size < 1:
            return jsonify({'error': 'Invalid pagination parameters'}), 400
        
        all_alerts = []
        total_alerts = len(all_alerts)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_alerts = all_alerts[start_idx:end_idx]
        
        response = {
            'alerts': paginated_alerts,
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'totalAlerts': total_alerts,
                'totalPages': (total_alerts + page_size - 1) // page_size,
                'hasNext': end_idx < total_alerts,
                'hasPrevious': page > 1
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get alerts: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({'error': 'File must be a JSON file'}), 400
        
        content = file.read().decode('utf-8')
        events = json.loads(content)
        
        if not isinstance(events, list):
            return jsonify({'error': 'JSON must contain an array of events'}), 400
        
        return jsonify({
            'message': f'File uploaded successfully',
            'events': events,
            'eventCount': len(events)
        })
        
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/sample-data')
def get_sample_data():
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
        
        {"service": "broken"},
        {"timestamp": "2025-08-04T10:00:00Z"},
        {"service": "invalid", "timestamp": "not-a-timestamp"},
    ]
    
    return jsonify({
        'events': sample_events,
        'eventCount': len(sample_events)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def main():
    print(" Starting Heartbeat Monitor Web Server...")
    print("Dashboard: http://localhost:5000")
    print(" API endpoints:")
    print("   - POST /api/process - Process events with pagination")
    print("   - POST /api/reset - Reset data")
    print("   - GET /api/alerts - Get paginated alerts")
    print("   - POST /api/upload - Upload JSON file")
    print("   - GET /api/sample-data - Get sample data")
    print("\n Features:")
    print("   -  Pagination (10, 25, 50, 100 alerts per page)")
    print("   -  Reset functionality")
    print("   -  Full JSON output")
    print("   -  Responsive UI")
    print("\n  Make sure heartbeat_ui.html is in the same directory!")
    print(" Press Ctrl+C to stop\n")
    
    if not os.path.exists('heartbeat_ui.html'):
        print("  Warning: heartbeat_ui.html not found!")
    
    if not os.path.exists('main.py'):
        print("  Warning: main.py not found!")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n Error starting server: {e}")

if __name__ == '__main__':
    main()
