from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Cấu hình Facebook Graph API - Sử dụng phiên bản v23.0
GRAPH_API_URL = "https://graph.facebook.com/v23.0/"

@app.route('/', methods=['GET', 'POST'])
def index():
    page_data = []
    engagement_data = {}
    summary_data = {}
    growth_comparison_data = {} # Biến mới để lưu dữ liệu so sánh cùng kỳ năm ngoái
    overall_growth_summary = {} # Biến mới để lưu tổng hợp tăng trưởng cho nhiều pages
    error_message = None

    # Khởi tạo các biến ngày tháng và input
    start_date_str = ""
    end_date_str = ""
    access_token_input = ""
    page_ids_input = ""

    if request.method == 'POST':
        access_token_input = request.form.get('access_token')
        page_ids_input = request.form.get('page_ids_input')

        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else datetime.now()
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else end_date - timedelta(days=180) # Mặc định 6 tháng
        except ValueError:
            error_message = "Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD."
            return render_template('index.html', page_data=page_data, engagement_data=engagement_data, error_message=error_message,
                                   start_date_val=start_date_str, end_date_val=end_date_str,
                                   access_token_val=access_token_input, page_ids_val=page_ids_input,
                                   summary_data=summary_data, growth_comparison_data=growth_comparison_data,
                                   overall_growth_summary=overall_growth_summary)

        since_timestamp = int(start_date.timestamp())
        until_timestamp = int(end_date.timestamp())

        # Tính toán ngày tháng cho cùng kỳ năm ngoái
        start_date_last_year = start_date.replace(year=start_date.year - 1)
        end_date_last_year = end_date.replace(year=end_date.year - 1)
        since_last_year_timestamp = int(start_date_last_year.timestamp())
        until_last_year_timestamp = int(end_date_last_year.timestamp())

        if not access_token_input:
            error_message = "EAASjNRkupd4BPDqLUZCZC6iZCglJ2ZBuu8pVU6m6nofRc2xNC6PJTnx1nQZC1wrnXV2pXkrzuJ7lTiNZAyNsEljDBS4gce72YqUBLAwxNtwNsT9A6C1kDO0R8flGePoYy6ZAZCoKZAhH2zkAig1VRZB85png07blHzs6ut2rDVZCZBhyZBr9amZC1p4m2hG8T6nvWDCnlW9mrQzhb0aGRddhYh92faZC9RYRNBbnALq2vqHoBSFvEgWNrkpcatJ"
        elif not page_ids_input:
            error_message = "473104119228517"
        else:
            page_ids = [id.strip() for id in page_ids_input.split('\n') if id.strip()]
            
            # Khởi tạo tổng cộng các chỉ số để so sánh tổng thể
            overall_current_total = {
                'page_views_total': 0,
                'page_post_engagements': 0,
                'page_fan_adds_unique': 0,
                'page_impressions': 0,
                'page_posts_impressions_unique': 0
            }
            overall_last_year_total = {
                'page_views_total': 0,
                'page_post_engagements': 0,
                'page_fan_adds_unique': 0,
                'page_impressions': 0,
                'page_posts_impressions_unique': 0
            }


            def get_effective_page_token(user_token, page_id_current):
                try:
                    page_token_url = f"{GRAPH_API_URL}{page_id_current}?fields=access_token&access_token={user_token}"
                    response = requests.get(page_token_url)
                    response.raise_for_status()
                    page_token_data = response.json()
                    if 'access_token' in page_token_data:
                        return page_token_data['access_token']
                except requests.exceptions.RequestException as e:
                    print(f"Lỗi khi cố gắng lấy Page Access Token cho {page_id_current}: {e}")
                return user_token

            # Hàm lấy insights cho một khoảng thời gian
            def fetch_insights(page_id, token, since, until):
                metrics_insights = "page_views_total,page_post_engagements,page_fan_adds_unique,page_impressions,page_posts_impressions_unique"
                url_insights = f"{GRAPH_API_URL}{page_id}/insights?metric={metrics_insights}&period=month&since={since}&until={until}&access_token={token}"
                response_insights = requests.get(url_insights)
                response_insights.raise_for_status()
                return response_insights.json()

            # Hàm xử lý dữ liệu insights
            def process_insights_data(data_insights):
                processed = {}
                total_metrics = {
                    'page_views_total': 0,
                    'page_post_engagements': 0,
                    'page_fan_adds_unique': 0,
                    'page_impressions': 0,
                    'page_posts_impressions_unique': 0
                }
                for item in data_insights.get('data', []):
                    metric_name = item['name']
                    processed[metric_name] = []
                    for value_data in item.get('values', []):
                        date_obj = datetime.strptime(value_data['end_time'], '%Y-%m-%dT%H:%M:%S%z')
                        date_str_formatted = date_obj.strftime('%Y-%m')
                        processed[metric_name].append({
                            'date': date_str_formatted,
                            'value': value_data['value']
                        })
                        if metric_name in total_metrics:
                            total_metrics[metric_name] += value_data['value']
                return processed, total_metrics

            for page_id in page_ids:
                token_to_use = get_effective_page_token(access_token_input, page_id)

                page_info = {}
                try:
                    # --- BƯỚC 1: Lấy thông tin cơ bản của trang ---
                    fields_info = "id,name,about,category,likes,website,phone,emails,location,link,fan_count,is_verified,picture"
                    url_info = f"{GRAPH_API_URL}{page_id}?fields={fields_info}&access_token={token_to_use}"
                    response_info = requests.get(url_info)
                    response_info.raise_for_status()

                    data_info = response_info.json()
                    page_info = {
                        'id': data_info.get('id'),
                        'name': data_info.get('name', 'N/A'),
                        'category': data_info.get('category', 'N/A'),
                        'likes': data_info.get('fan_count', 'N/A'),
                        'about': data_info.get('about', 'N/A'),
                        'website': data_info.get('website', 'N/A'),
                        'phone': data_info.get('phone', 'N/A'),
                        'emails': data_info.get('emails', ['N/A'])[0] if data_info.get('emails') else 'N/A',
                        'address': data_info.get('location', {}).get('street', 'N/A') + ", " + \
                                   data_info.get('location', {}).get('city', 'N/A') + ", " + \
                                   data_info.get('location', {}).get('country', 'N/A'),
                        'link': data_info.get('link', 'N/A'),
                        'is_verified': "Có" if data_info.get('is_verified') else "Không",
                        'picture_url': data_info.get('picture', {}).get('data', {}).get('url', '')
                    }
                    page_data.append(page_info)

                    # --- BƯỚC 2: Lấy thông tin tương tác (Insights) cho kỳ hiện tại ---
                    insights_current_period_data = fetch_insights(page_id, token_to_use, since_timestamp, until_timestamp)
                    insights_processed_current, total_metrics_current = process_insights_data(insights_current_period_data)
                    engagement_data[page_id] = insights_processed_current
                    summary_data[page_id] = total_metrics_current

                    # Cộng dồn vào tổng thể
                    for metric, value in total_metrics_current.items():
                        overall_current_total[metric] += value

                    # --- BƯỚC 3: Lấy thông tin tương tác (Insights) cho cùng kỳ năm ngoái ---
                    insights_last_year_data = fetch_insights(page_id, token_to_use, since_last_year_timestamp, until_last_year_timestamp)
                    _, total_metrics_last_year = process_insights_data(insights_last_year_data)

                    # Tính toán tỷ lệ tăng trưởng
                    growth_metrics = {}
                    for metric in total_metrics_current:
                        current_val = total_metrics_current[metric]
                        last_year_val = total_metrics_last_year.get(metric, 0) # Lấy 0 nếu không có data năm ngoái

                        if last_year_val == 0:
                            # Tránh chia cho 0. Nếu hiện tại có giá trị, coi là tăng trưởng rất lớn (hoặc vô hạn)
                            # Nếu cả 2 đều 0, coi là 0%
                            growth_metrics[metric] = "N/A" if current_val == 0 else "N/A (Mới)"
                        else:
                            growth = ((current_val - last_year_val) / last_year_val) * 100
                            growth_metrics[metric] = round(growth, 2) # Làm tròn 2 chữ số thập phân

                    growth_comparison_data[page_id] = {
                        'current': total_metrics_current,
                        'last_year': total_metrics_last_year,
                        'growth': growth_metrics
                    }
                    
                    # Cộng dồn vào tổng thể năm ngoái
                    for metric, value in total_metrics_last_year.items():
                        overall_last_year_total[metric] += value

                except requests.exceptions.HTTPError as e:
                    error_json = {}
                    try:
                        error_json = e.response.json()
                    except json.JSONDecodeError:
                        pass
                    api_error_message = error_json.get('error', {}).get('message', str(e))
                    api_error_code = error_json.get('error', {}).get('code', 'N/A')

                    error_detail = f"Lỗi API ({api_error_code}): {api_error_message}"
                    if "This method must be called with a Page Access Token" in api_error_message:
                        error_detail += " -> Lỗi quyền. Vui lòng đảm bảo User Access Token có đủ quyền ('pages_show_list', 'pages_read_engagement') và ứng dụng đã được duyệt (App Review) nếu trang không thuộc sở hữu/quản lý của bạn. Hoặc bạn cần Page Access Token cụ thể cho trang này."
                    elif "Object with ID" in api_error_message and "does not exist" in api_error_message:
                        error_detail += " -> Page ID có thể không tồn tại, hoặc Access Token không có quyền truy cập trang này."
                    elif "Permission" in api_error_message or "permissions" in api_error_message:
                        error_detail += " -> Access Token thiếu quyền. Đảm bảo bạn đã cấp quyền 'pages_read_engagement' và 'pages_show_list'."
                    elif "valid insights metric" in api_error_message:
                        error_detail += " -> Metric insights không hợp lệ hoặc không khả dụng. Một số metric có thể không áp dụng cho mọi loại trang hoặc đã thay đổi tên."
                    elif "Unsupported get request" in api_error_message:
                        error_detail += " -> Yêu cầu không được hỗ trợ. Có thể Access Token không có quyền truy cập thông tin công khai hoặc trang không tồn tại."

                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Lỗi khi truy xuất Page ID {page_id}: {error_detail}"})
                    summary_data[page_id] = {'error': True, 'message': f"Không thể lấy tổng hợp cho Page ID {page_id} do lỗi."}
                    growth_comparison_data[page_id] = {'error': True, 'message': f"Không thể so sánh tăng trưởng cho Page ID {page_id} do lỗi."}

                except requests.exceptions.ConnectionError as e:
                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Lỗi kết nối mạng cho Page ID {page_id}: {e}. Vui lòng kiểm tra kết nối internet."})
                    summary_data[page_id] = {'error': True, 'message': f"Không thể lấy tổng hợp cho Page ID {page_id} do lỗi kết nối."}
                    growth_comparison_data[page_id] = {'error': True, 'message': f"Không thể so sánh tăng trưởng cho Page ID {page_id} do lỗi kết nối."}
                except json.JSONDecodeError:
                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Phản hồi API không phải JSON hợp lệ cho Page ID {page_id}."})
                    summary_data[page_id] = {'error': True, 'message': f"Không thể lấy tổng hợp cho Page ID {page_id} do phản hồi không hợp lệ."}
                    growth_comparison_data[page_id] = {'error': True, 'message': f"Không thể so sánh tăng trưởng cho Page ID {page_id} do phản hồi không hợp lệ."}
                except Exception as e:
                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Đã xảy ra lỗi không mong muốn cho Page ID {page_id}: {e}"})
                    summary_data[page_id] = {'error': True, 'message': f"Không thể lấy tổng hợp cho Page ID {page_id} do lỗi không mong muốn."}
                    growth_comparison_data[page_id] = {'error': True, 'message': f"Không thể so sánh tăng trưởng cho Page ID {page_id} do lỗi không mong muốn."}

            # Tính toán tỷ lệ tăng trưởng tổng thể nếu có nhiều hơn 1 page hoặc chỉ có 1 page nhưng vẫn muốn tổng thể
            if page_ids: # Chỉ tính nếu có ít nhất một page ID
                for metric in overall_current_total:
                    current_total_val = overall_current_total[metric]
                    last_year_total_val = overall_last_year_total.get(metric, 0)

                    if last_year_total_val == 0:
                        overall_growth_summary[metric] = "N/A" if current_total_val == 0 else "N/A (Mới)"
                    else:
                        growth = ((current_total_val - last_year_total_val) / last_year_total_val) * 100
                        overall_growth_summary[metric] = round(growth, 2)
            
            # Thêm thông tin tổng thể vào summary_data
            if len(page_ids) > 1: # Chỉ thêm hàng "Tổng Cộng" nếu có nhiều hơn 1 trang
                summary_data['overall_total'] = overall_current_total
                growth_comparison_data['overall_total'] = {'growth': overall_growth_summary}


    return render_template('index.html',
                           page_data=page_data,
                           engagement_data=engagement_data,
                           error_message=error_message,
                           start_date_val=start_date_str,
                           end_date_val=end_date_str,
                           start_date_last_year_val=start_date_last_year.strftime('%Y-%m-%d') if 'start_date_last_year' in locals() else '', # Truyền ngày năm ngoái
                           end_date_last_year_val=end_date_last_year.strftime('%Y-%m-%d') if 'end_date_last_year' in locals() else '', # Truyền ngày năm ngoái
                           access_token_val=access_token_input,
                           page_ids_val=page_ids_input,
                           summary_data=summary_data,
                           growth_comparison_data=growth_comparison_data,
                           overall_growth_summary=overall_growth_summary)

if __name__ == '__main__':
    app.run(debug=True)