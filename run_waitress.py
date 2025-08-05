from waitress import serve
from app import app

if __name__ == "__main__":
    print("Running with Waitress...")
    serve(app, host="0.0.0.0", port=5001, threads=10) # Đổi thành cổng 5001