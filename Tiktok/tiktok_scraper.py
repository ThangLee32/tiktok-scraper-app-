import requests
import re
import json
from bs4 import BeautifulSoup
import time

def get_tiktok_stats(username):
    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
    }

    try:
        print(f"Đang gửi yêu cầu tới {url}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        json_data_str = None
        
        # Tìm thẻ script với id='SIGI_STATE' đầu tiên
        script_tag_sigi = soup.find('script', id='SIGI_STATE')
        if script_tag_sigi:
            json_data_str = script_tag_sigi.string
            print("Đã tìm thấy thẻ script SIGI_STATE.")
        
        # Nếu không tìm thấy SIGI_STATE, tìm thẻ script chứa '__DEFAULT_SCOPE__'
        if not json_data_str:
            print("Không tìm thấy thẻ script SIGI_STATE. Đang tìm thẻ script chứa '__DEFAULT_SCOPE__'.")
            # Tìm tất cả các thẻ script không có thuộc tính 'src'
            all_scripts = soup.find_all('script', src=False) 
            for script in all_scripts:
                if script.string and '__DEFAULT_SCOPE__' in script.string:
                    json_data_str = script.string
                    print("Đã tìm thấy thẻ script chứa '__DEFAULT_SCOPE__'.")
                    break
            
        if not json_data_str:
            print("Không tìm thấy thẻ script phù hợp hoặc nội dung rỗng.")
            return None

        # Bước quan trọng: Trích xuất chính xác khối JSON bằng regex
        # Pattern này tìm kiếm một đối tượng JSON bắt đầu bằng '{"__DEFAULT_SCOPE__":'
        # và kết thúc với '}' đóng phù hợp nhất.
        # re.DOTALL để khớp với cả ký tự xuống dòng.
        # re.escape để tránh các ký tự đặc biệt trong chuỗi tìm kiếm như "{" hay ":"
        
        # Thử một regex mạnh mẽ hơn một chút, tìm từ khóa cụ thể.
        # Chúng ta biết rằng JSON bắt đầu bằng '{"__DEFAULT_SCOPE__":'
        # và các khóa như "webapp.user-page" sẽ nằm trong đó.
        
        # Dòng bạn đã gửi gây lỗi: {"__DEFAULT_SCOPE__":{"webapp.app-context": {"language":"en", "region":"VN", ...
        # Có thể regex trước đó đã cắt không đúng hoặc có vấn đề với các ký tự thoát.

        # Regex mới: tìm '{"__DEFAULT_SCOPE__":' và sau đó lấy mọi thứ cho đến khi tìm thấy ']}'
        # Đây là một thử nghiệm, có thể cần điều chỉnh thêm tùy thuộc vào cách TikTok nhúng JSON
        match = re.search(r'\{"__DEFAULT_SCOPE__":.*?\}\s*\}\s*$', json_data_str, re.DOTALL)
        if not match:
            # Nếu regex trên không khớp, thử một regex khác để tìm cụm '{"__DEFAULT_SCOPE__":'
            # và sau đó lấy toàn bộ phần còn lại của string, sau đó cố gắng phân tích JSON.
            # Điều này ít chính xác hơn nhưng có thể hoạt động nếu phần còn lại của script tag là JSON.
            match = re.search(r'\{"__DEFAULT_SCOPE__":', json_data_str, re.DOTALL)
            if not match:
                print("Không tìm thấy JSON hợp lệ (regex match) trong thẻ script.")
                print(f"Nội dung script tag (một phần, 500 ký tự đầu): {json_data_str[:500]}...")
                return None
            
            # Lấy toàn bộ chuỗi từ vị trí khớp regex trở đi
            json_content = json_data_str[match.start():]
            
            # Thử tìm vị trí của dấu ngoặc nhọn đóng cuối cùng của JSON
            # Điều này là rất phức tạp vì có thể có nhiều dấu ngoặc nhọn lồng nhau.
            # Cách an toàn nhất là tìm dấu ngoặc nhọn đóng cuối cùng của toàn bộ thẻ script.
            # Tuy nhiên, nếu có mã JS khác sau JSON, cách này cũng sẽ fail.
            # Ta sẽ dùng cách đơn giản hơn: loại bỏ các ký tự không phải JSON ở cuối.
            # Thử cắt chuỗi ở dấu ngoặc nhọn đóng cuối cùng.
            last_brace_index = json_content.rfind('}')
            if last_brace_index != -1:
                json_content = json_content[:last_brace_index + 1]
            
            print("Đã thử phương pháp trích xuất JSON thứ hai.")

        else:
            json_content = match.group(0)

        # Xử lý các ký tự thoát có thể có trong chuỗi JSON
        # json_content = json_content.replace(r'\"', '"').replace(r'\/', '/')
        # Thư viện json.loads thường tự xử lý các ký tự thoát hợp lệ.
        # Việc replace thủ công có thể gây lỗi nếu có các ký tự thoát thực sự cần thiết.
        # Tuy nhiên, nếu lỗi vẫn tiếp diễn, chúng ta có thể cần xem xét lại.
        
        # In ra nội dung JSON trước khi parse để debug
        print(f"Nội dung JSON được trích xuất (một phần, 500 ký tự đầu): {json_content[:500]}...")

        json_data = json.loads(json_content)

        # Truy cập các số liệu theo đường dẫn đã tìm thấy
        # __DEFAULT_SCOPE__.webapp.user-page.userProfile.stats.followerCount
        # Sử dụng .get() một cách an toàn để tránh KeyError
        user_page_data = json_data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-page', {})
        user_profile = user_page_data.get('userProfile', {})
        stats = user_profile.get('stats', {})

        follower_count = stats.get('followerCount')
        heart_count = stats.get('heartCount')
        video_count = stats.get('videoCount')

        if all(x is not None for x in [follower_count, heart_count, video_count]):
            return {
                "followerCount": follower_count,
                "heartCount": heart_count,
                "videoCount": video_count
            }
        else:
            print("Không tìm thấy tất cả các số liệu thống kê (followerCount, heartCount, videoCount).")
            print(f"Dữ liệu userProfile.stats: {stats}") # In ra để kiểm tra
            return None

    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi thực hiện yêu cầu HTTP: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Lỗi khi phân tích JSON: {e}")
        print(f"Lý do chi tiết: {e.msg} tại vị trí {e.pos}")
        print(f"Nội dung JSON gây lỗi (từ vị trí lỗi, 100 ký tự): {json_content[max(0, e.pos-50):e.pos+100]}...") # In thêm context xung quanh lỗi
        return None
    except AttributeError as e:
        print(f"Lỗi khi truy cập thuộc tính (có thể không tìm thấy thẻ script hoặc nội dung): {e}")
        return None
    except Exception as e:
        print(f"Đã xảy ra lỗi không mong muốn: {e}")
        return None

if __name__ == "__main__":
    tiktok_username = "pnj_kv6_truelove" # Hoặc "pri_kv6_slayqueen" nếu bạn muốn
    
    print(f"Đang lấy dữ liệu cho người dùng: {tiktok_username}...")
    stats = get_tiktok_stats(tiktok_username)

    if stats:
        print("\nSố liệu thống kê TikTok:")
        print(f"Lượt theo dõi: {stats['followerCount']}")
        print(f"Tổng lượt thích: {stats['heartCount']}")
        print(f"Số lượng video: {stats['videoCount']}")

        try:
            with open('tiktok_stats.json', 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=4)
            print("\nĐã lưu số liệu vào tệp 'tiktok_stats.json'")
        except IOError as e:
            print(f"Lỗi khi lưu tệp JSON: {e}")
    else:
        print(f"Không thể lấy số liệu thống kê cho người dùng {tiktok_username}.")

    time.sleep(2)