import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from flask import Flask, request, render_template, jsonify, Response
import time
import csv
import io
import re
import random
import os
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Import các thư viện mới cho xử lý ảnh
from PIL import Image
import cv2
import numpy as np

# Lấy đường dẫn tuyệt đối của thư mục chứa app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Thiết lập template_folder sử dụng đường dẫn tuyệt đối
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

def convert_to_int(text):
    """
    Chuyển đổi chuỗi số (có thể chứa 'K', 'M', 'B') thành số nguyên.
    Ví dụ: '10K' -> 10000, '1.2M' -> 1200000.
    """
    if isinstance(text, (int, float)):
        return int(text)
    if not text:
        return 0
    text = text.lower().strip()
    text = text.replace(',', '')
    
    if 'k' in text:
        return int(float(text.replace('k', '')) * 1000)
    elif 'm' in text:
        return int(float(text.replace('m', '')) * 1_000_000)
    elif 'b' in text:
        return int(float(text.replace('b', '')) * 1_000_000_000)
    else:
        try:
            return int(text)
        except ValueError:
            return 0

# Hàm mới để giải CAPTCHA kéo thả (RẤT PHỨC TẠP VÀ KHÔNG ĐẢM BẢO HOẠT ĐỘNG)
def solve_slider_captcha(driver, username):
    print(f"[{username}] Đang cố gắng giải CAPTCHA kéo thả...")
    
    try:
        # 1. Tìm phần tử CAPTCHA chính và thanh trượt
        # Các selector này cần phải CHÍNH XÁC với trang TikTok
        # Dựa trên ảnh bạn cung cấp, có vẻ như đây là Geetest.
        # Geetest có cấu trúc riêng và việc tìm hình ảnh mảnh ghép/lỗ hổng cần phân tích sâu hơn
        # Đây là ví dụ chung cho slider CAPTCHA, có thể không hoạt động với Geetest
        
        captcha_modal_selector = "//div[contains(@class, 'mask-wrapper') or contains(@class, 'captcha_container') or contains(@class, 'geetest_holder')]"
        slider_button_selector = "//div[contains(@class, 'verify-bar-wrapper') or contains(@class, 'geetest_slider_button') or contains(@class, 'geetest_slider')]"
        
        captcha_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, captcha_modal_selector))
        )
        slider_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, slider_button_selector))
        )

        # Chụp ảnh toàn bộ CAPTCHA container
        captcha_container.screenshot('captcha_full.png')
        time.sleep(1) # Chờ ảnh được lưu

        # Tải ảnh và xử lý bằng OpenCV để tìm khoảng cách
        # Giả định: Hình ảnh nền và mảnh ghép được hiển thị rõ ràng trong captcha_full.png
        # Đây là phần cực kỳ phức tạp: bạn cần tìm mảnh ghép và lỗ hổng.
        # Đối với Geetest, thường có 2 hình ảnh: full background và slide piece.
        # Nếu TikTok sử dụng Geetest, bạn cần lấy các URL của các hình ảnh này từ DOM/network request
        # và xử lý chúng riêng.
        # Ví dụ này chỉ xử lý từ một ảnh chụp màn hình duy nhất, rất khó chính xác.
        
        img_rgb = cv2.imread('captcha_full.png')
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)

        # CÁC BƯỚC XỬ LÝ ẢNH SAU ĐÂY LÀ VÍ DỤ RẤT ĐƠN GIẢN VÀ CÓ THỂ KHÔNG HOẠT ĐỘNG
        # Bạn cần tìm hiểu sâu về xử lý ảnh với OpenCV để làm điều này.
        # Ví dụ: dùng Canny edge detection, template matching, v.v.
        
        # Giả định mảnh ghép là một vùng màu khác biệt hoặc có cạnh rõ ràng.
        # Tìm cạnh trong ảnh
        edges = cv2.Canny(img_gray, 50, 150) # Tinh chỉnh ngưỡng
        
        # Ở đây, bạn cần logic để:
        # 1. Tìm hình dạng của mảnh ghép (puzzle piece).
        # 2. Tìm hình dạng của lỗ hổng (hole) trên nền.
        # 3. Tính toán khoảng cách giữa cạnh trái của mảnh ghép và cạnh trái của lỗ hổng.
        
        # Ví dụ cực kỳ đơn giản (KHÔNG THỂ DÙNG THỰC TẾ TRÊN TIKTOK):
        # Giả sử mảnh ghép là một vùng sáng/tối cụ thể
        # _, thresholded = cv2.threshold(img_gray, 200, 255, cv2.THRESH_BINARY_INV)
        # contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # for contour in contours:
        #     x, y, w, h = cv2.boundingRect(contour)
        #     # Nếu đây là mảnh ghép (cần heuristic để xác định kích thước/hình dạng)
        #     if 20 < w < 60 and 20 < h < 60: # Ví dụ kích thước mảnh ghép
        #         piece_x_start = x
        #         # Logic tìm lỗ hổng tương tự
        #         # hole_x_start = ...
        #         # distance = hole_x_start - piece_x_start
        #         # break

        # VỚI GEETEST: CÁCH TIẾP CẬN KHÁC
        # Geetest thường load 2 hình ảnh riêng biệt: full_bg (nền) và slice (mảnh ghép).
        # Bạn phải tải 2 hình ảnh đó về, rồi dùng template matching để tìm slice trong full_bg.
        # Sau đó tính toán khoảng cách pixel.
        
        # Ví dụ giả định khoảng cách (bạn phải thay thế bằng giá trị tính toán được)
        # Nếu không có cách nào khác, bạn có thể thử một vài giá trị cố định, nhưng nó sẽ không đáng tin cậy.
        # Geetest thường cần khoảng cách pixel rất chính xác.
        
        # Để đơn giản, tôi sẽ đặt một khoảng cách giả định. BẠN CẦN THAY THẾ NÓ.
        # Giá trị này phải là khoảng cách pixel mà thanh trượt cần di chuyển
        # Ví dụ, nếu miếng ghép cần di chuyển 250 pixel sang phải
        target_offset_x = random.randint(200, 300) # Đây chỉ là ví dụ!

        print(f"[{username}] Khoảng cách kéo được tính toán: {target_offset_x} pixels.")

        # 2. Mô phỏng hành vi kéo thả tự nhiên
        actions = ActionChains(driver)
        actions.click_and_hold(slider_button).perform()
        
        # Chia nhỏ chuyển động để trông tự nhiên hơn
        steps = 20 # Số bước di chuyển
        x_per_step = target_offset_x / steps
        
        # Hàm tạo đường đi "ease-out" (chậm dần về cuối)
        def ease_out_quart(t):
            return 1 - pow(1 - t, 4)

        for i in range(steps + 1):
            current_x = x_per_step * i
            # Sử dụng hàm ease-out để tạo chuyển động không đều
            eased_x = target_offset_x * ease_out_quart(i / steps)
            
            # Di chuyển theo eased_x, trừ đi vị trí hiện tại để có offset
            if i > 0:
                actions.move_by_offset(eased_x - (target_offset_x * ease_out_quart((i-1)/steps)), 0).perform()
            else:
                actions.move_by_offset(eased_x, 0).perform() # Bước đầu tiên từ 0
            
            time.sleep(random.uniform(0.01, 0.05)) # Độ trễ nhỏ giữa các bước
            
        actions.release().perform()
        print(f"[{username}] Đã thực hiện thao tác kéo thả.")
        time.sleep(random.uniform(3, 7)) # Chờ CAPTCHA xác nhận

        # Kiểm tra xem CAPTCHA đã biến mất chưa
        try:
            WebDriverWait(driver, 5).until_not(
                EC.presence_of_element_located((By.XPATH, captcha_modal_selector))
            )
            print(f"[{username}] CAPTCHA đã biến mất. Giải quyết thành công (có thể).")
            return True
        except TimeoutException:
            print(f"[{username}] CAPTCHA vẫn còn sau khi kéo thả. Giải quyết thất bại.")
            return False

    except TimeoutException:
        print(f"[{username}] Không tìm thấy phần tử CAPTCHA hoặc thanh trượt trong thời gian chờ.")
        return False
    except Exception as e:
        print(f"[{username}] Lỗi khi giải CAPTCHA kéo thả: {e}")
        return False

def get_tiktok_full_data_selenium(username):
    """
    Sử dụng Selenium để thu thập dữ liệu profile TikTok cho một tên người dùng cụ thể.
    """
    driver = None
    data = {
        'username': username,
        'followers': 'N/A',
        'likes': 'N/A',
        'video_count': 'N/A',
        'most_viewed_video_link': 'N/A',
        'most_viewed_video_views': 'N/A',
        'success': False,
        'error': 'Không rõ lỗi',
        'updated_at': 'N/A'
    }
    
    try:
        print(f"Bắt đầu xử lý tài khoản: {username}")

        # Cấu hình ChromeOptions cho undetected_chromedriver
        options = uc.ChromeOptions()
        # options.add_argument('--headless') # Bỏ comment khi muốn chạy ẩn danh
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--log-level=3') 
        options.add_argument('--disable-gpu')
        options.add_argument('--incognito')
        options.add_argument('--start-maximized') 
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-default-apps")
        options.add_argument("--mute-audio")
        options.add_argument('--enable-webgl')
        options.add_argument('--ignore-gpu-blocklist')
        options.add_argument('--enable-quic')
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-application-cache")
        options.add_argument("--disk-cache-size=1")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")

        driver = uc.Chrome(options=options)
        
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        print(f"[{username}] Đã ghi đè navigator.webdriver.")
        print(f"[{username}] Sử dụng User-Agent: {driver.execute_script('return navigator.userAgent;')}")
        
        width = random.randint(1200, 1920)
        height = random.randint(800, 1080)
        driver.set_window_size(width, height)
        print(f"[{username}] Đã đặt kích thước cửa sổ: {width}x{height}")

        driver.get(f"https://www.tiktok.com/@{username}")
        
        print(f"[{username}] Đang chờ trang tải đầy đủ (document.readyState)...")
        WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        print(f"[{username}] document.readyState: complete")

        initial_error_attempts = 0
        max_initial_error_attempts = 5 
        found_content_after_error = False

        while initial_error_attempts < max_initial_error_attempts:
            # === KIỂM TRA VÀ GIẢI CAPTCHA NẾU CÓ ===
            captcha_container_selector = "//div[contains(@class, 'captcha_container') or contains(@class, 'geetest_holder') or contains(@class, 'mask-wrapper')]"
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, captcha_container_selector))
                )
                print(f"[{username}] CAPTCHA đã được phát hiện.")
                if solve_slider_captcha(driver, username):
                    print(f"[{username}] Đã cố gắng giải CAPTCHA. Đang chờ trang tải lại...")
                    time.sleep(random.uniform(7, 15)) # Cho thời gian để CAPTCHA phản hồi và trang tải lại
                    # Sau khi giải CAPTCHA, thử kiểm tra lại nội dung chính
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="followers-count"], div[data-e2e="user-post-item"]'))
                        )
                        found_content_after_error = True
                        break # Thoát vòng lặp nếu thành công
                    except TimeoutException:
                        print(f"[{username}] Nội dung chính không xuất hiện sau khi giải CAPTCHA. Thử lại vòng lặp.")
                        initial_error_attempts += 1 # Tiếp tục vòng lặp
                        continue
                else:
                    data['error'] = 'CAPTCHA kéo thả xuất hiện và không thể giải quyết tự động.'
                    print(f"[{username}] {data['error']}")
                    return data # Thoát nếu không giải được CAPTCHA
            except TimeoutException:
                # Không tìm thấy CAPTCHA, tiếp tục với logic kiểm tra "Something went wrong"
                pass
            except Exception as e:
                data['error'] = f"Lỗi khi xử lý CAPTCHA: {e}"
                print(f"[{username}] {data['error']}")
                return data

            # Logic kiểm tra lỗi "Something went wrong" (chỉ chạy nếu không có CAPTCHA hoặc CAPTCHA đã được xử lý)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="followers-count"], div[data-e2e="user-post-item"]'))
                )
                print(f"[{username}] Phần tử nội dung chính (followers hoặc video) đã xuất hiện, không có lỗi 'Something went wrong'.")
                found_content_after_error = True
                break
            except TimeoutException:
                try:
                    error_message_elem = driver.find_elements(By.XPATH, "//*[contains(text(), 'Something went wrong') or contains(text(), 'Lỗi') or contains(text(), 'Tải lại')]")
                    refresh_button_elem = driver.find_elements(By.XPATH, "//button[contains(., 'Refresh') or contains(., 'Thử lại') or contains(., 'Tải lại')]")
                    
                    if error_message_elem or refresh_button_elem:
                        print(f"[{username}] Phát hiện lỗi 'Something went wrong' hoặc tương tự. Đang thử làm mới trang... ({initial_error_attempts + 1}/{max_initial_error_attempts})")
                        if refresh_button_elem:
                            driver.execute_script("arguments[0].click();", refresh_button_elem[0])
                        else:
                            driver.refresh()
                        time.sleep(random.uniform(7, 15)) 
                        initial_error_attempts += 1
                        continue
                    else:
                        print(f"[{username}] Không tìm thấy lỗi 'Something went wrong', nhưng cũng không tìm thấy phần tử followers. Có thể trang đang tải chậm hoặc cấu trúc đã thay đổi.")
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                        time.sleep(random.uniform(3, 5))
                        initial_error_attempts += 1 
                        continue 
                except Exception as e:
                    print(f"[{username}] Lỗi khi kiểm tra 'Something went wrong' hoặc refresh: {e}. Tiếp tục chờ phần tử chính.")
                    initial_error_attempts += 1
                    time.sleep(random.uniform(5, 10)) 
                    continue
        
        if not found_content_after_error:
            data['error'] = 'Trang tải không thành công hoặc không thể vượt qua lỗi "Something went wrong" hoặc CAPTCHA sau nhiều lần thử.'
            print(f"[{username}] {data['error']}")
            return data
        
        print(f"[{username}] Trang đã tải mà không có lỗi 'Something went wrong' hoặc đã khắc phục được.")

        # === KIỂM TRA TÀI KHOẢN KHÔNG TỒN TẠI ===
        account_exists_on_page_successfully = False
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[data-e2e="user-username"], strong[data-e2e="followers-count"]'))
            )
            account_exists_on_page_successfully = True
            print(f"[{username}] Đã tìm thấy phần tử tên người dùng hoặc người theo dõi. Tài khoản có vẻ tồn tại và tải thành công.")
        except TimeoutException:
            print(f"[{username}] Không tìm thấy phần tử tên người dùng hoặc người theo dõi trong thời gian chờ 10s.")
            pass 

        if not account_exists_on_page_successfully:
            account_not_found_texts = [
                'Không tìm thấy tài khoản này',
                'Couldn\'t find this account', 
                'User not found',
                'Trang này không khả dụng.',
                'This page is not available.'
            ]
            found_not_exist_message = False
            page_source_content = driver.page_source

            for text in account_not_found_texts:
                if text in page_source_content:
                    data['error'] = 'Tài khoản không tồn tại.'
                    print(f"[{username}] {data['error']} (Tìm thấy: '{text}' trong page_source)")
                    found_not_exist_message = True
                    break
            
            if found_not_exist_message:
                return data
            else:
                data['error'] = 'Không thể xác định trạng thái tài khoản hoặc trang không tải đúng cách.'
                print(f"[{username}] {data['error']}")
                return data


        print(f"[{username}] Đang thực hiện di chuyển chuột và nhấn ESC ngẫu nhiên...")
        try:
            action = ActionChains(driver)
            random_x = random.randint(100, driver.execute_script("return window.innerWidth;") - 100)
            random_y = random.randint(100, driver.execute_script("return window.innerHeight;") - 100)
            action.move_by_offset(random_x, random_y).click().perform()
            print(f"[{username}] Đã di chuyển chuột đến ({random_x},{random_y}) và click.")
            action.move_by_offset(-random_x, -random_y).perform() 
            print(f"[{username}] Đã di chuyển chuột về.")

            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            print(f"[{username}] Đã nhấn phím ESC.")
            time.sleep(random.uniform(1, 3)) 
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            print(f"[{username}] Đã nhấn phím ESC lần nữa.")
        except Exception as e:
            print(f"[{username}] Lỗi khi mô phỏng di chuyển chuột/nhấn ESC: {e}")

        print(f"[{username}] Đang tìm pop-up và overlay...")
        overlay_handled = False
        overlay_attempts = 0
        max_overlay_attempts = 5

        while not overlay_handled and overlay_attempts < max_overlay_attempts:
            try:
                not_now_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Not now') or contains(., 'Đóng') or contains(., 'Close') or contains(., 'Sau')]"))
                )
                driver.execute_script("arguments[0].click();", not_now_button)
                print(f"[{username}] Đã nhấp nút 'Not now'/'Đóng'/'Sau'.")
                overlay_handled = True
            except TimeoutException:
                try:
                    accept_cookie_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                    )
                    driver.execute_script("arguments[0].click();", accept_cookie_button)
                    print(f"[{username}] Đã nhấp nút chấp nhận cookie.")
                    overlay_handled = True
                except TimeoutException:
                    try:
                        body = driver.find_element(By.TAG_NAME, 'body')
                        body.send_keys(Keys.ESCAPE)
                        print(f"[{username}] Không tìm thấy nút đóng cụ thể. Thử nhấn ESC.")
                        time.sleep(random.uniform(1, 2))
                        if not driver.find_elements(By.XPATH, "//button[contains(., 'Not now')]") and \
                           not driver.find_elements(By.ID, "onetrust-accept-btn-handler"):
                           overlay_handled = True
                           print(f"[{username}] Đã xác nhận overlay đã biến mất.")
                        else:
                            overlay_attempts += 1
                            print(f"[{username}] Overlay vẫn còn. Lần thử: {overlay_attempts}")
                    except Exception as e:
                        print(f"[{username}] Lỗi khi xử lý overlay bằng ESC: {e}")
                        overlay_attempts += 1
                except Exception as e:
                    print(f"[{username}] Lỗi không xác định khi xử lý overlay: {e}")
                    overlay_attempts += 1
            
            if overlay_attempts >= max_overlay_attempts and not overlay_handled:
                print(f"[{username}] Đã đạt đến giới hạn xử lý overlay. Tiếp tục mà không đóng được.")
                overlay_handled = True

        print(f"[{username}] Đã xử lý xong các pop-up/overlay.")
        time.sleep(random.uniform(3, 7))

        print(f"[{username}] Đang thực hiện cuộn trang ngẫu nhiên để giả lập hành vi người dùng (sau overlay)...")
        scroll_amount_1 = random.uniform(0.1, 0.3)
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_amount_1});")
        time.sleep(random.uniform(2, 4))
        scroll_amount_2 = random.uniform(0.05, 0.15)
        driver.execute_script(f"window.scrollTo(0, -document.body.scrollHeight * {scroll_amount_2});")
        time.sleep(random.uniform(2, 4))
        print(f"[{username}] Đã hoàn thành cuộn trang ngẫu nhiên.")
        
        try:
            followers_elem = WebDriverWait(driver, 15).until( 
                EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="followers-count"]'))
            )
            data['followers'] = followers_elem.text.strip()
            print(f"[{username}] Người theo dõi: {data['followers']}")
        except Exception as e:
            data['followers'] = 'N/A'
            print(f"[{username}] Không tìm thấy người theo dõi: {e}")

        try:
            likes_elem = WebDriverWait(driver, 15).until( 
                EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="likes-count"]'))
            )
            data['likes'] = likes_elem.text.strip()
            print(f"[{username}] Lượt thích: {data['likes']}")
        except Exception as e:
            data['likes'] = 'N/A'
            print(f"[{username}] Không tìm thấy lượt thích: {e}")

        print(f"[{username}] Đang cuộn trang để tải tất cả video...")
        
        video_item_selectors = [
            'div[data-e2e="user-post-item"]', 
            'div.css-x6y88p-DivItemContainerV2', 
            'div.tiktok-video-card-container', 
            'div.tiktok-feed-video-item',
            'div[class*="DivItemContainerV2"]', 
            'div[data-e2e="feed-item-v2"]'
        ]

        seen_video_links = set()
        all_video_elements_unique = [] 

        last_height = driver.execute_script("return document.body.scrollHeight")
        consecutive_no_growth = 0
        max_consecutive_no_growth = 7 
        scroll_attempts = 0
        max_scroll_attempts = 1000 

        scroll_pause_time = random.uniform(4, 9) 

        print(f"[{username}] Bắt đầu vòng lặp cuộn trang...")
        while True:
            initial_video_count_in_set = len(seen_video_links)
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"[{username}] Đã cuộn xuống cuối trang.")
            time.sleep(scroll_pause_time)

            current_video_elements = []
            for video_selector in video_item_selectors:
                try:
                    found_elements = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, video_selector))
                    )
                    current_video_elements.extend(found_elements)
                except TimeoutException:
                    pass
                except Exception as e:
                    pass
            
            new_videos_found_in_this_scroll = 0
            for elem in current_video_elements:
                try:
                    link_elem = None
                    potential_link_selectors = [
                        'a[href*="/video/"]', 
                        'a.css-1mdo0pl-AVideoContainer' 
                    ]
                    for ls in potential_link_selectors:
                        try:
                            link_elem = elem.find_element(By.CSS_SELECTOR, ls)
                            if link_elem and "/video/" in link_elem.get_attribute('href'):
                                break
                            link_elem = None 
                        except NoSuchElementException:
                            continue
                    
                    if link_elem:
                        href = link_elem.get_attribute('href')
                        if href and href not in seen_video_links:
                            seen_video_links.add(href)
                            all_video_elements_unique.append(elem)
                            new_videos_found_in_this_scroll += 1
                except Exception as e:
                    pass
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            current_total_videos = len(seen_video_links)
            
            print(f"[{username}] Chiều cao cũ: {last_height}, Chiều cao mới: {new_height}. Video mới tìm thấy trong lần cuộn này: {new_videos_found_in_this_scroll}. Tổng video duy nhất: {current_total_videos}")

            if new_height == last_height and current_total_videos == initial_video_count_in_set:
                consecutive_no_growth += 1
                print(f"[{username}] Không có tăng trưởng chiều cao hoặc video mới. Số lần liên tiếp: {consecutive_no_growth}/{max_consecutive_no_growth}")
            else:
                consecutive_no_growth = 0
            
            if consecutive_no_growth >= max_consecutive_no_growth:
                print(f"[{username}] Đã đạt đến giới hạn không tăng trưởng ({max_consecutive_no_growth} lần liên tiếp). Dừng cuộn.")
                break
            
            last_height = new_height
            scroll_attempts += 1
            
            if scroll_attempts >= max_scroll_attempts:
                print(f"[{username}] Đã đạt đến giới hạn tổng số lần cuộn ({max_scroll_attempts}). Dừng cuộn.")
                break
            
            # Sau mỗi lần cuộn, kiểm tra lại CAPTCHA (nó có thể xuất hiện bất cứ lúc nào)
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, captcha_container_selector))
                )
                print(f"[{username}] CAPTCHA đã xuất hiện trong khi cuộn. Đang cố gắng giải...")
                if solve_slider_captcha(driver, username):
                    print(f"[{username}] Đã giải CAPTCHA trong khi cuộn. Tiếp tục.")
                    time.sleep(random.uniform(5, 10)) # Chờ trang ổn định
                else:
                    data['error'] = 'CAPTCHA kéo thả xuất hiện trong khi cuộn và không thể giải quyết tự động.'
                    print(f"[{username}] {data['error']}")
                    return data
            except TimeoutException:
                pass # Không có CAPTCHA, tiếp tục cuộn
            except Exception as e:
                print(f"[{username}] Lỗi không mong muốn khi kiểm tra CAPTCHA trong vòng lặp cuộn: {e}")


        data['video_count'] = len(all_video_elements_unique)
        print(f"[{username}] Đã tìm thấy tổng cộng {data['video_count']} video (sau khi cuộn hết và loại bỏ trùng lặp).")

        max_views = -1
        most_viewed_link = 'N/A'
        print(f"[{username}] Đang tìm video có lượt xem cao nhất trong số {len(all_video_elements_unique)} video.")

        view_count_selectors = [
            'strong[data-e2e="video-views"]', 
            'strong.video-count', 
            'span[data-e2e="feed-item-play-count"]',
            'div[class*="tiktok-"][class*="-interaction-number"] span[data-e2e="browse-like-count"]', 
            'div[class*="tiktok-"][class*="-interaction-number"]',
            'span.video-count-text'
        ]
        
        link_selectors = [
            'a[href*="/video/"]', 
            'a.css-1mdo0pl-AVideoContainer'
        ]

        for video_element in all_video_elements_unique:
            try:
                current_views = 0
                current_link = 'N/A'

                view_count_text = '0'
                for view_selector in view_count_selectors:
                    try:
                        view_elems = video_element.find_elements(By.CSS_SELECTOR, view_selector)
                        if view_elems: 
                            view_count_text = view_elems[0].text.strip()
                            break
                        view_count_text = '0' # Reset if not found
                    except Exception:
                        view_count_text = '0' # Reset on error
                        pass
                current_views = convert_to_int(view_count_text)

                link_elem = None
                for ls in link_selectors:
                    try:
                        link_elem = video_element.find_element(By.CSS_SELECTOR, ls)
                        if link_elem and "/video/" in link_elem.get_attribute('href'):
                            break
                        link_elem = None
                    except NoSuchElementException:
                        continue

                if link_elem:
                    current_link = link_elem.get_attribute('href')

                if current_views > max_views and current_link != 'N/A':
                    max_views = current_views
                    most_viewed_link = current_link
            except Exception as e:
                print(f"[{username}] Lỗi khi xử lý một video để lấy lượt xem/link: {e}")
                continue

        if max_views != -1:
            data['most_viewed_video_views'] = str(max_views)
            data['most_viewed_video_link'] = most_viewed_link
            print(f"[{username}] Video có lượt xem cao nhất: {max_views} lượt xem, link: {most_viewed_link}")
        else:
            print(f"[{username}] Không tìm thấy video có lượt xem nào.")

        if data['followers'] != 'N/A' or \
           data['likes'] != 'N/A' or \
           data['video_count'] != 'N/A':
            data['success'] = True
        
        data['error'] = 'N/A' if data['success'] else data['error']
        data['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except WebDriverException as e:
        data['error'] = f"Lỗi WebDriver: {e}"
        print(f"[{username}] Lỗi WebDriver: {e}")
    except Exception as e:
        data['error'] = f"Lỗi không mong muốn: {e}"
        print(f"[{username}] Lỗi không mong muốn: {e}")
    finally:
        if driver:
            try:
                time.sleep(random.uniform(1, 3)) 
                driver.quit()
                print(f"[{username}] Driver đã đóng thành công.")
            except Exception as e:
                print(f"[{username}] Lỗi khi đóng driver: {e}")
    return data

@app.route('/')
def index():
    """
    Render trang HTML chính cho scraper.
    """
    return render_template('tiktok_scraper.html') 

@app.route('/get_tiktok_data', methods=['POST'])
def get_tiktok_data():
    """
    Xử lý yêu cầu POST để lấy dữ liệu TikTok.
    """
    usernames_input = request.form.get('usernames', '').strip()
    file = request.files.get('file')
    output_format = request.args.get('format', 'json')

    all_usernames = []
    if usernames_input:
        all_usernames.extend([u.strip() for u in re.split(r'[,;\n\s]+', usernames_input) if u.strip()])
    
    if file:
        file_content = file.read().decode('utf-8').splitlines()
        all_usernames.extend([u.strip() for u in file_content if u.strip()])

    all_usernames = list(set(all_usernames))

    results = []
    
    for username in all_usernames:
        result = get_tiktok_full_data_selenium(username)
        results.append(result)

    if output_format == 'csv':
        output = io.StringIO()
        fieldnames = ['username', 'followers', 'likes', 'video_count', 'most_viewed_video_link', 'most_viewed_video_views', 'updated_at']
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        
        rows_to_write = []
        for r in results:
            row = {k: v for k, v in r.items() if k in fieldnames}
            rows_to_write.append(row)
        writer.writerows(rows_to_write)

        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers["Content-Disposition"] = "attachment; filename=tiktok_data.csv"
        return response
    else: 
        cleaned_results = []
        for r in results:
            cleaned_r = {k: v for k, v in r.items() if k not in ['success', 'error']}
            cleaned_results.append(cleaned_r)
        return jsonify(cleaned_results)

if __name__ == '__main__':
    app.run(debug=True)