from flask import Flask, render_template, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
import time
import os
import re
import io

app = Flask(__name__)

def parse_views_string(views_str):
    """
    Chuyển đổi chuỗi lượt xem (ví dụ: '1.2M') thành số nguyên.
    """
    views_str = views_str.lower().strip()
    if 'k' in views_str:
        return int(float(views_str.replace('k', '')) * 1000)
    elif 'm' in views_str:
        return int(float(views_str.replace('m', '')) * 1000000)
    return int(views_str.replace(',', ''))

def get_tiktok_data_selenium(username):
    """
    Sử dụng Selenium để lấy dữ liệu TikTok bao gồm người theo dõi, lượt thích,
    tổng số video và video có lượt xem cao nhất.
    """
    driver = None
    data = {
        'username': username,
        'followers': 'Không tìm thấy',
        'likes': 'Không tìm thấy',
        'video_count': 0,
        'most_viewed_video': {'views': 0, 'url': 'Không tìm thấy'},
        'success': False,
        'error': ''
    }

    try:
        options = uc.ChromeOptions()
        
        # BẬT CHẾ ĐỘ ẨN DANH (HEADLESS) BẮT BUỘC TRÊN MÁY CHỦ
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        
        # Cấu hình đường dẫn Chrome cho môi trường Render
        chrome_binary_path = os.environ.get('GOOGLE_CHROME_BIN')
        if chrome_binary_path:
            options.binary_location = chrome_binary_path
        
        driver = uc.Chrome(options=options)
        
        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        # Chờ trang tải hoàn tất
        wait = WebDriverWait(driver, 15)
        time.sleep(5) 
        
        # --- LẤY DỮ LIỆU ---
        
        # Lấy số người theo dõi và lượt thích
        try:
            # Các XPATH selector có thể thay đổi, bạn có thể cần cập nhật chúng
            followers_element = wait.until(EC.presence_of_element_located((By.XPATH, '//strong[@data-e2e="followers-count"]')))
            data['followers'] = followers_element.text.strip()
            
            likes_element = wait.until(EC.presence_of_element_located((By.XPATH, '//strong[@data-e2e="likes-count"]')))
            data['likes'] = likes_element.text.strip()
        except TimeoutException:
            data['error'] = f"Không tìm thấy phần tử người theo dõi hoặc lượt thích cho {username}."
        except NoSuchElementException:
            data['error'] = f"Không tìm thấy phần tử người theo dõi hoặc lượt thích cho {username}."
            
        # Cuộn trang để tải tất cả các video
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_limit = 10
        for i in range(scroll_limit):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        # Tìm tất cả các phần tử video
        video_elements = driver.find_elements(By.XPATH, '//div[@data-e2e="user-post-item"]//a[contains(@href, "/video/")]')
        data['video_count'] = len(video_elements)
        
        if video_elements:
            highest_views = 0
            most_viewed_url = 'Không tìm thấy'
            
            for video in video_elements:
                try:
                    views_element = video.find_element(By.CSS_SELECTOR, 'strong[data-e2e="video-views"]')
                    views_text = views_element.text.strip()
                    views = parse_views_string(views_text)
                    
                    if views > highest_views:
                        highest_views = views
                        most_viewed_url = video.get_attribute('href')
                        
                except Exception as e:
                    print(f"Không thể lấy dữ liệu lượt xem cho một phần tử video: {e}")
                    continue
            
            if highest_views > 0:
                data['most_viewed_video']['views'] = highest_views
                data['most_viewed_video']['url'] = most_viewed_url
        
        if data['followers'] != 'Không tìm thấy' or data['likes'] != 'Không tìm thấy' or data['video_count'] > 0:
            data['success'] = True

    except Exception as e:
        data['error'] = f"Lỗi không xác định: {e}"
        data['success'] = False
        print(f"Lỗi chung khi lấy dữ liệu cho {username}: {e}")
    finally:
        if driver:
            driver.quit()
    return data

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/get_tiktok_data', methods=['POST'])
def get_tiktok_data_api():
    usernames_to_process = []
    
    # Xử lý nhập liệu từ trường văn bản để tách tên người dùng đúng cách
    usernames_text = request.form.get('usernames')
    if usernames_text:
        # Tách chuỗi bằng cả dấu phẩy và xuống dòng
        lines = usernames_text.splitlines()
        for line in lines:
            parts = [u.strip() for u in line.split(',') if u.strip()]
            usernames_to_process.extend(parts)

    # Xử lý tệp tải lên
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '' and file.filename.endswith('.txt'):
            try:
                stream = io.StringIO(file.stream.read().decode("utf-8"))
                for line in stream.readlines():
                    username = line.strip()
                    if username:
                        usernames_to_process.append(username)
            except Exception as e:
                return jsonify({'error': f'Lỗi khi xử lý tệp: {e}'}), 400
        elif file and file.filename != '':
            return jsonify({'error': 'Vui lòng tải lên tệp .txt hợp lệ.'}), 400

    # Loại bỏ các tên người dùng trùng lặp và rỗng
    usernames_to_process = list(set([re.sub(r'[^a-zA-Z0-9_.]', '', u) for u in usernames_to_process if u]))

    if not usernames_to_process:
        return jsonify({'error': 'Vui lòng cung cấp ít nhất một tên người dùng qua văn bản hoặc tệp.'}), 400

    results = []
    for username in usernames_to_process:
        result = get_tiktok_data_selenium(username)
        results.append(result)

    # TRẢ VỀ MỘT MẢNG JSON CHO TẤT CẢ CÁC KẾT QUẢ
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))