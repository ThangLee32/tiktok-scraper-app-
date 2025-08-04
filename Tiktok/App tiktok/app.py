from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os # Thêm thư viện os để quản lý đường dẫn

app = Flask(__name__)

# --- Hàm lấy người theo dõi từ TikTok (từ script của bạn) ---
def get_tiktok_followers_selenium(username):
    # Đảm bảo chromedriver.exe nằm trong cùng thư mục với app.py
    # hoặc cung cấp đường dẫn đầy đủ đến nó.
    # Sử dụng os.path.join để tạo đường dẫn tương thích với mọi hệ điều hành
    current_dir = os.path.dirname(os.path.abspath(__file__))
    chromedriver_path = os.path.join(current_dir, 'chromedriver.exe')

    # Kiểm tra xem chromedriver.exe có tồn tại không
    if not os.path.exists(chromedriver_path):
        return f"Lỗi: Không tìm thấy chromedriver.exe tại {chromedriver_path}. Vui lòng tải xuống và đặt nó vào đây."

    service = Service(chromedriver_path)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Chạy ở chế độ ẩn, không mở cửa sổ trình duyệt
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--log-level=3') # Tắt log của Chrome để console gọn gàng hơn

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        wait = WebDriverWait(driver, 20) # Chờ tối đa 20 giây

        # Sử dụng selector bạn đã tìm thấy
        follower_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="followers-count"]')))

        followers = follower_element.text.strip()
        return followers

    except Exception as e:
        print(f"Lỗi khi lấy người theo dõi cho {username}: {e}") # In lỗi ra console server
        return "Không tìm thấy hoặc lỗi."
    finally:
        if driver:
            driver.quit()

# --- Định tuyến Flask ---

@app.route('/')
def index():
    return render_template('index.html') # Render tệp HTML

@app.route('/get_followers', methods=['POST'])
def get_followers_api():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({'error': 'Vui lòng cung cấp tên người dùng.'}), 400

    followers = get_tiktok_followers_selenium(username)

    if "Không tìm thấy hoặc lỗi." in followers:
        return jsonify({'username': username, 'followers': followers, 'success': False})
    else:
        return jsonify({'username': username, 'followers': followers, 'success': True})

if __name__ == '__main__':
    app.run(debug=True) # Chạy ứng dụng Flask ở chế độ debug