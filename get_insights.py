import requests
import pandas as pd
import webbrowser
import os
from datetime import datetime, timedelta

# ==============================================================================
# CẤU HÌNH - HÃY THAY THÔNG TIN CỦA BẠN VÀO ĐÂY
# ==============================================================================
# Sao chép Access Token bạn lấy từ Graph API Explorer vào đây
ACCESS_TOKEN = 'EAASjNRkupd4BPOlTE0wwGNagwPLGCfVKG4zZA7PQGn4eOpMiHVJJEBZCidbM4zVQQZCaZChSbNvm8OIurcBilCvCoOhAUqtmINGGeldSO4BC4e7gEO5lsZBX2292ozFq7SyAtsCEUOKdnALojF24Jsz9RIZAVVZB2Pd3ZC1trqxaBcDptlEOZB78q9xnzLiYkGlwEou5DbarWaoMSO9EEmZBB8lHzrgtJ2ZC0PvVZB8XNwMbIRGQ8wbDgmc5EAZDZD' 

# Danh sách các chỉ số bạn muốn lấy.
# Tham khảo thêm tại: https://developers.facebook.com/docs/graph-api/reference/page/insights
METRICS_TO_GET = [
    'page_impressions_unique', # Số người đã xem nội dung của Trang (duy nhất)
    'page_post_engagements',   # Số lượt tương tác với bài viết
    'page_fans',               # Tổng số lượt thích trang (cập nhật hàng ngày)
    'page_actions_post_reactions_total', # Tổng số cảm xúc về bài viết
]

# Khoảng thời gian lấy dữ liệu (ví dụ: 30 ngày gần nhất)
UNTIL_DATE = datetime.now()
SINCE_DATE = UNTIL_DATE - timedelta(days=30)

# Chuyển đổi ngày thành định dạng timestamp
since_timestamp = int(SINCE_DATE.timestamp())
until_timestamp = int(UNTIL_DATE.timestamp())

# ==============================================================================
# HÀM LẤY DỮ LIỆU TỪ FACEBOOK GRAPH API
# ==============================================================================

# Đã cập nhật phiên bản API lên v23.0
BASE_URL = 'https://graph.facebook.com/v23.0'

def get_managed_pages(access_token):
    """Lấy danh sách các Fanpage mà người dùng quản lý."""
    url = f"{BASE_URL}/me/accounts"
    params = {'access_token': access_token}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data or not data['data']:
            print("Không tìm thấy trang nào hoặc token không có quyền 'pages_show_list'.")
            return None
            
        return [{'name': page['name'], 'id': page['id']} for page in data['data']]
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi API: {e}")
        print(f"Chi tiết lỗi từ Facebook: {response.text}")
        return None

def get_page_insights(page_id, access_token, metrics, since, until):
    """Lấy dữ liệu Insight cho một Fanpage cụ thể."""
    url = f"{BASE_URL}/{page_id}/insights"
    params = {
        'metric': ','.join(metrics),
        'period': 'day',
        'since': since,
        'until': until,
        'access_token': access_token
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data:
            print(f"Không có dữ liệu insight cho trang ID: {page_id}")
            return None
            
        return data['data']

    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi lấy insight cho trang {page_id}: {e}")
        print(f"Chi tiết lỗi từ Facebook: {response.text}")
        return None

def process_data_to_dataframe(insights_data):
    """Chuyển đổi dữ liệu JSON từ API thành Pandas DataFrame."""
    all_data = []
    for metric_data in insights_data:
        metric_name = metric_data['name']
        for value_point in metric_data['values']:
            if 'value' in value_point:
                date = datetime.strptime(value_point['end_time'], '%Y-%m-%dT%H:%M:%S+%f').strftime('%Y-%m-%d')
                all_data.append({
                    'Chỉ số': metric_name,
                    'Ngày': date,
                    'Giá trị': value_point['value']
                })
    
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df_pivot = df.pivot(index='Ngày', columns='Chỉ số', values='Giá trị').sort_index(ascending=False)
    return df_pivot

# ==============================================================================
# HÀM CHÍNH ĐỂ CHẠY CHƯƠNG TRÌNH
# ==============================================================================

def main():
    """Hàm chính điều khiển luồng chương trình."""
    if ACCESS_TOKEN == 'EAASjNRkupd4BPOlTE0wwGNagwPLGCfVKG4zZA7PQGn4eOpMiHVJJEBZCidbM4zVQQZCaZChSbNvm8OIurcBilCvCoOhAUqtmINGGeldSO4BC4e7gEO5lsZBX2292ozFq7SyAtsCEUOKdnALojF24Jsz9RIZAVVZB2Pd3ZC1trqxaBcDptlEOZB78q9xnzLiYkGlwEou5DbarWaoMSO9EEmZBB8lHzrgtJ2ZC0PvVZB8XNwMbIRGQ8wbDgmc5EAZDZD':
        print("LỖI: Vui lòng thay 'YOUR_ACCESS_TOKEN' bằng Access Token của bạn.")
        return

    pages = get_managed_pages(ACCESS_TOKEN)
    if not pages:
        return

    print(f"Tìm thấy {len(pages)} trang bạn đang quản lý.")

    html_content = """
    <html>
    <head>
        <title>Báo cáo Insight Fanpage</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #3b5998; }
            h2 { color: #8b9dc3; border-bottom: 2px solid #dfe3ee; padding-bottom: 10px; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f0f2f5; font-weight: bold; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
        </style>
    </head>
    <body>
        <h1>Báo cáo Facebook Fanpage Insights (API v23.0)</h1>
        <p>Dữ liệu từ ngày """ + SINCE_DATE.strftime('%d-%m-%Y') + " đến " + UNTIL_DATE.strftime('%d-%m-%Y') + """</p>
    """

    for page in pages:
        print(f"\nĐang lấy dữ liệu cho trang: {page['name']}...")
        insights_data = get_page_insights(page['id'], ACCESS_TOKEN, METRICS_TO_GET, since_timestamp, until_timestamp)

        if insights_data:
            df = process_data_to_dataframe(insights_data)
            if not df.empty:
                print(f" -> Lấy dữ liệu thành công, đang chuyển đổi sang HTML...")
                html_content += f"<h2>{page['name']}</h2>"
                html_content += df.to_html(na_rep='N/A', classes='table table-striped')
            else:
                 print(f" -> Không có dữ liệu insight trong khoảng thời gian đã chọn cho trang {page['name']}.")
        else:
            print(f" -> Không thể lấy dữ liệu cho trang {page['name']}.")
    
    html_content += "</body></html>"

    file_path = 'fanpage_insights.html'
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\nHoàn tất! Đã xuất báo cáo ra file: {file_path}")
    webbrowser.open('file://' + os.path.realpath(file_path))

if __name__ == '__main__':
    main()