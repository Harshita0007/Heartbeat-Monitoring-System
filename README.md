# Heartbeat Monitor

A simple tool to watch your services and alert you when they stop sending heartbeats. Think of it like a health check for your applications.

## What it does

Services send heartbeat signals at regular intervals. If a service misses too many heartbeats in a row, this tool will alert you. It's useful for monitoring web services, APIs, databases, or any application that should be running continuously.

## Features

- **Monitor multiple services** at once
- **Flexible timing** - set how often heartbeats should arrive and how many can be missed
- **Web interface** - easy to use dashboard for uploading data and viewing results
- **Pagination** - handle large numbers of alerts without overwhelming the screen
- **Input validation** - prevents invalid settings and provides helpful feedback
- **Reset functionality** - clear data and start fresh
- **JSON output** - get results in a format that's easy to process

## Quick start

### Prerequisites

- Python 3.7 or higher
- A JSON file with your heartbeat data

### Setup

1. Clone or download this project
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install flask flask-cors
   ```

### Running the web interface

```bash
python web_server.py
```

Then open http://localhost:5000 in your browser.

### Command line usage

```bash
python main.py
```

This will process `heartbeat_events.json` if it exists in the current directory.

## Data format

Your heartbeat data should be a JSON array of events:

```json
[
  {
    "service": "email-service",
    "timestamp": "2025-08-04T10:00:00Z"
  },
  {
    "service": "email-service",
    "timestamp": "2025-08-04T10:01:00Z"
  },
  {
    "service": "database",
    "timestamp": "2025-08-04T10:00:00Z"
  }
]
```

## Configuration

- **Expected Interval**: How often heartbeats should arrive (in seconds)
- **Allowed Misses**: How many consecutive heartbeats can be missed before alerting
- **Page Size**: How many alerts to show per page in the web interface

## How it works

1. **Load your data** - Upload a JSON file or use the sample data
2. **Set your parameters** - Configure timing and alert thresholds
3. **Process** - The system analyzes your heartbeat patterns
4. **Review results** - See which services missed heartbeats and when

The system groups events by service, sorts them by time, and looks for gaps that exceed your configured thresholds. It handles various timestamp formats and ignores malformed data.

## Testing

Run the test suite to verify everything works:

```bash
python test_heartbeat.py
```

## Project structure

```
├── main.py              # Core monitoring logic
├── web_server.py        # Web interface server
├── heartbeat_ui.html    # Web interface
├── test_heartbeat.py    # Tests
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Example use cases

- **Web application monitoring** - Check if your web servers are responding
- **API health checks** - Monitor microservices and APIs
- **Database monitoring** - Ensure database connections are active
- **Background job monitoring** - Verify scheduled tasks are running

## Troubleshooting

- **"File not found"** - Make sure your JSON file exists and is readable
- **"Invalid JSON"** - Check that your JSON is properly formatted
- **"No alerts detected"** - Your services might be healthy, or your thresholds might be too lenient
- **Web interface not loading** - Ensure Flask is installed and the server is running

## Contributing

Feel free to improve this tool! The code is straightforward and well-tested. Just make sure to run the tests before submitting changes.

## License

This project is open source. Use it for monitoring your services and keeping them healthy.
