from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
import requests
import json
from datetime import datetime, timedelta
import csv
from io import StringIO

app = Flask(__name__)

# Cấu hình Facebook Graph API - Sử dụng phiên bản v23.0
GRAPH_API_URL = "https://graph.facebook.com/v23.0/"

@app.route('/', methods=['GET', 'POST'])
def index():
    access_token_input = request.form.get('access_token') if request.method == 'POST' else request.args.get('access_token', '')
    
    if request.method == 'POST' and access_token_input:
        return redirect(url_for('select_pages', access_token=access_token_input))
    
    # Cho phép truy cập trực tiếp select_pages nếu token có sẵn trong query param
    if request.method == 'GET' and access_token_input:
        return redirect(url_for('select_pages', access_token=access_token_input))

    return render_template('index.html', access_token_val=access_token_input)

@app.route('/select_pages', methods=['GET'])
def select_pages():
    access_token = request.args.get('access_token')
    pages = []
    error_message = None

    if not access_token:
        error_message = "Vui lòng nhập Access Token để xem danh sách trang."
        return render_template('index.html', error_message=error_message)

    try:
        # Hàm để lấy tất cả các trang, xử lý phân trang (pagination)
        def fetch_all_pages(token):
            all_pages = []
            url = f"{GRAPH_API_URL}me/accounts?fields=id,name,picture&access_token={token}&limit=100" # Tăng giới hạn lên 100
            while url:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                all_pages.extend(data.get('data', []))
                url = data.get('paging', {}).get('next') # Lấy URL của trang tiếp theo
            return all_pages

        pages = fetch_all_pages(access_token)

        if not pages:
            error_message = "Không tìm thấy trang nào được quản lý bởi Access Token này. Vui lòng kiểm tra quyền `pages_show_list` hoặc Access Token."

    except requests.exceptions.HTTPError as e:
        error_json = {}
        try:
            error_json = e.response.json()
        except json.JSONDecodeError:
            pass
        api_error_message = error_json.get('error', {}).get('message', str(e))
        api_error_code = error_json.get('error', {}).get('code', 'N/A')
        error_message = f"Lỗi API ({api_error_code}) khi lấy danh sách trang: {api_error_message}. Đảm bảo Access Token có quyền `pages_show_list`."
    except requests.exceptions.ConnectionError as e:
        error_message = f"Lỗi kết nối mạng: {e}. Vui lòng kiểm tra kết nối internet."
    except Exception as e:
        error_message = f"Đã xảy ra lỗi không mong muốn khi lấy danh sách trang: {e}"

    return render_template('select_pages.html', pages=pages, access_token_val=access_token, error_message=error_message)


# Tách logic xử lý insights thành một hàm riêng để có thể gọi lại cho cả hiển thị và xuất
def get_processed_insights(access_token_input, selected_page_ids, start_date_str, end_date_str):
    page_data = []
    engagement_data = {}
    summary_data = {}
    growth_comparison_data = {}
    overall_growth_summary = {}
    error_message = None

    # Khởi tạo overall_last_year_total ở đây
    overall_last_year_total = {
        'page_views_total': 0,
        'page_post_engagements': 0,
        'page_fan_adds_unique': 0,
        'page_impressions': 0,
        'page_posts_impressions_unique': 0
    }

    if not selected_page_ids:
        return page_data, engagement_data, summary_data, growth_comparison_data, overall_growth_summary, overall_last_year_total, "Vui lòng chọn ít nhất một Fanpage để xem insights.", False

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else datetime.now()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else end_date - timedelta(days=180)
    except ValueError:
        return page_data, engagement_data, summary_data, growth_comparison_data, overall_growth_summary, overall_last_year_total, "Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD.", False

    since_timestamp = int(start_date.timestamp())
    until_timestamp = int(end_date.timestamp())

    start_date_last_year = start_date.replace(year=start_date.year - 1)
    end_date_last_year = end_date.replace(year=end_date.year - 1)
    since_last_year_timestamp = int(start_date_last_year.timestamp())
    until_last_year_timestamp = int(end_date_last_year.timestamp())
    
    overall_current_total = {
        'page_views_total': 0,
        'page_post_engagements': 0,
        'page_fan_adds_unique': 0,
        'page_impressions': 0,
        'page_posts_impressions_unique': 0
    }
    # overall_last_year_total đã được khởi tạo ở trên

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

    def fetch_insights(page_id, token, since, until):
        metrics_insights = "page_views_total,page_post_engagements,page_fan_adds_unique,page_impressions,page_posts_impressions_unique"
        url_insights = f"{GRAPH_API_URL}{page_id}/insights?metric={metrics_insights}&period=month&since={since}&until={until}&access_token={token}"
        response_insights = requests.get(url_insights)
        response_insights.raise_for_status()
        return response_insights.json()

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

    for page_id in selected_page_ids:
        token_to_use = get_effective_page_token(access_token_input, page_id)

        page_info = {}
        try:
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

            insights_current_period_data = fetch_insights(page_id, token_to_use, since_timestamp, until_timestamp)
            insights_processed_current, total_metrics_current = process_insights_data(insights_current_period_data)
            engagement_data[page_id] = insights_processed_current
            summary_data[page_id] = total_metrics_current

            for metric, value in total_metrics_current.items():
                overall_current_total[metric] += value

            insights_last_year_data = fetch_insights(page_id, token_to_use, since_last_year_timestamp, until_last_year_timestamp)
            _, total_metrics_last_year = process_insights_data(insights_last_year_data)

            growth_metrics = {}
            for metric in total_metrics_current:
                current_val = total_metrics_current[metric]
                last_year_val = total_metrics_last_year.get(metric, 0)

                if last_year_val == 0:
                    growth_metrics[metric] = "N/A" if current_val == 0 else "N/A (Mới)"
                else:
                    growth = ((current_val - last_year_val) / last_year_val) * 100
                    growth_metrics[metric] = round(growth, 2)

            growth_comparison_data[page_id] = {
                'current': total_metrics_current,
                'last_year': total_metrics_last_year,
                'growth': growth_metrics
            }
            
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
    
    if selected_page_ids:
        for metric in overall_current_total:
            current_total_val = overall_current_total[metric]
            last_year_total_val = overall_last_year_total.get(metric, 0)

            if last_year_total_val == 0:
                overall_growth_summary[metric] = "N/A" if current_total_val == 0 else "N/A (Mới)"
            else:
                growth = ((current_total_val - last_year_total_val) / last_year_total_val) * 100
                overall_growth_summary[metric] = round(growth, 2)
        
        if len(selected_page_ids) > 1:
            summary_data['overall_total'] = overall_current_total
            growth_comparison_data['overall_total'] = {'growth': overall_growth_summary}
    
    # Trả về overall_last_year_total cùng với các giá trị khác
    return page_data, engagement_data, summary_data, growth_comparison_data, overall_growth_summary, overall_last_year_total, error_message, True

@app.route('/get_insights', methods=['POST'])
def get_insights():
    access_token_input = request.form.get('access_token')
    selected_page_ids = request.form.getlist('selected_pages')

    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    # Nhận thêm overall_last_year_total từ hàm get_processed_insights
    page_data, engagement_data, summary_data, growth_comparison_data, overall_growth_summary, overall_last_year_total_for_render, error_message, success = \
        get_processed_insights(access_token_input, selected_page_ids, start_date_str, end_date_str)

    if not success:
        # Nếu có lỗi khi get_processed_insights, quay lại trang chọn pages
        pages = []
        try: # Thử lấy lại danh sách pages để hiển thị lại trên form chọn pages
            def fetch_all_pages(token):
                all_pages = []
                url = f"{GRAPH_API_URL}me/accounts?fields=id,name,picture&access_token={token}&limit=100"
                while url:
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()
                    all_pages.extend(data.get('data', []))
                    url = data.get('paging', {}).get('next')
                return all_pages
            pages = fetch_all_pages(access_token_input)
        except Exception as e:
            print(f"Error re-fetching pages for select_pages.html: {e}")
            pages = [] # Đảm bảo pages là rỗng nếu có lỗi

        return render_template('select_pages.html', pages=pages, access_token_val=access_token_input, error_message=error_message)


    return render_template('results.html',
                           page_data=page_data,
                           engagement_data=engagement_data,
                           error_message=error_message,
                           start_date_val=start_date_str,
                           end_date_val=end_date_str,
                           # Pass these for results.html to use for export
                           access_token_val=access_token_input,
                           selected_page_ids=selected_page_ids, 
                           summary_data=summary_data,
                           growth_comparison_data=growth_comparison_data,
                           overall_growth_summary=overall_growth_summary,
                           # Truyền thêm dữ liệu năm trước để hiển thị trong kết quả
                           overall_last_year_total=overall_last_year_total_for_render
                           )

@app.route('/export_insights', methods=['POST'])
def export_insights():
    access_token_input = request.form.get('access_token')
    selected_page_ids = request.form.getlist('selected_pages') # Lấy danh sách ID đã chọn
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    # Gọi lại hàm xử lý insights để lấy dữ liệu thô (đã xử lý)
    # Bây giờ nhận thêm overall_last_year_total
    page_data, engagement_data, summary_data, growth_comparison_data, overall_growth_summary, overall_last_year_total, error_message, success = \
        get_processed_insights(access_token_input, selected_page_ids, start_date_str, end_date_str)

    if not success:
        return error_message, 400 # Trả về lỗi nếu không lấy được dữ liệu

    output = StringIO()
    writer = csv.writer(output)

    # Headers for the CSV
    headers = [
        "Page Name", "Page ID", "Category", "Likes", "About", "Website", "Phone", "Email", "Address", "Link", "Is Verified",
        "Total Page Views (Current)", "Growth Page Views (%)",
        "Total Post Engagements (Current)", "Growth Post Engagements (%)",
        "Total New Fans (Current)", "Growth New Fans (%)",
        "Total Impressions (Current)", "Growth Impressions (%)",
        "Total Unique Reach (Current)", "Growth Unique Reach (%)",
        "Page Views (Last Year)", "Post Engagements (Last Year)", "New Fans (Last Year)", "Impressions (Last Year)", "Unique Reach (Last Year)"
    ]
    writer.writerow(headers)

    for page in page_data:
        if page.get('error'): # Bỏ qua các trang lỗi khi xuất
            continue

        page_id = page['id']
        page_summary = summary_data.get(page_id, {})
        page_growth_comparison = growth_comparison_data.get(page_id, {})
        page_growth = page_growth_comparison.get('growth', {})
        page_last_year = page_growth_comparison.get('last_year', {})

        row = [
            page.get('name', 'N/A'),
            page.get('id', 'N/A'),
            page.get('category', 'N/A'),
            page.get('likes', 'N/A'),
            page.get('about', 'N/A'),
            page.get('website', 'N/A'),
            page.get('phone', 'N/A'),
            page.get('emails', 'N/A'),
            page.get('address', 'N/A'),
            page.get('link', 'N/A'),
            page.get('is_verified', 'N/A'),
            
            page_summary.get('page_views_total', 0),
            page_growth.get('page_views_total', 'N/A'),
            
            page_summary.get('page_post_engagements', 0),
            page_growth.get('page_post_engagements', 'N/A'),
            
            page_summary.get('page_fan_adds_unique', 0),
            page_growth.get('page_fan_adds_unique', 'N/A'),
            
            page_summary.get('page_impressions', 0),
            page_growth.get('page_impressions', 'N/A'),
            
            page_summary.get('page_posts_impressions_unique', 0),
            page_growth.get('page_posts_impressions_unique', 'N/A'),

            # Dữ liệu năm ngoái
            page_last_year.get('page_views_total', 0),
            page_last_year.get('page_post_engagements', 0),
            page_last_year.get('page_fan_adds_unique', 0),
            page_last_year.get('page_impressions', 0),
            page_last_year.get('page_posts_impressions_unique', 0)
        ]
        writer.writerow(row)

    # Thêm hàng tổng cộng nếu có
    if len(selected_page_ids) > 1 and 'overall_total' in summary_data:
        overall_summary = summary_data['overall_total']
        overall_growth = overall_growth_summary
        # Sử dụng overall_last_year_total đã được trả về từ get_processed_insights
        
        overall_row = [
            "TỔNG CỘNG", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A",
            
            overall_summary.get('page_views_total', 0),
            overall_growth.get('page_views_total', 'N/A'),
            
            overall_summary.get('page_post_engagements', 0),
            overall_growth.get('page_post_engagements', 'N/A'),
            
            overall_summary.get('page_fan_adds_unique', 0),
            overall_growth.get('page_fan_adds_unique', 'N/A'),
            
            overall_summary.get('page_impressions', 0),
            overall_growth.get('page_impressions', 'N/A'),
            
            overall_summary.get('page_posts_impressions_unique', 0),
            overall_growth.get('page_posts_impressions_unique', 'N/A'),

            # Dữ liệu tổng năm ngoái
            overall_last_year_total.get('page_views_total', 0),
            overall_last_year_total.get('page_post_engagements', 0),
            overall_last_year_total.get('page_fan_adds_unique', 0),
            overall_last_year_total.get('page_impressions', 0),
            overall_last_year_total.get('page_posts_impressions_unique', 0)
        ]
        writer.writerow(overall_row)


    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers["Content-Disposition"] = f"attachment; filename=facebook_page_insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return response

if __name__ == '__main__':
    app.run(debug=True)