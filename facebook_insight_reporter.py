import requests
import json
import pandas as pd
from jinja2 import Environment, FileSystemLoader

# --- Cấu hình của bạn ---
# THAY THẾ BẰNG ACCESS TOKEN CỦA BẠN
ACCESS_TOKEN = "EAASjNRkupd4BPFwEFhddB6CRycngtZBJ9YpRG3RSa5hXYNxaUHhEqYCoqW0T1N5rIYNOLjFkMiF5HHcWsYOIUXwYBtEE5cjrzDAIqEShEdw3ymKKDOspVYN4JrRN9yV308qcfbBpIh3ZCZAGAHhNWExvMhZA5vnZCSwptZAEN9m1MkYhOSGfcRvgANW7hZBIJ3vnXs2xbhszgU2Ic5dTYpfP4s9uOayayyUxlp5ZBWbRwk2FOaFxVvWhmgZDZD" 

# THAY THẾ BẰNG ID CỦA FANPAGE CỦA BẠN (Hoặc bạn có thể lấy danh sách các page bạn quản lý)
PAGE_ID = "154375091091347" 

# --- Các hàm hỗ trợ ---

def get_fanpage_insights(page_id, access_token, since_date=None, until_date=None):
    """
    Truy xuất dữ liệu insight cho một fanpage cụ thể.
    Xem thêm các metric tại: https://developers.facebook.com/docs/graph-api/reference/page/insights/
    """
    base_url = f"https://graph.facebook.com/v19.0/{page_id}/insights"
    
    # Các metric phổ biến. Bạn có thể thêm hoặc bớt tùy nhu cầu.
    # Đảm bảo các metric này được hỗ trợ bởi quyền của access token của bạn.
    metrics = [
        "page_fans",                 # Tổng số lượt thích trang
        "page_fan_adds_unique",      # Lượt thích trang mới
        "page_post_engagements",     # Lượt tương tác bài viết (click, like, comment, share)
        "page_impressions_unique",   # Số người tiếp cận bài viết
        "page_actions_post_reactions_total", # Tổng số phản ứng bài viết
        "page_views_total",          # Tổng lượt xem trang
        "page_views_unique"          # Số người xem trang duy nhất
    ]
    
    params = {
        "metric": ",".join(metrics),
        "period": "day",  # "day", "week", "days_28", "lifetime"
        "access_token": access_token
    }

    if since_date:
        params["since"] = since_date
    if until_date:
        params["until"] = until_date

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status() # Ném lỗi cho các mã trạng thái HTTP xấu (4xx hoặc 5xx)
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi API Facebook: {e}")
        return []

def get_pages_managed(access_token):
    """
    Lấy danh sách các fanpage mà người dùng đang quản lý.
    """
    url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi lấy danh sách page: {e}")
        return []

def process_insight_data(insights):
    """
    Xử lý dữ liệu insight thô từ API để dễ dàng hơn cho việc hiển thị.
    """
    processed_data = []
    for insight in insights:
        metric_name = insight.get("name")
        for value_data in insight.get("values", []):
            end_time = pd.to_datetime(value_data["end_time"]).strftime("%Y-%m-%d")
            value = value_data["value"]
            processed_data.append({
                "Ngày": end_time,
                "Metric": metric_name,
                "Giá trị": value
            })
    return pd.DataFrame(processed_data)

def generate_html_report(insights_df, page_name="Fanpage của bạn"):
    """
    Tạo báo cáo HTML từ DataFrame dữ liệu insight.
    """
    # Thiết lập Jinja2 để tải template từ thư mục hiện tại
    env = Environment(loader=FileSystemLoader('.'))
    template = env.from_string(
        """
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Báo Cáo Insight Fanpage - {{ page_name }}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; background-color: #f4f4f4; color: #333; }
                .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                h1 { color: #0056b3; text-align: center; margin-bottom: 20px; }
                h2 { color: #007bff; margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; color: #333; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .note { font-style: italic; color: #666; margin-top: 20px; }
                .metric-section { margin-bottom: 20px; }
                .metric-section h3 { background-color: #e9ecef; padding: 10px; border-radius: 4px; margin-bottom: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Báo Cáo Insight Fanpage: {{ page_name }}</h1>
                <p class="note">Dữ liệu được truy xuất vào {{ current_date }}.</p>

                {% if insights_data %}
                    {% for metric_name, data_group in insights_data.groupby('Metric') %}
                        <div class="metric-section">
                            <h2>{{ metric_name|replace('_', ' ')|title }}</h2>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Ngày</th>
                                        <th>Giá trị</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for row in data_group.itertuples() %}
                                        <tr>
                                            <td>{{ row.Ngày }}</td>
                                            <td>{{ '{:,.0f}'.format(row.Giá trị) if isinstance(row.Giá trị, (int, float)) else row.Giá trị }}</td>
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>Không có dữ liệu insight nào được tìm thấy hoặc có lỗi khi truy xuất.</p>
                {% endif %}
            </div>
        </body>
        </html>
        """
    )

    from datetime import datetime
    current_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # Group insights by metric for better presentation
    # insights_df sẽ được truyền trực tiếp và group trong template
    
    return template.render(
        page_name=page_name,
        insights_data=insights_df,
        current_date=current_date
    )

# --- Logic chính ---
if __name__ == "__main__":
    print("Đang lấy danh sách các Fanpage bạn quản lý...")
    pages = get_pages_managed(ACCESS_TOKEN)
    
    if not pages:
        print("Không tìm thấy Fanpage nào bạn quản lý hoặc Access Token không hợp lệ/thiếu quyền.")
        print("Vui lòng kiểm tra lại ACCESS_TOKEN và các quyền (pages_show_list, pages_read_engagement).")
    else:
        print("Các Fanpage bạn quản lý:")
        for i, page in enumerate(pages):
            print(f"{i+1}. Tên: {page['name']}, ID: {page['id']}")
            
        # Chọn một page để lấy insight, hoặc bạn có thể lặp qua tất cả
        if pages:
            # Ví dụ: Chọn page đầu tiên
            selected_page = pages[0] 
            # Hoặc yêu cầu người dùng nhập
            # try:
            #     choice = int(input("Nhập số thứ tự của Fanpage bạn muốn lấy insight: ")) - 1
            #     if 0 <= choice < len(pages):
            #         selected_page = pages[choice]
            #     else:
            #         print("Lựa chọn không hợp lệ.")
            #         exit()
            # except ValueError:
            #     print("Nhập không hợp lệ.")
            #     exit()
                
            PAGE_ID = selected_page['id']
            PAGE_NAME = selected_page['name']

            print(f"\nĐang lấy insight cho Fanpage: {PAGE_NAME} (ID: {PAGE_ID})...")
            
            # Lấy dữ liệu insight trong 30 ngày gần nhất
            from datetime import datetime, timedelta
            until_date = datetime.now()
            since_date = until_date - timedelta(days=30) 
            
            # Định dạng ngày theo YYYY-MM-DD
            since_str = since_date.strftime("%Y-%m-%d")
            until_str = until_date.strftime("%Y-%m-%d")

            insights = get_fanpage_insights(PAGE_ID, ACCESS_TOKEN, since_date=since_str, until_date=until_str)

            if insights:
                insights_df = process_insight_data(insights)
                if not insights_df.empty:
                    html_content = generate_html_report(insights_df, PAGE_NAME)
                    
                    output_filename = f"bao_cao_insight_{PAGE_NAME.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"
                    with open(output_filename, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print(f"\nBáo cáo HTML đã được tạo thành công: {output_filename}")
                else:
                    print("Không có dữ liệu insight nào được xử lý.")
            else:
                print("Không thể lấy dữ liệu insight từ Fanpage. Vui lòng kiểm tra lại PAGE_ID và ACCESS_TOKEN/quyền.")