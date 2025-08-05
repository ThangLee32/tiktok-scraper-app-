from flask import Flask, render_template, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException, StaleElementReferenceException
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
    try:
        # Xử lý trường hợp không có K hoặc M
        return int(views_str.replace(',', ''))
    except ValueError:
        return 0

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
        print(f"Bắt đầu lấy dữ liệu cho người dùng: {username}")
        options = uc.ChromeOptions()
        
        # BẬT CHẾ ĐỘ ẨN DANH (HEADLESS) BẮT BUỘC TRÊN MÁY CHỦ
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        
        # Chỉ định đường dẫn tới tệp thực thi của Chrome trên Render
        # Đây là giải pháp đáng tin cậy nhất để khắc phục lỗi "Could not determine browser executable."
        options.binary_location = "/usr/bin/google-chrome-stable"
        
        driver = uc.Chrome(options=options)
        
        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        # Chờ trang tải hoàn tất và tìm phần tử chính
        wait = WebDriverWait(driver, 20)
        
        # ... (các đoạn mã khác)
        
    except Exception as e:
        data['error'] = f"Lỗi không xác định: {e}"
        data['success'] = False
        print(f"Lỗi chung khi lấy dữ liệu cho {username}: {e}")
    finally:
        if driver:
            driver.quit()
            print(f"Đã đóng trình duyệt cho {username}.")
    return data

        driver = uc.Chrome(options=options)
        
        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        # Chờ trang tải hoàn tất và tìm phần tử chính
        wait = WebDriverWait(driver, 20) # Tăng thời gian chờ lên 20 giây
        
        # --- LẤY DỮ LIỆU ---
        
        try:
            # Chờ phần tử người theo dõi xuất hiện
            followers_element = wait.until(EC.presence_of_element_located((By.XPATH, '//strong[@data-e2e="followers-count"]')))
            data['followers'] = followers_element.text.strip()
            
            # Chờ phần tử lượt thích xuất hiện
            likes_element = wait.until(EC.presence_of_element_located((By.XPATH, '//strong[@data-e2e="likes-count"]')))
            data['likes'] = likes_element.text.strip()

            print(f"Đã tìm thấy người theo dõi và lượt thích cho {username}.")

        except TimeoutException:
            # Kiểm tra xem có phải trang không tồn tại hay không
            try:
                # Tìm phần tử cho biết trang không tồn tại
                driver.find_element(By.XPATH, '//div[contains(text(), "Couldn\'t find this account")]')
                data['error'] = f"Tên người dùng TikTok '{username}' không tồn tại."
                print(f"Lỗi: Tên người dùng '{username}' không tồn tại.")
                return data
            except NoSuchElementException:
                data['error'] = f"Không tìm thấy phần tử người theo dõi hoặc lượt thích cho {username} (Timeout)."
                print(f"Lỗi: Không tìm thấy phần tử chính cho '{username}' sau 20s.")
                return data
        
        # --- LẤY DỮ LIỆU VIDEO ---
        # Cuộn trang cho đến khi không còn nội dung mới được tải
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while scroll_count < 15: # Giới hạn cuộn để tránh vòng lặp vô hạn
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) # Giảm thời gian chờ giữa các lần cuộn
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_count += 1
            print(f"Đã cuộn trang lần thứ {scroll_count} cho {username}. Tổng chiều cao: {new_height}")
        
        # Chờ tất cả các video tải xong sau khi cuộn
        try:
            wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@data-e2e="user-post-item"]')))
            print(f"Đã tải xong các phần tử video cho {username}.")
        except TimeoutException:
            print(f"Không thể tìm thấy bất kỳ phần tử video nào cho {username} sau khi cuộn.")
            
        # Tìm tất cả các phần tử container video
        video_containers = driver.find_elements(By.XPATH, '//div[@data-e2e="user-post-item"]')
        data['video_count'] = len(video_containers)
        
        if video_containers:
            highest_views = 0
            most_viewed_url = 'Không tìm thấy'
            
            for container in video_containers:
                try:
                    # Tìm thẻ <a> và thẻ lượt xem bên trong mỗi container
                    video_link = container.find_element(By.XPATH, './/a[contains(@href, "/video/")]')
                    views_element = container.find_element(By.XPATH, './/strong[@data-e2e="video-views"]')
                    
                    views_text = views_element.text.strip()
                    views = parse_views_string(views_text)
                    
                    if views > highest_views:
                        highest_views = views
                        most_viewed_url = video_link.get_attribute('href')
                        
                except NoSuchElementException:
                    # Bỏ qua nếu không tìm thấy video link hoặc views element trong container này
                    continue
                except Exception as e:
                    print(f"Lỗi khi lấy dữ liệu lượt xem cho một phần tử video: {e}")
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
            print(f"Đã đóng trình duyệt cho {username}.")
    return data

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/get_tiktok_data', methods=['POST'])
def get_tiktok_data_api():
    usernames_to_process = []
    
    usernames_text = request.form.get('usernames')
    if usernames_text:
        lines = usernames_text.splitlines()
        for line in lines:
            parts = [u.strip() for u in line.split(',') if u.strip()]
            usernames_to_process.extend(parts)

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

    usernames_to_process = list(set([re.sub(r'[^a-zA-Z0-9_.]', '', u) for u in usernames_to_process if u]))

    if not usernames_to_process:
        return jsonify({'error': 'Vui lòng cung cấp ít nhất một tên người dùng qua văn bản hoặc tệp.'}), 400

    results = []
    for username in usernames_to_process:
        result = get_tiktok_data_selenium(username)
        results.append(result)

    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))