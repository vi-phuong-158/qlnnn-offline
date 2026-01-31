# QLNNN Offline - Hướng dẫn cài đặt và sử dụng

## Giới thiệu

Đây là phiên bản **offline hoàn toàn** của hệ thống tra cứu & quản lý người nước ngoài (QLNNN), được port từ nền tảng Google (BigQuery + Google Apps Script) sang:

- **Python** - Backend
- **Streamlit** - Giao diện web
- **DuckDB** - Database (thay thế BigQuery)

## Yêu cầu hệ thống

- Python 3.9+
- Windows/macOS/Linux
- RAM: 4GB+ (khuyến nghị 8GB cho dữ liệu lớn)
- Ổ cứng: 500MB cho ứng dụng + dung lượng dữ liệu

## Cài đặt

### 1. Clone/Copy thư mục

```bash
cd "c:\Users\admin\OneDrive\Vi Phuong\Project GAS\Bigquerry\qlnnn_offline"
```

### 2. Tạo virtual environment (khuyến nghị)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

## Migration dữ liệu từ BigQuery

### Bước 1: Export từ BigQuery

1. Mở Google Cloud Console
2. Vào BigQuery Console
3. Chạy query để export mỗi bảng:

```sql
-- Export sang CSV
EXPORT DATA OPTIONS(
  uri='gs://your-bucket/raw_immigration_*.csv',
  format='CSV',
  overwrite=true,
  header=true
) AS
SELECT * FROM `qlnnn_warehouse.raw_immigration`;
```

Hoặc sử dụng script Python (cần service account):

```bash
cd scripts
python export_bigquery.py
```

### Bước 2: Import vào DuckDB

1. Copy thư mục `bigquery_export` vào `data/`
2. Chạy script import:

```bash
cd scripts
python import_from_export.py
```

## Khởi động ứng dụng

```bash
streamlit run Trang_chu.py
```

Mở trình duyệt và truy cập: `http://localhost:8501`

## Tài khoản mặc định

- **Username**: admin
- **Password**: admin123

⚠️ **Quan trọng**: Đổi mật khẩu ngay sau khi đăng nhập lần đầu!

## Cấu trúc thư mục

```
qlnnn_offline/
├── Trang_chu.py           # Entry point (was app.py)
├── config.py              # Cấu hình
├── requirements.txt       # Dependencies
│
├── database/              # Database layer
│   ├── connection.py      # DuckDB connection
│   └── models.py          # Schema & models
│
├── modules/               # Business logic
│   ├── search.py          # Tra cứu
│   ├── statistics.py      # Thống kê
│   ├── import_data.py     # Import
│   └── export_data.py     # Export Excel
│
├── utils/                 # Utilities
│   ├── date_utils.py      # Xử lý ngày tháng
│   ├── text_utils.py      # Xử lý text
│   └── security.py        # Mã hóa, auth
│
├── pages/                 # Streamlit pages
│   ├── 1_📊_Tra_cuu.py
│   ├── 2_📈_Thong_ke.py
│   ├── 3_📥_Nhap_lieu.py
│   └── 4_⚙️_Cai_dat.py
│
├── scripts/               # Utility scripts
│   ├── export_bigquery.py
│   └── import_from_export.py
│
└── data/                  # Data directory
    └── qlnnn.db           # DuckDB database
```

## Tính năng

### ✅ Đã implement

- [x] Tra cứu đơn (theo hộ chiếu/họ tên)
- [x] Tra cứu hàng loạt (batch search)
- [x] Thống kê theo thời gian, châu lục, mục đích
- [x] Văn bản tường thuật
- [x] Export Excel
- [x] Import từ Excel/CSV
- [x] Xác thực username/password
- [x] Phân quyền Admin/Commune

### 🔄 Khác biệt so với phiên bản Google

| Tính năng | Google Version | Offline Version |
|-----------|---------------|-----------------|
| Database | BigQuery | DuckDB |
| Auth | PIN 9 số | Username/Password |
| Rate Limit | Google quotas | Không giới hạn |
| Hosting | Google Cloud | Local machine |
| Internet | Bắt buộc | Không cần |

## Troubleshooting

### Lỗi "ModuleNotFoundError"

```bash
pip install -r requirements.txt
```

### Lỗi database

```bash
# Xóa database cũ và tạo mới
del data\qlnnn.db
python -c "from database.models import init_database; init_database()"
```

### Lỗi encoding khi import

Đảm bảo file CSV được save với encoding UTF-8:
1. Mở file với Notepad++
2. Encoding > Convert to UTF-8
3. Save

## Liên hệ

Tác giả: Vi Ngọc Phương
