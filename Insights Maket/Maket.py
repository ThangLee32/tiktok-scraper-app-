import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from fake_useragent import UserAgent # Import thư viện mới

def scrape_shopee_products(keyword, num_pages=3):
    """
    Cào dữ liệu sản phẩm trang sức từ Shopee dựa trên từ khóa.
    Args:
        keyword (str): Từ khóa tìm kiếm (ví dụ: "nhẫn vàng", "vòng cổ bạc").
        num_pages (int): Số lượng trang muốn cào.
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu sản phẩm.
    """
    base_url = "https://shopee.vn/search?keyword="
    products_data = []
    ua = UserAgent() # Khởi tạo đối tượng UserAgent

    print(f"Bắt đầu cào dữ liệu cho từ khóa: '{keyword}'...")

    for page in range(num_pages):
        url = f"{base_url}{keyword}&page={page}"
        print(f"Đang cào trang: {page + 1}/{num_pages} - URL: {url}")
        
        # Lấy một User-Agent ngẫu nhiên cho mỗi yêu cầu
        headers = {
            "User-Agent": ua.random, 
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8" # Thêm Accept-Language
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status() 

            soup = BeautifulSoup(response.text, 'html.parser')

            # Cần kiểm tra lại class name trên trang Shopee thực tế vì chúng thường xuyên thay đổi
            # Bạn có thể mở trình duyệt, vào trang tìm kiếm của Shopee với từ khóa của bạn
            # và sử dụng "Inspect Element" (F12) để tìm đúng class.
            # Các class sau đây là ví dụ và có thể cần được cập nhật:
            product_cards = soup.find_all('div', class_='shopee-search-item-result__item')

            if not product_cards:
                print(f"Không tìm thấy thẻ sản phẩm nào trên trang {page + 1}. Có thể cấu trúc HTML đã thay đổi, bị chặn hoặc trang trống.")
                break

            for card in product_cards:
                try:
                    # Cập nhật các class name này dựa trên F12 của bạn
                    name_tag = card.find('div', class_='_1yN3pW _1eH_D1') # Tên sản phẩm
                    price_tag = card.find('span', class_='_2910Qy') # Giá
                    sales_tag = card.find('div', class_='_1-lVqM') # Lượt bán

                    name = name_tag.text.strip() if name_tag else "N/A"
                    price = price_tag.text.strip() if price_tag else "N/A"
                    sales = sales_tag.text.strip() if sales_tag else "N/A"

                    products_data.append({
                        'Tên Sản Phẩm': name,
                        'Giá': price,
                        'Lượt Bán': sales
                    })
                except Exception as e:
                    # print(f"Lỗi khi xử lý thẻ sản phẩm trên trang {page+1}: {e}")
                    continue # Bỏ qua thẻ bị lỗi và tiếp tục

            # Tăng thời gian chờ ngẫu nhiên hơn
            sleep_time = random.uniform(5, 10) # Tăng lên 5-10 giây
            print(f"Tạm dừng {sleep_time:.2f} giây...")
            time.sleep(sleep_time) 

        except requests.exceptions.RequestException as e:
            print(f"Lỗi kết nối hoặc HTTP trên trang {page + 1}: {e}")
            break
        except Exception as e:
            print(f"Lỗi không xác định trên trang {page + 1}: {e}")
            break

    df = pd.DataFrame(products_data)
    print("Hoàn tất cào dữ liệu.")
    return df

if __name__ == "__main__":
    keyword_to_search = "nhẫn bạc" # Hoặc "trang sức vàng"
    shopee_df = scrape_shopee_products(keyword_to_search, num_pages=5) # Thử cào ít trang hơn trước

    if not shopee_df.empty:
        print("\nDữ liệu sản phẩm thu thập được:")
        print(shopee_df.head())
        shopee_df.to_csv(f'{keyword_to_search}_shopee_data.csv', index=False, encoding='utf-8-sig')
        print(f"\nDữ liệu đã được lưu vào file: {keyword_to_search}_shopee_data.csv")
    else:
        print("Không có dữ liệu nào được thu thập.")