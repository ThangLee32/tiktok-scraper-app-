from flask import Flask, render_template, request, jsonify
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import os
import io
import time
import re

app = Flask(__name__)

# Lấy đường dẫn chromedriver từ biến môi trường hoặc mặc định
CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chromedriver.exe'))

def parse_views_string(views_str):
    """Chuyển đổi chuỗi lượt xem (ví dụ: '1.2M', '2.5K') thành số nguyên."""
    views_str = views_str.upper().strip()
    views_str = views_str.replace(' ', '')
    views_str = views_str.replace(',', '')
    
    if 'K' in views_str:
        return int(float(views_str.replace('K', '')) * 1000)
    elif 'M' in views_str:
        return int(float(views_str.replace('M', '')) * 1000000)
    else:
        try:
            return int(views_str)
        except (ValueError, TypeError):
            return 0

def get_tiktok_data_selenium(username):
    """
    Lấy dữ liệu TikTok bao gồm người theo dõi, lượt thích, tổng số video và video có lượt xem cao nhất.
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
        # Khối code này phải được thụt lề vào trong
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        
        # BẬT CHẾ ĐỘ ẨN DANH (HEADLESS) BẮT BUỘC TRÊN MÁY CHỦ
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        
        # Bỏ qua việc thiết lập binary_location để nó tự động tìm
        driver = uc.Chrome(options=options)
        
        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        wait = WebDriverWait(driver, 15)
        
        time.sleep(5) 
        
        # --- LẤY DỮ LIỆU ---
        
        # Lấy số người theo dõi và lượt thích
        try:
            followers_element = wait.until(EC.presence_of_element_located((By.XPATH, '//span[@data-e2e="followers"]/preceding-sibling::strong')))
            data['followers'] = followers_element.text.strip()
        except TimeoutException:
            print(f"Không tìm thấy phần tử người theo dõi cho {username}.")

        try:
            likes_element = wait.until(EC.presence_of_element_located((By.XPATH, '//span[@data-e2e="likes"]/preceding-sibling::strong')))
            data['likes'] = likes_element.text.strip()
        except TimeoutException:
            print(f"Không tìm thấy phần tử lượt thích cho {username}.")

        # Cuộn trang để tải tất cả các video
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_limit = 10
        for i in range(scroll_limit):
            print(f"Đang cuộn trang cho {username}, lần {i+1}...")
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_tiktok_data', methods=['POST'])
def get_tiktok_data_api():
    usernames_to_process = []
    
    # CẬP NHẬT: Xử lý nhập liệu từ trường văn bản để tách tên người dùng đúng cách
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

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=False)