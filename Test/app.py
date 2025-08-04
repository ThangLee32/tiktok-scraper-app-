from flask import Flask, render_template, request, send_file
import requests
import pandas as pd
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
ACCESS_TOKEN = 'EAASjNRkupd4BPDqLUZCZC6iZCglJ2ZBuu8pVU6m6nofRc2xNC6PJTnx1nQZC1wrnXV2pXkrzuJ7lTiNZAyNsEljDBS4gce72YqUBLAwxNtwNsT9A6C1kDO0R8flGePoYy6ZAZCoKZAhH2zkAig1VRZB85png07blHzs6ut2rDVZCZBhyZBr9amZC1p4m2hG8T6nvWDCnlW9mrQzhb0aGRddhYh92faZC9RYRNBbnALq2vqHoBSFvEgWNrkpcatJ'

def get_fanpage_data(page_id):
    url = f"https://graph.facebook.com/v23.0/{page_id}?fields=name,fan_count,about,picture.type(large),posts.limit(3){{message,created_time}}&access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        data = response.json()
        return data
    except Exception as e:
        return {"error": str(e)}

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    error = None
    if request.method == 'POST':
        page_ids = request.form['page_ids'].split(',')
        for pid in page_ids:
            pid = pid.strip()
            if pid:
                data = get_fanpage_data(pid)
                results.append(data)

        # Prepare data for chart and Excel
        names = [r.get('name') or 'Không xác định' for r in results]
        fans = [r.get('fan_count') or 0 for r in results]

        # Save chart
        plt.figure(figsize=(10, 6))
        plt.bar(names, fans, color='skyblue')
        plt.xlabel('Fanpage')
        plt.ylabel('Số người theo dõi')
        plt.title('Biểu đồ số lượng người theo dõi')
        chart_path = 'uploads/fan_chart.png'
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()

        # Save Excel
        excel_data = []
        for r in results:
            posts = r.get('posts', [])
            if isinstance(posts, dict):
                post_data = posts.get('data', [])
            else:
                post_data = posts
            bai_viet = '\n'.join([p.get('message', '') for p in post_data])
            excel_data.append({
                'Tên fanpage': r.get('name'),
                'Số người theo dõi': r.get('fan_count'),
                'Mô tả': r.get('about'),
                'Bài viết': bai_viet
            })
        df = pd.DataFrame(excel_data)
        excel_path = 'uploads/fan_data.xlsx'
        df.to_excel(excel_path, index=False)

        return render_template('index.html', results=results, chart_path=chart_path, excel_path=excel_path)

    return render_template('index.html', results=None, chart_path=None, excel_path=None)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(f'uploads/{filename}', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
