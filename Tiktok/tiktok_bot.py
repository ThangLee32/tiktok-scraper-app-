from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def get_tiktok_followers_selenium(username):
    # Đường dẫn đến chromedriver.exe (Thay thế nếu bạn đặt ở nơi khác)
    # Nếu chromedriver.exe nằm cùng thư mục với script, chỉ cần đặt 'chromedriver.exe'
    chromedriver_path = 'D:\Thắng\Fanpage\Total\Python\Tiktok\chromedriver.exe'
    service = Service(chromedriver_path)

    options = webdriver.ChromeOptions()
    # Tùy chọn: Chạy trình duyệt ẩn (không mở cửa sổ trình duyệt)
    # options.add_argument('--headless')
    # Tùy chọn: Vô hiệu hóa GPU để tránh một số lỗi trên các hệ thống nhất định
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Tùy chọn User-Agent để giả lập trình duyệt thực
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


    driver = None # Khởi tạo driver là None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        url = f"https://www.tiktok.com/@{username}"
        driver.get(url)

        # Chờ đợi một chút để trang tải hoàn chỉnh và JavaScript thực thi
        # Chúng ta sẽ chờ cho đến khi phần tử người theo dõi xuất hiện
        # Thời gian chờ tối đa là 20 giây
        wait = WebDriverWait(driver, 20)
        
        # Sử dụng selector bạn đã tìm thấy: strong với data-e2e="followers-count"
        # EC.presence_of_element_located sẽ chờ cho đến khi phần tử có mặt trong DOM
        follower_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'strong[data-e2e="followers-count"]')))
        
        # Nếu tìm thấy phần tử, lấy văn bản của nó
        followers = follower_element.text.strip()
        return followers

    except Exception as e:
        return f"Đã xảy ra lỗi với Selenium: {e}"
    finally:
        if driver:
            driver.quit() # Đảm bảo đóng trình duyệt sau khi hoàn tất

# Tên người dùng TikTok bạn muốn theo dõi
tiktok_username = "pnj_kv6_truelove" # Đảm bảo tên người dùng chính xác

print(f"Bắt đầu theo dõi người theo dõi của @{tiktok_username} bằng Selenium...")

while True:
    followers_count = get_tiktok_followers_selenium(tiktok_username)
    print(f"Số người theo dõi hiện tại của @{tiktok_username}: {followers_count}")
    time.sleep(60) # Chờ 60 giây trước khi kiểm tra lại