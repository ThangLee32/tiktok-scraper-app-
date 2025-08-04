import gspread
import pandas as pd
from TikTokApi import TikTokApi
import re
from datetime import datetime
import time
import asyncio
import os

# Cấu hình logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Cấu hình của bạn ---
# Đảm bảo các đường dẫn và giá trị này là chính xác và CÓ DẤU NHÁY ĐƠN/KÉP
GOOGLE_SHEET_KEY_PATH = r'D:\Thắng\Fanpage\Total\Python\Tiktok\service_account.json'
GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1VHg9ZmbdqjZsYbU9SwdgClcjbBeoiS2492Gfu-sZpPM/edit?usp=sharing'
WORKSHEET_NAME = 'Cụm 1'

# Cấu hình TikTokApi - SỬ DỤNG TOÀN BỘ COOKIES (PHƯƠNG PHÁP KHUYẾN NGHỊ NHẤT)
# BẠN PHẢI LẤY CÁC GIÁ TRỊ NÀY MỚI NHẤT TỪ TRÌNH DUYỆT CỦA BẠN (TikTok.com -> F12 -> Application -> Cookies)
TIKTOK_COOKIES = {
    "sessionid": "aa086d5f30057275dbb718fc3ebe4b23", # DÁN GIÁ TRỊ SESSIONID CỦA BẠN VÀO ĐÂY
    "msToken": "2iMSnMSal4KW6cblasLqA_n8j30gic2VCpmBmA7ro-PRciHh0JcNh8Hl-o6lXvp4jbZGfl3dI4D5hhJ9iDAvd1wWmU1_cZBo0NPwbbzdSzGRXKSksw9H3yLloQfiJCWIlFW0C1qGAa2xgdbGBqmpxISX", # DÁN GIÁ TRỊ MSTOKEN CỦA BẠN VÀO ĐÂY
    "tt_csrf_token": "DQFxb6EO-NTh-p0UnxfaOqbUagV2JP45w6Lg", # DÁN GIÁ TRỊ TT_CSRF_TOKEN CỦA BẠN VÀO ĐÂY (nếu có)
    # Thêm các cookie khác nếu cần thiết (ví dụ: 'odin_tt'...)
}

# --- Hàm hỗ trợ để lấy ID video từ URL TikTok ---
def get_video_id_from_url(url):
    match = re.search(r'video/(\d+)', url)
    if match:
        return match.group(1)
    return None

# --- Hàm cập nhật Google Sheet ---
def update_google_sheet(worksheet, new_data_list, link_column_name="Link video tiktok"):
    if not new_data_list:
        logging.info("Không có dữ liệu mới để cập nhật Google Sheet.")
        return

    current_data = worksheet.get_all_records()
    current_df = pd.DataFrame(current_data)
    headers = worksheet.row_values(1)
    
    updates = [] # Danh sách các đối tượng Cell để cập nhật hàng loạt

    for item in new_data_list:
        link = item.get(link_column_name)
        if link:
            row_index = current_df[current_df[link_column_name] == link].index
            if not row_index.empty:
                actual_row_number = row_index[0] + 2 # +1 cho index base 0, +1 cho hàng tiêu đề

                cell_updates_for_row = []
                for col_idx, header in enumerate(headers):
                    if header in item and item[header] is not None: # Chỉ cập nhật các cột có dữ liệu mới và không rỗng
                        cell = gspread.models.Cell(row=actual_row_number, col=col_idx + 1) # col_idx + 1 vì gspread 1-based
                        cell.value = item[header]
                        cell_updates_for_row.append(cell)
                updates.extend(cell_updates_for_row)
                logging.info(f"Đã chuẩn bị cập nhật cho hàng {actual_row_number} (Link: {link})")
            else:
                logging.warning(f"Không tìm thấy liên kết '{link}' trong Google Sheet. Bỏ qua cập nhật cho liên kết này.")
        else:
            logging.warning("Bỏ qua mục do thiếu liên kết.")

    if updates:
        try:
            worksheet.update_cells(updates) # Sử dụng update_cells thay vì batch_update
            logging.info("Đã cập nhật Google Sheet thành công với dữ liệu TikTok mới.")
        except Exception as e:
            logging.error(f"Lỗi trong quá trình cập nhật hàng loạt Google Sheet: {e}")
    else:
        logging.info("Không có cập nhật ô nào được chuẩn bị.")


# --- Hàm chính để thu thập dữ liệu TikTok (sử dụng async) ---
async def collect_tiktok_data(links, auth_method):
    results = []
    api_instance = None
    MAX_RETRIES = 3
    RETRY_DELAY = 5 # seconds

    try:
        if auth_method.get('cookies'):
            api_instance = TikTokApi(cookies=auth_method['cookies'])
            logging.info("Đang sử dụng TikTokApi với xác thực cookie đầy đủ.")
        elif auth_method.get('ms_token'):
            api_instance = TikTokApi(ms_token=auth_method['ms_token'])
            logging.info("Đang sử dụng TikTokApi với xác thực ms_token.")
        elif auth_method.get('session_id'):
            api_instance = TikTokApi(session_id=auth_method['session_id'])
            logging.info("Đang sử dụng TikTokApi với xác thực session_id.")
        else:
            logging.error("Không có thông tin xác thực nào được cung cấp cho TikTokApi.")
            return []

        await api_instance.create_sessions(num_sessions=1, sleep_after=3, browser=os.getenv("TIKTOK_BROWSER", "chromium"))
        logging.info("TikTokApi đã được khởi tạo và session đã được tạo thành công.")

    except Exception as e:
        logging.error(f"Lỗi khi khởi tạo hoặc tạo session cho TikTokApi: {e}")
        logging.error("Vui lòng kiểm tra lại thông tin xác thực (session_id/ms_token/cookies) và đảm bảo TikTokApi đã được cập nhật.")
        return []

    for link in links:
        video_id = get_video_id_from_url(link)
        if not video_id:
            logging.warning(f"Không thể trích xuất ID video từ liên kết: {link}. Bỏ qua.")
            continue

        for attempt in range(MAX_RETRIES):
            try:
                logging.info(f"Thử lần {attempt + 1}/{MAX_RETRIES} để lấy dữ liệu cho ID video: {video_id}")
                video = await api_instance.video(id=video_id).info()

                data = {
                    "Link video tiktok": link,
                    "Video ID": video_id,
                    "Tên kênh": video.get('author', {}).get('nickname'),
                    "ID kênh": video.get('author', {}).get('id'),
                    "Tổng số lượt thích": video.get('stats', {}).get('diggCount'),
                    "Tổng số lượt chia sẻ": video.get('stats', {}).get('shareCount'),
                    "Tổng số bình luận": video.get('stats', {}).get('commentCount'),
                    "Tổng số lượt xem": video.get('stats', {}).get('playCount'),
                    "Ngày đăng": datetime.fromtimestamp(video.get('createTime')).strftime('%Y-%m-%d %H:%M:%S') if video.get('createTime') else None
                }
                results.append(data)
                logging.info(f"Đã lấy dữ liệu thành công cho ID video: {video_id}")
                await asyncio.sleep(2) # Thêm độ trễ giữa các request để tránh bị chặn
                break # Thoát vòng lặp thử lại nếu thành công
            except Exception as e:
                logging.error(f"Lỗi khi lấy dữ liệu cho ID video {video_id} (Liên kết: {link}): {e}")
                if attempt < MAX_RETRIES - 1:
                    sleep_time = RETRY_DELAY * (2 ** attempt) # Độ trễ lũy thừa
                    logging.info(f"Đang thử lại sau {sleep_time} giây...")
                    await asyncio.sleep(sleep_time)
                else:
                    logging.error(f"Thất bại khi lấy dữ liệu cho ID video {video_id} sau {MAX_RETRIES} lần thử. Bỏ qua.")
    
    try:
        await api_instance.force_close_browser() 
        logging.info("Đã đóng trình duyệt TikTokApi.")
    except Exception as e:
        logging.warning(f"Không thể đóng trình duyệt TikTokApi: {e}")

    return results

# --- Hàm chính của chương trình ---
async def main():
    # --- Khởi tạo kết nối Google Sheet ---
    try:
        gc = gspread.service_account(filename=GOOGLE_SHEET_KEY_PATH)
        spreadsheet = gc.open_by_url(GOOGLE_SHEET_URL)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        logging.info(f"Đã kết nối thành công tới Google Sheet '{WORKSHEET_NAME}'")
    except Exception as e:
        logging.error(f"Lỗi khi kết nối Google Sheet: {e}")
        logging.error("Vui lòng kiểm tra lại GOOGLE_SHEET_KEY_PATH, GOOGLE_SHEET_URL và quyền truy cập của Service Account.")
        return # Thoát chương trình nếu không kết nối được Google Sheet

    # --- Đọc dữ liệu từ Google Sheet ---
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # Kiểm tra cột "Link video tiktok" có tồn tại không
    if "Link video tiktok" not in df.columns:
        logging.error("Lỗi: Không tìm thấy cột 'Link video tiktok' trong Google Sheet.")
        logging.error(f"Các cột hiện có: {df.columns.tolist()}")
        return # Thoát chương trình nếu thiếu cột

    tiktok_links = df["Link video tiktok"].tolist() 
    logging.info(f"Tìm thấy {len(tiktok_links)} link TikTok từ Google Sheet.")

    # Cấu hình xác thực TikTok
    auth_config = {
        'cookies': TIKTOK_COOKIES, # Đảm bảo TIKTOK_COOKIES được định nghĩa chính xác
    }

    # Thu thập dữ liệu TikTok
    tiktok_results = await collect_tiktok_data(tiktok_links, auth_config)
    
    if tiktok_results:
        logging.info(f"Đã thu thập dữ liệu cho {len(tiktok_results)} video TikTok. Đang chuẩn bị cập nhật Google Sheet.")
        update_google_sheet(worksheet, tiktok_results)
    else:
        logging.info("Không có dữ liệu TikTok nào được thu thập. Không có gì để cập nhật trong Google Sheet.")

# Chạy hàm main khi script được thực thi
if __name__ == "__main__":
    asyncio.run(main())