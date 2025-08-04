from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Cấu hình Facebook Graph API - Sử dụng phiên bản v23.0 như bạn đã kiểm tra
GRAPH_API_URL = "https://graph.facebook.com/v23.0/" #

@app.route('/', methods=['GET', 'POST'])
def index():
    page_data = []
    engagement_data = {}
    error_message = None
    
    # Khởi tạo các biến ngày tháng và input để tránh UnboundLocalError khi GET request
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
            # Nếu người dùng không nhập ngày, dùng ngày hiện tại và 6 tháng trước
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else datetime.now()
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else end_date - timedelta(days=180) # 6 tháng
        except ValueError:
            error_message = "Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD."
            # Truyền lại giá trị input để không bị mất khi có lỗi
            return render_template('index.html', page_data=page_data, engagement_data=engagement_data, error_message=error_message,
                                   start_date_val=start_date_str, end_date_val=end_date_str,
                                   access_token_val=access_token_input, page_ids_val=page_ids_input)

        # Định dạng lại ngày tháng về Unix timestamp (bắt buộc cho Graph API)
        since_timestamp = int(start_date.timestamp())
        until_timestamp = int(end_date.timestamp())

        if not access_token_input:
            error_message = "EAASjNRkupd4BPDqLUZCZC6iZCglJ2ZBuu8pVU6m6nofRc2xNC6PJTnx1nQZC1wrnXV2pXkrzuJ7lTiNZAyNsEljDBS4gce72YqUBLAwxNtwNsT9A6C1kDO0R8flGePoYy6ZAZCoKZAhH2zkAig1VRZB85png07blHzs6ut2rDVZCZBhyZBr9amZC1p4m2hG8T6nvWDCnlW9mrQzhb0aGRddhYh92faZC9RYRNBbnALq2vqHoBSFvEgWNrkpcatJ"
        elif not page_ids_input:
            error_message = "511152268755597"
        else:
            page_ids = [id.strip() for id in page_ids_input.split('\n') if id.strip()]
            
            # Hàm phụ trợ để lấy Page Access Token từ User Access Token
            # Hoặc trả về chính User Access Token nếu không phải token trang hoặc lỗi
            def get_effective_page_token(user_token, page_id_current):
                # Nếu User Access Token có quyền 'pages_show_list' và user là admin của page_id_current
                # thì Facebook API cho phép lấy Page Access Token trực tiếp từ endpoint của page.
                try:
                    # Endpoint để lấy Page Access Token cho một trang cụ thể từ User Access Token
                    # Đòi hỏi User Access Token phải có quyền 'pages_show_list' và user là quản trị viên của page_id_current
                    # Tham khảo: https://developers.facebook.com/docs/graph-api/reference/page/
                    page_token_url = f"{GRAPH_API_URL}{page_id_current}?fields=access_token&access_token={user_token}"
                    response = requests.get(page_token_url)
                    response.raise_for_status() # Raise HTTPError cho lỗi 4xx/5xx
                    
                    page_token_data = response.json()
                    
                    if 'access_token' in page_token_data:
                        # Trả về Page Access Token cụ thể cho trang này
                        return page_token_data['access_token']
                except requests.exceptions.RequestException as e:
                    print(f"Lỗi khi cố gắng lấy Page Access Token cho {page_id_current} từ User Access Token: {e}")
                except Exception as e:
                    print(f"Lỗi không mong muốn khi lấy Page Access Token cho {page_id_current}: {e}")
                
                # Mặc định, nếu không thể lấy được Page Access Token cụ thể, sử dụng User Access Token ban đầu
                return user_token

            for page_id in page_ids:
                # Cố gắng lấy Page Access Token cho từng trang. Nếu không được, sẽ dùng User Access Token.
                token_to_use = get_effective_page_token(access_token_input, page_id)

                page_info = {}
                try:
                    # --- BƯỚC 1: Lấy thông tin cơ bản của trang ---
                    # Thêm 'picture' để lấy URL ảnh đại diện của page
                    fields = "id,name,about,category,likes,website,phone,emails,location,link,fan_count,is_verified,picture"
                    url_info = f"{GRAPH_API_URL}{page_id}?fields={fields}&access_token={token_to_use}"
                    response_info = requests.get(url_info)
                    response_info.raise_for_status() # Sẽ raise HTTPError cho lỗi 4xx/5xx
                    
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
                        'picture_url': data_info.get('picture', {}).get('data', {}).get('url', '') # Lấy URL ảnh đại diện
                    }
                    
                    # --- BƯỚC 2: Lấy thông tin tương tác (Insights) ---
                    # Các metrics phổ biến và thường khả dụng trên v23.0
                    # Đã loại bỏ page_engaged_users và page_impressions_unique để tránh lỗi #100 The value must be a valid insights metric
                    metrics = "page_views_total,page_post_engagements,page_fan_adds_unique" 
                    url_insights = f"{GRAPH_API_URL}{page_id}/insights?metric={metrics}&period=month&since={since_timestamp}&until={until_timestamp}&access_token={token_to_use}"
                    
                    response_insights = requests.get(url_insights)
                    response_insights.raise_for_status() # Sẽ raise HTTPError cho lỗi 4xx/5xx
                    
                    data_insights = response_insights.json()
                    
                    # Xử lý dữ liệu insights để dễ hiển thị
                    insights_processed = {}
                    for item in data_insights.get('data', []):
                        metric_name = item['name']
                        insights_processed[metric_name] = []
                        for value_data in item.get('values', []):
                            date_obj = datetime.strptime(value_data['end_time'], '%Y-%m-%dT%H:%M:%S%z')
                            date_str_formatted = date_obj.strftime('%Y-%m')
                            insights_processed[metric_name].append({
                                'date': date_str_formatted,
                                'value': value_data['value']
                            })
                    
                    engagement_data[page_id] = insights_processed
                    page_data.append(page_info)
                
                except requests.exceptions.HTTPError as e:
                    # Bắt lỗi HTTP cụ thể để có thông báo rõ ràng hơn
                    error_json = {}
                    try:
                        error_json = e.response.json()
                    except json.JSONDecodeError:
                        pass # Không thể decode JSON lỗi, dùng thông báo mặc định
                    
                    api_error_message = error_json.get('error', {}).get('message', str(e))
                    api_error_code = error_json.get('error', {}).get('code', 'N/A')

                    error_detail = f"Lỗi API ({api_error_code}): {api_error_message}"
                    
                    if "This method must be called with a Page Access Token" in api_error_message: #
                        error_detail += " -> Lỗi quyền. Vui lòng đảm bảo User Access Token có đủ quyền (pages_show_list, pages_read_engagement) và ứng dụng đã được duyệt (App Review) nếu trang không thuộc sở hữu/quản lý của bạn. Hoặc bạn cần Page Access Token cụ thể cho trang này."
                    elif "Object with ID" in api_error_message and "does not exist" in api_error_message:
                        error_detail += " -> Page ID có thể không tồn tại, hoặc Access Token không có quyền truy cập trang này."
                    elif "Permission" in api_error_message or "permissions" in api_error_message:
                         error_detail += " -> Access Token thiếu quyền. Đảm bảo bạn đã cấp quyền 'pages_read_engagement' và 'pages_show_list'."
                    elif "valid insights metric" in api_error_message: #
                         error_detail += " -> Metric insights không hợp lệ hoặc không khả dụng. Một số metric có thể không áp dụng cho mọi loại trang hoặc đã thay đổi tên."
                    elif "Unsupported get request" in api_error_message:
                         error_detail += " -> Yêu cầu không được hỗ trợ. Có thể Access Token không có quyền truy cập thông tin công khai hoặc trang không tồn tại."


                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Lỗi khi truy xuất Page ID {page_id}: {error_detail}"})
                
                except requests.exceptions.ConnectionError as e:
                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Lỗi kết nối mạng cho Page ID {page_id}: {e}. Vui lòng kiểm tra kết nối internet."})
                except json.JSONDecodeError:
                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Phản hồi API không phải JSON hợp lệ cho Page ID {page_id}."})
                except Exception as e:
                    page_data.append({'id': page_id, 'name': 'Lỗi', 'error': f"Đã xảy ra lỗi không mong muốn cho Page ID {page_id}: {e}"})

    return render_template('index.html', 
                           page_data=page_data, 
                           engagement_data=engagement_data, 
                           error_message=error_message,
                           start_date_val=start_date_str, 
                           end_date_val=end_date_str,
                           access_token_val=access_token_input, # Truyền lại giá trị để giữ trong form
                           page_ids_val=page_ids_input) # Truyền lại giá trị để giữ trong form

if __name__ == '__main__':
    app.run(debug=True)