# 🎯 QLNNN Offline - Skills & Vibecode Bundle

Bundle được tạo riêng cho dự án **QLNNN Offline** - Hệ thống Quản lý Người Nước Ngoài.

---

## 📦 Nội dung Bundle

### 🔧 Skills (15 skills)

#### 🐍 Python Development
| Skill | Mô tả |
|-------|-------|
| `python-pro` | Best practices Python |
| `python-patterns` | Design patterns cho Python |
| `python-testing-patterns` | Unit testing với pytest |

#### 🗄️ Database & SQL
| Skill | Mô tả |
|-------|-------|
| `database-design` | Thiết kế schema database |
| `sql-pro` | Viết SQL queries chuyên nghiệp |
| `sql-optimization-patterns` | Tối ưu hiệu suất truy vấn |
| `database-migration` | Migration dữ liệu |

#### 🔐 Security
| Skill | Mô tả |
|-------|-------|
| `auth-implementation-patterns` | Triển khai authentication |
| `secrets-management` | Quản lý credentials an toàn |

#### 📊 Data Engineering
| Skill | Mô tả |
|-------|-------|
| `data-engineer` | Xử lý dữ liệu lớn |
| `data-quality-frameworks` | Validate & kiểm tra chất lượng dữ liệu |

#### 🧪 Testing & Quality
| Skill | Mô tả |
|-------|-------|
| `testing-patterns` | Chiến lược testing |
| `debugging-strategies` | Debug hiệu quả |
| `clean-code` | Code sạch, dễ bảo trì |

#### 📝 Documentation
| Skill | Mô tả |
|-------|-------|
| `documentation-templates` | Mẫu tài liệu chuẩn |

---

### 🚀 Vibecode Templates (5 files)

| File | Mục đích | Khi nào dùng |
|------|----------|--------------|
| `DASHBOARD-v4.txt` | Xây dựng dashboard/admin panel | Rebuild UI hoàn toàn |
| `DEBUG-MASTER-v4.txt` | Quy trình debug chuyên nghiệp | Gặp bug khó |
| `QA-MASTER-v4.txt` | Kiểm tra chất lượng toàn diện | Trước khi release |
| `XRAY-MASTER-v4.txt` | Phân tích sâu codebase | Hiểu code legacy |
| `PHILOSOPHY_V4.md` | Triết lý làm việc với AI | Đọc để hiểu quy trình |

---

## 🚀 Cách cài đặt

### Bước 1: Copy vào dự án QLNNN

```powershell
# Copy toàn bộ bundle vào dự án
Copy-Item -Path "qlnnn_skills_bundle\*" -Destination "đường_dẫn_dự_án\.agent\skills\" -Recurse -Force
```

### Bước 2: Cấu trúc sau khi cài

```
qlnnn_offline/
├── .agent/
│   └── skills/
│       ├── python-pro/
│       ├── database-design/
│       ├── vibecode/
│       │   ├── DASHBOARD-v4.txt
│       │   ├── DEBUG-MASTER-v4.txt
│       │   └── ...
│       └── ...
├── app.py
└── ...
```

---

## 💡 Cách sử dụng

### 🔧 Sử dụng Skills (trong AI coding assistant)

```
Use the `python-pro` skill to review modules/search.py
```

```
Apply `database-design` and `sql-optimization-patterns` to improve DuckDB queries
```

```
Use `debugging-strategies` to fix this error: [paste error]
```

### 🚀 Sử dụng Vibecode (copy-paste vào ChatGPT/Claude)

1. Mở file trong thư mục `vibecode/`
2. Copy toàn bộ nội dung
3. Paste vào ChatGPT hoặc Claude
4. Mô tả yêu cầu của bạn

**Ví dụ với DASHBOARD-v4.txt:**
> "Tôi đang xây dựng dashboard quản lý người nước ngoài bằng Streamlit + Python. Hãy giúp tôi cải thiện UI/UX cho trang thống kê."

---

## 📋 Prompts mẫu cho QLNNN

### Sửa/Cải thiện code hiện tại
```
Use `python-pro` and `clean-code` skills to:
1. Review app.py
2. Suggest improvements for code structure
3. Identify potential bugs
```

### Tối ưu Database
```
Apply `database-design` and `sql-optimization-patterns` to:
1. Review DuckDB schema
2. Add indexes for faster search by passport
3. Optimize batch search queries
```

### Debug lỗi
```
Use `debugging-strategies` skill to analyze this error:
[paste error message]

Context: This happens in modules/search.py when doing batch search
```

### Thêm tính năng mới
```
Use `python-patterns` and `data-quality-frameworks` to:
Add data validation for Excel import in modules/import_data.py
Requirements:
- Validate date format (DD/MM/YYYY)
- Check required fields: passport, name, nationality
- Report errors without stopping import
```

### Rebuild module hoàn toàn
```
[Copy DASHBOARD-v4.txt từ vibecode/]

Tôi cần rebuild trang thống kê (pages/2_📈_Thong_ke.py) với:
- Charts đẹp hơn (Plotly)
- Filters linh hoạt
- Export to Excel
- Dark mode support
```

---

## ⚡ Quick Reference

| Việc cần làm | Dùng gì |
|--------------|---------|
| Review/sửa code Python | `python-pro` + `clean-code` |
| Tối ưu queries | `sql-optimization-patterns` |
| Fix bugs | `debugging-strategies` |
| Thêm tests | `python-testing-patterns` |
| Cải thiện auth | `auth-implementation-patterns` |
| Validate data import | `data-quality-frameworks` |
| Phân tích codebase | `XRAY-MASTER-v4.txt` |
| Debug phức tạp | `DEBUG-MASTER-v4.txt` |
| Test trước release | `QA-MASTER-v4.txt` |
| Xây mới hoàn toàn | `DASHBOARD-v4.txt` |

---

*Bundle created: 2026-01-30*
*Vibecode Kit v4.0 + Antigravity Skills*
