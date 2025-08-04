import os
import time
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# Hàm lấy dữ liệu TikTok bằng Selenium
def get_tiktok_full_data_selenium(username):
    # Cấu hình Chrome Options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Chạy trình duyệt ẩn, không hiển thị giao diện
    options.add_argument('--disable-gpu') # Tắt tăng tốc GPU (thường hữu ích trên Linux/Server)
    options.add_argument('--window-size=1920,1080') # Đặt kích thước cửa sổ cố định
    options.add_argument('--no-sandbox') # Bỏ qua sandbox (cần thiết trên một số hệ thống Linux)
    options.add_argument('--disable-dev-shm-usage') # Vô hiệu hóa việc sử dụng /dev/shm (cần thiết trên một số hệ thống Linux)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36') # Đặt User-Agent để tránh bị phát hiện là bot

    driver = None
    try:
        # Tự động tải xuống và cài đặt ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        # Chờ trang tải xong, sử dụng WebDriverWait để đợi một phần tử cụ thể xuất hiện
        # Tăng thời gian chờ lên 20 giây để đảm bảo tải đủ dữ liệu
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'h2[data-e2e="user-card-name"]'))
        )
        
        # Đợi một chút để đảm bảo tất cả các thành phần động được tải
        time.sleep(3) 

        # Kiểm tra xem có thông báo lỗi "Couldn't find this account" không
        try:
            # Tìm thẻ div có class "tiktok-1c7lg48-DivNotFoundContainer" (hoặc class tương tự)
            not_found_element = driver.find_element(By.CSS_SELECTOR, '.tiktok-1c7lg48-DivNotFoundContainer, .tiktok-jof268-DivNotFoundContainer')
            if not_found_element:
                return {"error": f"Không tìm thấy tài khoản TikTok '{username}'. Vui lòng kiểm tra lại tên người dùng."}
        except NoSuchElementException:
            pass # Không tìm thấy thông báo lỗi, tiếp tục xử lý

        # Lấy tên người dùng
        try:
            user_card_name_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h2[data-e2e="user-card-name"]'))
            )
            scraped_username = user_card_name_element.text
        except TimeoutException:
            return {"error": f"Không thể lấy tên người dùng cho '{username}'."}

        # Lấy số lượng người theo dõi, lượt thích và số lượng video
        followers, likes, video_count = 0, 0, 0
        try:
            # Tìm tất cả các span có data-e2e="followers-count", "likes-count", "video-count"
            counts_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'strong[data-e2e*="-count"]'))
            )
            
            # Kiểm tra và gán giá trị từ các phần tử tìm được
            for element in counts_elements:
                e2e_attribute = element.get_attribute('data-e2e')
                count_value = element.text.replace('K', '000').replace('M', '000000').replace('.', '') # Xử lý K và M, bỏ dấu chấm
                
                if 'followers-count' in e2e_attribute:
                    followers = int(float(count_value)) if count_value else 0
                elif 'likes-count' in e2e_attribute:
                    likes = int(float(count_value)) if count_value else 0
                elif 'video-count' in e2e_attribute:
                    video_count = int(float(count_value)) if count_value else 0
            
            # Đôi khi TikTok thay đổi cấu trúc, hãy thử lấy bằng cách khác nếu cách trên không hoạt động
            if followers == 0 and likes == 0 and video_count == 0:
                # Tìm các phần tử có class 'tiktok-r9z6d-StrongText' hoặc tương tự
                alternative_counts = driver.find_elements(By.CSS_SELECTOR, '.tiktok-r9z6d-StrongText')
                if len(alternative_counts) >= 3:
                    followers = int(alternative_counts[0].text.replace('K', '000').replace('M', '000000').replace('.', ''))
                    likes = int(alternative_counts[1].text.replace('K', '000').replace('M', '000000').replace('.', ''))
                    video_count = int(alternative_counts[2].text.replace('K', '000').replace('M', '000000').replace('.', ''))

        except (TimeoutException, NoSuchElementException):
            return {"error": f"Không thể lấy số liệu thống kê cho '{username}'."}
        
        # Lấy video được xem nhiều nhất
        most_viewed_video_link = "N/A"
        most_viewed_video_views = "N/A"
        try:
            # Tìm tất cả các phần tử video
            video_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-e2e="user-post-item"] a'))
            )
            
            max_views = -1
            for video_element in video_elements:
                link = video_element.get_attribute('href')
                # Cuộn đến phần tử để đảm bảo nó hiển thị và có thể lấy được lượt xem
                driver.execute_script("arguments[0].scrollIntoView();", video_element)
                time.sleep(0.5) # Chờ một chút sau khi cuộn

                try:
                    # Tìm phần tử lượt xem bên trong mỗi video item
                    view_count_element = video_element.find_element(By.CSS_SELECTOR, 'div[data-e2e="feed-video-views"]')
                    views_text = view_count_element.text.replace('K', '000').replace('M', '000000').replace('.', '')
                    current_views = int(float(views_text)) if views_text else 0

                    if current_views > max_views:
                        max_views = current_views
                        most_viewed_video_link = link
                        most_viewed_video_views = current_views
                except NoSuchElementException:
                    continue # Bỏ qua video này nếu không tìm thấy lượt xem

        except TimeoutException:
            # Có thể không có video hoặc không tải được phần tử
            pass
        except NoSuchElementException:
            pass # Không tìm thấy phần tử video

        return {
            "success": True,
            "username": scraped_username,
            "followers": followers,
            "likes": likes,
            "video_count": video_count,
            "most_viewed_video_link": most_viewed_video_link,
            "most_viewed_video_views": most_viewed_video_views
        }

    except TimeoutException as e:
        return {"error": f"Hết thời gian chờ khi tải trang cho '{username}': {e}"}
    except WebDriverException as e:
        return {"error": f"Lỗi WebDriver cho '{username}': {e}"}
    except Exception as e:
        return {"error": f"Đã xảy ra lỗi không xác định khi thu thập dữ liệu cho '{username}': {e}"}
    finally:
        if driver:
            driver.quit() # Đảm bảo đóng trình duyệt sau khi hoàn thành hoặc có lỗi

@app.route('/')
def index():
    # Tạo thư mục 'templates' nếu nó không tồn tại
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # Tạo một file index.html cơ bản nếu nó không tồn tại
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w', encoding='utf-8') as f:
            f.write("""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Công cụ thu thập dữ liệu TikTok</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); }
        h1, h2 { color: #0056b3; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], textarea { width: calc(100% - 22px); padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; }
        button { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-right: 10px; }
        button:hover { background-color: #0056b3; }
        #result, #csv_result { margin-top: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 4px; background-color: #e9ecef; word-wrap: break-word; }
        .error { color: red; font-weight: bold; }
        .success { color: green; font-weight: bold; }
        .spinner {
            border: 4px solid rgba(0, 0, 0, .1);
            border-left-color: #09f;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
            display: inline-block;
            vertical-align: middle;
            margin-left: 10px;
            display: none; /* Hidden by default */
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Công cụ thu thập dữ liệu TikTok</h1>
        
        <div>
            <h2>Thu thập dữ liệu một tài khoản</h2>
            <form id="tiktokForm">
                <label for="username">Tên người dùng TikTok:</label>
                <input type="text" id="username" name="username" placeholder="Ví dụ: tiktok" required>
                <button type="submit">Thu thập dữ liệu</button>
                <div id="spinner" class="spinner"></div>
            </form>
            <div id="result"></div>
        </div>

        <hr>

        <div>
            <h2>Tải xuống dữ liệu nhiều tài khoản (.csv)</h2>
            <form id="csvForm">
                <label for="usernames_csv">Danh sách tên người dùng (cách nhau bởi dấu phẩy):</label>
                <textarea id="usernames_csv" name="usernames" rows="5" placeholder="Ví dụ: tiktok, foryou, funny" required></textarea>
                <button type="submit">Tải xuống CSV</button>
                <div id="csvSpinner" class="spinner"></div>
            </form>
            <div id="csv_result"></div>
        </div>
    </div>

    <script>
        document.getElementById('tiktokForm').addEventListener('submit', async function(event) {
            event.preventDefault();
            const username = document.getElementById('username').value;
            const resultDiv = document.getElementById('result');
            const spinner = document.getElementById('spinner');

            resultDiv.innerHTML = 'Đang thu thập dữ liệu...';
            resultDiv.className = '';
            spinner.style.display = 'inline-block';

            try {
                const response = await fetch('/get_tiktok_data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `username=${encodeURIComponent(username)}`
                });
                const data = await response.json();

                if (data.success) {
                    resultDiv.innerHTML = `
                        <p class="success"><strong>Thu thập thành công!</strong></p>
                        <p><strong>Người dùng:</strong> ${data.username}</p>
                        <p><strong>Người theo dõi:</strong> ${data.followers}</p>
                        <p><strong>Lượt thích:</strong> ${data.likes}</p>
                        <p><strong>Số lượng video:</strong> ${data.video_count}</p>
                        <p><strong>Video được xem nhiều nhất:</strong> <a href="${data.most_viewed_video_link}" target="_blank">${data.most_viewed_video_link}</a> (${data.most_viewed_video_views} lượt xem)</p>
                    `;
                    resultDiv.className = 'success';
                } else {
                    resultDiv.innerHTML = `<p class="error">Lỗi: ${data.error || 'Không thể thu thập dữ liệu.'}</p>`;
                    resultDiv.className = 'error';
                }
            } catch (error) {
                resultDiv.innerHTML = `<p class="error">Đã xảy ra lỗi mạng hoặc máy chủ: ${error.message}</p>`;
                resultDiv.className = 'error';
            } finally {
                spinner.style.display = 'none';
            }
        });

        document.getElementById('csvForm').addEventListener('submit', async function(event) {
            event.preventDefault();
            const usernames = document.getElementById('usernames_csv').value;
            const csvResultDiv = document.getElementById('csv_result');
            const csvSpinner = document.getElementById('csvSpinner');

            csvResultDiv.innerHTML = 'Đang chuẩn bị CSV... Quá trình này có thể mất một lúc tùy thuộc vào số lượng tài khoản.';
            csvResultDiv.className = '';
            csvSpinner.style.display = 'inline-block';

            try {
                const response = await fetch('/download_csv', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `usernames=${encodeURIComponent(usernames)}`
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'tiktok_data.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    csvResultDiv.innerHTML = '<p class="success">Tệp CSV đã được tải xuống thành công!</p>';
                    csvResultDiv.className = 'success';
                } else {
                    const errorData = await response.json();
                    csvResultDiv.innerHTML = `<p class="error">Lỗi khi tải xuống CSV: ${errorData.error || 'Không thể tải xuống tệp CSV.'}</p>`;
                    csvResultDiv.className = 'error';
                }
            } catch (error) {
                csvResultDiv.innerHTML = `<p class="error">Đã xảy ra lỗi mạng hoặc máy chủ: ${error.message}</p>`;
                csvResultDiv.className = 'error';
            } finally {
                csvSpinner.style.display = 'none';
            }
        });
    </script>
</body>
</html>
            """)
    return render_template('index.html')

@app.route('/get_tiktok_data', methods=['POST'])
def get_tiktok_data():
    username = request.form.get('username')
    if not username:
        return jsonify({"success": False, "error": "Vui lòng cung cấp tên người dùng."})

    data = get_tiktok_full_data_selenium(username)
    if "error" in data:
        return jsonify({"success": False, "error": data["error"]})
    return jsonify(data)

@app.route('/download_csv', methods=['POST'])
def download_csv():
    usernames_str = request.form.get('usernames')
    if not usernames_str:
        return jsonify({"success": False, "error": "Vui lòng cung cấp danh sách tên người dùng."})

    usernames = [u.strip() for u in usernames_str.split(',') if u.strip()]
    
    results = []
    for username in usernames:
        print(f"Đang thu thập dữ liệu cho: {username}")
        data = get_tiktok_full_data_selenium(username)
        if data.get("success"):
            results.append({
                "Tên người dùng": data.get("username", "N/A"),
                "Người theo dõi": data.get("followers", "N/A"),
                "Lượt thích": data.get("likes", "N/A"),
                "Số lượng video": data.get("video_count", "N/A"),
                "Link video xem nhiều nhất": data.get("most_viewed_video_link", "N/A"),
                "Lượt xem video nhiều nhất": data.get("most_viewed_video_views", "N/A")
            })
        else:
            results.append({
                "Tên người dùng": username,
                "Người theo dõi": "Lỗi",
                "Lượt thích": "Lỗi",
                "Số lượng video": "Lỗi",
                "Link video xem nhiều nhất": data.get("error", "Lỗi không xác định"),
                "Lượt xem video nhiều nhất": "Lỗi"
            })
            print(f"Lỗi khi thu thập dữ liệu cho {username}: {data.get('error', 'Lỗi không xác định')}")

    if not results:
        return jsonify({"success": False, "error": "Không có dữ liệu nào được thu thập."})

    df = pd.DataFrame(results)
    csv_path = "tiktok_data.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig') # Dùng utf-8-sig cho Excel tiếng Việt

    return send_file(csv_path, as_attachment=True, download_name='tiktok_data.csv', mimetype='text/csv')