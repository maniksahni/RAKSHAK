"""Local dev runner — threading mode (avoids eventlet kqueue issue on macOS)."""
import os
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app, socketio

app = create_app('development')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=False,
                 use_reloader=False, async_mode='threading',
                 allow_unsafe_werkzeug=True)
