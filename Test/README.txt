Ứng dụng Flask truy xuất dữ liệu từ nhiều fanpage Facebook

Hướng dẫn sử dụng:
1. Cài đặt các thư viện cần thiết:
   pip install flask pandas matplotlib requests openpyxl

2. Thay thế ACCESS_TOKEN trong app.py bằng token thật của bạn từ Facebook Graph API.

3. Chạy ứng dụng:
   python app.py

4. Truy cập trình duyệt tại địa chỉ:
   http://127.0.0.1:5000

5. Nhập danh sách fanpage ID hoặc upload file CSV để truy xuất dữ liệu.

6. Tải file Excel kết quả hoặc xem biểu đồ số lượng người theo dõi.

Thư mục uploads sẽ chứa file Excel và biểu đồ PNG.
