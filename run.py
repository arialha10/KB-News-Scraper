import webview
import threading
from app import app

def run_flask():
    app.run(debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    webview.create_window("LP 뉴스 스크래퍼", "http://127.0.0.1:5000", width=1400, height=800)
    webview.start(
        gui='edgechromium',
        debug=False,
        http_server=False,
        private_mode=False
    )
