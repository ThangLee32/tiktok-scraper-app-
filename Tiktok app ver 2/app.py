from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import os
import io # Thêm thư viện io để đọc tệp trong bộ nhớ

app = Flask(__name__)

# Lấy đường dẫn chromedriver từ biến môi trường hoặc mặc định
CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chromedriver.exe'))

# --- Hàm lấy dữ liệu TikTok (người theo dõi và lượt thích) ---
def get_tiktok_data_selenium(username):
    # Kiểm tra xem chromedriver.exe có tồn tại không
    if not os.path.exists(CHROMEDRIVER_PATH):
        raise FileNotFoundError(f"Lỗi: Không tìm thấy chromedriver.exe tại {CHROMEDRIVER_PATH}. Vui lòng tải xuống và đặt nó vào đây hoặc cấu hình biến môi trường CHROMEDRIVER_PATH.")

    service = Service(CHROMEDRIVER_PATH)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Chạy ở chế độ ẩn, không mở cửa sổ trình duyệt
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--log-level=3') # Tắt log của Chrome để console gọn gàng hơn

    driver = None
    data = {'username': username, 'followers': 'Không tìm thấy', 'likes': 'Không tìm thấy', 'success': False}
    try:
        driver = webdriver.Chrome(service=service, options=options)
        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        wait = WebDriverWait(driver, 15) # Chờ tối đa 15 giây

        # Cố gắng tìm phần tử người theo dõi
        try:
            follower_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="followers-count"]')))
            data['followers'] = follower_element.text.strip()
        except TimeoutException:
            print(f"Không tìm thấy phần tử người theo dõi cho {username}.")

        # Cố gắng tìm phần tử lượt thích (sử dụng selector mới tìm thấy)
        try:
            # Selector cho tổng lượt thích có thể là data-e2e="likes-count" hoặc một selector khác
            # Vui lòng kiểm tra lại selector này trên trang TikTok nếu nó không hoạt động.
            like_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="likes-count"]')))
            data['likes'] = like_element.text.strip()
        except TimeoutException:
            print(f"Không tìm thấy phần tử lượt thích cho {username}.")

        # Nếu tìm thấy ít nhất một trong hai, coi là thành công
        if data['followers'] != 'Không tìm thấy' or data['likes'] != 'Không tìm thấy':
            data['success'] = True

    except FileNotFoundError as e:
        data['error'] = str(e)
        data['success'] = False
        print(f"Lỗi FileNotFoundError: {e}")
    except WebDriverException as e:
        data['error'] = f"Lỗi WebDriver: {e}"
        data['success'] = False
        print(f"Lỗi WebDriver: {e}")
    except Exception as e:
        data['error'] = f"Lỗi không xác định: {e}"
        data['success'] = False
        print(f"Lỗi chung khi lấy dữ liệu cho {username}: {e}")
    finally:
        if driver:
            driver.quit()
    return data

# --- Định tuyến Flask ---

@app.route('/')
def index():
    return render_template('index.html') # Render tệp HTML

@app.route('/get_tiktok_data', methods=['POST'])
def get_tiktok_data_api():
    usernames_to_process = []
    
    # Xử lý nhập liệu từ trường văn bản
    usernames_text = request.form.get('usernames')
    if usernames_text:
        # Tách các tên người dùng bằng dấu phẩy hoặc xuống dòng
        for line in usernames_text.splitlines():
            parts = [u.strip() for u in line.split(',') if u.strip()]
            usernames_to_process.extend(parts)

    # Xử lý tệp tải lên
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            # Đảm bảo tệp là văn bản
            if file.filename.endswith('.txt'):
                stream = io.StringIO(file.stream.read().decode("UTF8"))
                for line in stream.readlines():
                    username = line.strip()
                    if username:
                        usernames_to_process.append(username)
            else:
                return jsonify({'error': 'Vui lòng tải lên tệp .txt hợp lệ.'}), 400

    # Loại bỏ các tên người dùng trùng lặp và rỗng
    usernames_to_process = list(set([u for u in usernames_to_process if u]))

    if not usernames_to_process:
        return jsonify({'error': 'Vui lòng cung cấp ít nhất một tên người dùng qua văn bản hoặc tệp.'}), 400

    results = []
    for username in usernames_to_process:
        result = get_tiktok_data_selenium(username)
        results.append(result)

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True) # Chạy ứng dụng Flask ở chế độ debug