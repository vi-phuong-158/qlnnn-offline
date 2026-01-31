#!/usr/bin/env python3
"""
PDF/JSF to Google Sheets Converter - Phiên bản chống timeout
- Retry mechanism với exponential backoff
- Chia file lớn thành nhiều parts
- Progress tracking và error handling
- Excel backup nếu Sheets upload thất bại
"""

import os
import sys
import subprocess
import shutil
import time
import socket
import pandas as pd
import pdfplumber
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ===== CẤU HÌNH =====
FOLDER_ID = '1dP-vSFjB0zvrJeKdJWcOtU4OLMPhc-KW'  # Folder chính
FOLDER_ID_2 = '1HsZT9FZ9S1kCE4ko6SgfuZI40Og34IKb'  # Folder thứ 2 (backup)
SERVICE_ACCOUNT_EMAIL = 'xlsx-to-gsheet@ocr-project-16867.iam.gserviceaccount.com'
SCOPES = ['https://www.googleapis.com/auth/drive']

# Đường dẫn
BASE_DIR = os.path.dirname(os.path.realpath(__file__)) if '__file__' in globals() else os.getcwd()
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'xlsx-to-sheets-sa.json')
INPUT_DIR = os.path.join(BASE_DIR, 'Input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'Output')
DONE_DIR = os.path.join(BASE_DIR, 'Done')

def install_missing_packages():
    """Tự động cài đặt thư viện thiếu."""
    required_packages = {
        'pandas': 'pandas',
        'pdfplumber': 'pdfplumber', 
        'google.oauth2': 'google-api-python-client google-auth'
    }
    
    missing_packages = []
    for module_name, pip_name in required_packages.items():
        try:
            __import__(module_name.split('.')[0])
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("📦 Đang cài đặt thư viện thiếu...")
        for package in missing_packages:
            print(f"🔄 Cài đặt {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + package.split())
                print(f"✅ {package} đã cài đặt xong")
            except subprocess.CalledProcessError:
                print(f"❌ Lỗi cài đặt {package}")
                input("Nhấn Enter để thoát...")
                sys.exit(1)
        print("✅ Tất cả thư viện đã sẵn sàng!\n")

def check_and_create_folders():
    """Tạo thư mục cần thiết."""
    for directory in [INPUT_DIR, OUTPUT_DIR, DONE_DIR]:
        os.makedirs(directory, exist_ok=True)

def check_service_account_file():
    """Kiểm tra file JSON Service Account."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ Không tìm thấy file: {SERVICE_ACCOUNT_FILE}")
        print("📝 Vui lòng đặt file 'xlsx-to-sheets-sa.json' vào cùng thư mục với script")
        input("Nhấn Enter để thoát...")
        sys.exit(1)

def test_google_drive_access():
    """Test và khởi tạo kết nối Google Drive với timeout settings."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        
        # Tăng timeout cho socket connections
        socket.setdefaulttimeout(300)  # 5 phút timeout
        
        drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        # Test quyền truy cập folder với timeout
        try:
            print("🔄 Đang kiểm tra quyền truy cập folder...")
            folder_info = drive_service.files().get(
                fileId=FOLDER_ID,
                fields='id,name'
            ).execute()
            
            folder_name = folder_info.get('name', 'Không có tên')
            print(f"✅ Kết nối Google Drive thành công!")
            print(f"📁 Folder chính: '{folder_name}'")
            
            # Kiểm tra folder thứ 2
            try:
                folder_info_2 = drive_service.files().get(
                    fileId=FOLDER_ID_2,
                    fields='id,name'
                ).execute()
                folder_name_2 = folder_info_2.get('name', 'Không có tên')
                print(f"📁 Folder thứ 2: '{folder_name_2}'")
            except Exception as e2:
                error_str_2 = str(e2).lower()
                if "not found" in error_str_2 or "permission" in error_str_2:
                    print(f"⚠️ Cảnh báo: Không có quyền truy cập folder thứ 2")
                    print(f"💡 Cần share folder cho: {SERVICE_ACCOUNT_EMAIL}")
                    print(f"🌐 Folder URL: https://drive.google.com/drive/folders/{FOLDER_ID_2}")
                    print(f"⚡ Quyền cần: Editor")
                else:
                    print(f"⚠️ Lỗi kiểm tra folder thứ 2: {e2}")
            
            return drive_service
            
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "permission" in error_str:
                print(f"❌ Không có quyền truy cập folder!")
                print(f"🔧 Cần share folder cho: {SERVICE_ACCOUNT_EMAIL}")
                print(f"🌐 Folder URL: https://drive.google.com/drive/folders/{FOLDER_ID}")
                print(f"⚡ Quyền cần: Editor")
                input("Share xong rồi nhấn Enter để thử lại...")
                return test_google_drive_access()  # Thử lại
            else:
                print(f"❌ Lỗi kiểm tra folder: {e}")
                raise e
            
    except Exception as e:
        print(f"❌ Lỗi kết nối Google Drive: {e}")
        print("💡 Gợi ý:")
        print("   - Kiểm tra file JSON Service Account")
        print("   - Kiểm tra kết nối internet")
        print("   - Thử chạy lại sau vài phút")
        input("Nhấn Enter để thoát...")
        sys.exit(1)

def extract_data_to_excel(file_path):
    """Trích xuất dữ liệu từ PDF/JSF thành Excel."""
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}_extracted.xlsx")
    all_dfs = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                print(f"⚠️ File {os.path.basename(file_path)} không có dữ liệu")
                return None
                
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    all_dfs.append(df)
    except Exception as e:
        print(f"❌ Lỗi đọc file {os.path.basename(file_path)}: {e}")
        return None

    if not all_dfs:
        print(f"⚠️ Không tìm thấy bảng trong {os.path.basename(file_path)}")
        return None

    # Ghép tất cả bảng
    df_all = pd.concat(all_dfs, ignore_index=True)

    # Làm sạch cột STT
    if 'STT' in df_all.columns:
        df_all = df_all[pd.to_numeric(df_all['STT'], errors='coerce').notna()]

    # Chuẩn hóa ngày tháng
    date_columns = ['Ngày sinh', 'Ngày đến', 'Ngày đi']
    for col in date_columns:
        if col in df_all.columns:
            print(f"🔄 Chuẩn hóa: {col}")
            datetime_col = pd.to_datetime(df_all[col], dayfirst=True, errors='coerce')
            df_all[col] = datetime_col.apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')

    # Lưu Excel
    df_all.to_excel(out_path, index=False)
    print(f"✅ Tạo Excel: {os.path.basename(out_path)} ({len(df_all)} dòng)")
    return out_path

def split_large_excel_file(excel_path, max_rows_per_file=3000):
    """Chia file Excel lớn thành nhiều file nhỏ hơn."""
    try:
        df = pd.read_excel(excel_path)
        total_rows = len(df)
        
        if total_rows <= max_rows_per_file:
            return [excel_path]  # File đã đủ nhỏ
        
        print(f"📊 File có {total_rows} dòng, chia thành các file {max_rows_per_file} dòng")
        
        base_name = os.path.splitext(os.path.basename(excel_path))[0]
        output_dir = os.path.dirname(excel_path)
        split_files = []
        
        for i in range(0, total_rows, max_rows_per_file):
            chunk = df.iloc[i:i + max_rows_per_file]
            part_num = (i // max_rows_per_file) + 1
            split_filename = f"{base_name}_PART_{part_num:02d}.xlsx"
            split_path = os.path.join(output_dir, split_filename)
            
            chunk.to_excel(split_path, index=False)
            split_files.append(split_path)
            print(f"✅ Part {part_num}: {len(chunk)} dòng")
        
        print(f"🔪 Đã chia thành {len(split_files)} file")
        return split_files
        
    except Exception as e:
        print(f"❌ Lỗi chia file: {e}")
        return [excel_path]  # Trả về file gốc nếu lỗi

def check_existing_file(drive_service, file_name, folder_id):
    """Kiểm tra xem file đã tồn tại trong folder chưa."""
    try:
        query = f"name='{file_name}' and parents in '{folder_id}' and trashed=false"
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, webViewLink, mimeType, createdTime)"
        ).execute()
        
        files = results.get('files', [])
        if files:
            file_info = files[0]  # Lấy file đầu tiên (mới nhất)
            print(f"✅ File đã tồn tại: {file_info.get('name')}")
            print(f"🔗 Link: {file_info.get('webViewLink')}")
            print(f"📅 Tạo lúc: {file_info.get('createdTime')}")
            return file_info
        return None
    except Exception as e:
        print(f"⚠️ Lỗi kiểm tra file tồn tại: {e}")
        return None

def copy_file_to_folder_2(drive_service, file_id, file_name):
    """Copy file Google Sheets vào folder thứ 2."""
    try:
        # Kiểm tra quyền truy cập folder 2 trước
        try:
            drive_service.files().get(fileId=FOLDER_ID_2, fields='id').execute()
        except Exception as perm_check:
            error_str = str(perm_check).lower()
            if "not found" in error_str or "permission" in error_str:
                print(f"⚠️ Không có quyền truy cập folder thứ 2")
                print(f"💡 Vui lòng share folder cho: {SERVICE_ACCOUNT_EMAIL}")
                print(f"🌐 Folder URL: https://drive.google.com/drive/folders/{FOLDER_ID_2}")
                print(f"⚡ Quyền cần: Editor (Chỉnh sửa)")
                print(f"⏭️  Bỏ qua copy vào folder 2, tiếp tục xử lý file khác...")
                return None
        
        # Kiểm tra file đã tồn tại trong folder 2 chưa
        existing_file = check_existing_file(drive_service, file_name, FOLDER_ID_2)
        if existing_file:
            print(f"✅ File '{file_name}' đã có trong folder 2 - bỏ qua copy")
            return existing_file
        
        print(f"📋 Đang copy '{file_name}' vào folder thứ 2...")
        
        # Copy file vào folder 2
        copied_file = drive_service.files().copy(
            fileId=file_id,
            body={
                'name': file_name,
                'parents': [FOLDER_ID_2]
            },
            fields='id, name, webViewLink'
        ).execute()
        
        print(f"✅ Đã copy vào folder 2: {copied_file.get('name')}")
        print(f"🔗 Link: {copied_file.get('webViewLink')}")
        return copied_file
        
    except Exception as e:
        error_str = str(e).lower()
        if "not found" in error_str or "permission" in error_str:
            print(f"⚠️ Không có quyền copy vào folder 2 hoặc folder không tồn tại")
            print(f"💡 Vui lòng share folder cho: {SERVICE_ACCOUNT_EMAIL}")
            print(f"🌐 Folder URL: https://drive.google.com/drive/folders/{FOLDER_ID_2}")
            print(f"⚡ Quyền cần: Editor (Chỉnh sửa)")
            print(f"⏭️  Bỏ qua copy vào folder 2, tiếp tục xử lý file khác...")
        else:
            print(f"❌ Lỗi copy file vào folder 2: {e}")
            print(f"⏭️  Bỏ qua copy vào folder 2, tiếp tục xử lý file khác...")
        return None

def upload_to_google_sheets(drive_service, excel_path, max_retries=3):
    """Upload Excel lên Google Drive và chuyển thành Sheets với retry."""
    filename = os.path.basename(excel_path)
    sheet_name = filename.replace('_extracted.xlsx', '').replace('.xlsx', '')
    
    # Kiểm tra file đã tồn tại chưa
    print(f"🔍 Kiểm tra file '{sheet_name}' đã tồn tại...")
    existing_file = check_existing_file(drive_service, sheet_name, FOLDER_ID)
    if existing_file:
        print("✅ File đã có sẵn - bỏ qua upload")
        # Vẫn copy vào folder thứ 2 nếu chưa có
        file_id = existing_file.get('id')
        if file_id:
            copy_file_to_folder_2(drive_service, file_id, sheet_name)
        return existing_file
    
    # Kiểm tra kích thước file
    file_size = os.path.getsize(excel_path) / (1024 * 1024)  # MB
    print(f"📊 File: {filename} ({file_size:.1f} MB)")
    
    if file_size > 100:
        print("⚠️ File lớn hơn 100MB, có thể mất nhiều thời gian...")
    
    file_metadata = {
        'name': sheet_name,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [FOLDER_ID]
    }
    
    # Cấu hình upload với chunk size tối ưu
    chunk_size = 1024 * 1024 * 5  # 5MB chunks
    if file_size > 50:
        chunk_size = 1024 * 1024 * 2  # 2MB chunks cho file lớn
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Upload lần {attempt + 1}/{max_retries}...")
            
            media = MediaFileUpload(
                excel_path,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                resumable=True,
                chunksize=chunk_size
            )
            
            # Tạo request với timeout dài hơn
            request = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            )
            
            # Upload với progress tracking
            response = None
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        print(f"📈 Tiến trình: {progress}%", end='\r')
                except Exception as chunk_error:
                    if "timeout" in str(chunk_error).lower():
                        print(f"\n⏰ Chunk timeout - tiếp tục...")
                        continue
                    else:
                        raise chunk_error
            
            print(f"\n✅ Upload thành công: {sheet_name}")
            print(f"🔗 Link: {response.get('webViewLink')}")
            
            # Copy file vào folder thứ 2
            file_id = response.get('id')
            if file_id:
                copy_file_to_folder_2(drive_service, file_id, sheet_name)
            
            return response
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Trường hợp đặc biệt: timeout nhưng có thể đã upload thành công
            if "timeout" in error_str or "deadline exceeded" in error_str:
                print(f"\n⏰ Timeout lần {attempt + 1} - Kiểm tra file đã upload chưa...")
                
                # Đợi một chút rồi kiểm tra
                time.sleep(5)
                existing_file = check_existing_file(drive_service, sheet_name, FOLDER_ID)
                if existing_file:
                    print("🎉 File đã upload thành công dù có timeout!")
                    # Copy file vào folder thứ 2
                    file_id = existing_file.get('id')
                    if file_id:
                        copy_file_to_folder_2(drive_service, file_id, sheet_name)
                    return existing_file
                
                # Nếu chưa có file, thử lại
                wait_time = 10 * (2 ** attempt)  # Exponential backoff
                print(f"❌ File chưa có - Đợi {wait_time}s rồi thử lại...")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Upload thất bại sau {max_retries} lần thử")
                    # Kiểm tra lần cuối xem có file không
                    final_check = check_existing_file(drive_service, sheet_name, FOLDER_ID)
                    if final_check:
                        print("🎉 Tìm thấy file - Upload đã thành công!")
                        # Copy file vào folder thứ 2
                        file_id = final_check.get('id')
                        if file_id:
                            copy_file_to_folder_2(drive_service, file_id, sheet_name)
                        return final_check
                    return None
            elif "quota" in error_str:
                print(f"❌ Vượt quá quota Google Drive API")
                print("💡 Đợi 1 giờ rồi thử lại")
                return None
            else:
                print(f"❌ Lỗi upload: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    return None
    
    return None

def upload_with_smart_handling(drive_service, excel_path):
    """Upload thông minh với tùy chọn chia file nếu cần."""
    file_size_mb = os.path.getsize(excel_path) / (1024 * 1024)
    df = pd.read_excel(excel_path)
    row_count = len(df)
    
    print(f"📊 File info: {file_size_mb:.1f} MB, {row_count:,} dòng")
    
    # Quyết định strategy upload
    if file_size_mb > 80 or row_count > 20000:
        print("⚠️ File lớn - có thể gây timeout")
        print("💡 Chiến lược:")
        print("   1. Thử upload nguyên file (rủi ro timeout)")
        print("   2. Chia nhỏ file rồi upload (an toàn hơn)")
        
        while True:
            choice = input("Chọn (1/2) [Khuyến nghị: 2]: ").strip()
            if choice in ['1', '2', '']:
                break
            print("Vui lòng chọn 1 hoặc 2")
        
        if choice == '1':
            # Thử upload nguyên file
            result = upload_to_google_sheets(drive_service, excel_path, max_retries=3)
            if result:
                return [result]
            else:
                print("❌ Upload nguyên file thất bại")
                return []
        else:
            # Chia file và upload
            split_files = split_large_excel_file(excel_path, max_rows_per_file=3000)
            uploaded_files = []
            
            for i, split_file in enumerate(split_files, 1):
                print(f"\n📤 Upload part {i}/{len(split_files)}")
                uploaded = upload_to_google_sheets(drive_service, split_file, max_retries=2)
                if uploaded:
                    uploaded_files.append(uploaded)
                else:
                    print(f"❌ Part {i} thất bại")
                    # Thử backup Excel cho part này
                    try:
                        backup_name = f"{os.path.splitext(os.path.basename(split_file))[0]}_EXCEL_BACKUP.xlsx"
                        backup_metadata = {'name': backup_name, 'parents': [FOLDER_ID]}
                        backup_media = MediaFileUpload(split_file)
                        backup_result = drive_service.files().create(
                            body=backup_metadata, media_body=backup_media, fields='webViewLink'
                        ).execute()
                        print(f"✅ Backup Excel: {backup_result.get('webViewLink')}")
                        uploaded_files.append(backup_result)
                    except:
                        print(f"❌ Backup cũng thất bại")
            
            return uploaded_files
    else:
        # File nhỏ, upload bình thường
        result = upload_to_google_sheets(drive_service, excel_path, max_retries=3)
        return [result] if result else []

def list_files_in_folder(drive_service, folder_id, max_files=10):
    """Liệt kê các file mới nhất trong folder."""
    try:
        query = f"parents in '{folder_id}' and trashed=false"
        results = drive_service.files().list(
            q=query,
            orderBy='createdTime desc',
            pageSize=max_files,
            fields="files(id, name, webViewLink, mimeType, createdTime, size)"
        ).execute()
        
        files = results.get('files', [])
        if files:
            print(f"\n📁 {len(files)} file mới nhất trong folder:")
            for i, file_info in enumerate(files, 1):
                name = file_info.get('name', 'Không có tên')
                link = file_info.get('webViewLink', 'Không có link')
                created = file_info.get('createdTime', '')
                if created:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created = dt.strftime('%d/%m/%Y %H:%M')
                    except:
                        created = created[:16]
                
                print(f"   {i}. {name}")
                print(f"      🔗 {link}")
                print(f"      📅 {created}")
                print()
        else:
            print("📁 Folder trống")
            
    except Exception as e:
        print(f"⚠️ Lỗi list file: {e}")

def main():
    """Hàm chính."""
    print("🚀 PDF/JSF TO GOOGLE SHEETS CONVERTER v2.1")
    print("   🔧 Chống timeout + Kiểm tra file tồn tại")
    print("=" * 55)
    
    # 1. Cài đặt thư viện thiếu
    install_missing_packages()
    
    # 2. Tạo thư mục
    check_and_create_folders()
    
    # 3. Kiểm tra file JSON
    check_service_account_file()
    
    # 4. Kết nối Google Drive
    drive_service = test_google_drive_access()
    
    # 5. Tìm file cần xử lý
    files_to_process = [
        f for f in os.listdir(INPUT_DIR) 
        if f.lower().endswith(('.pdf', '.jsf')) and not f.startswith('~$')
    ]
    
    if not files_to_process:
        print("📁 Thư mục Input trống!")
        print(f"📂 Đặt file PDF/JSF vào: {INPUT_DIR}")
        input("Nhấn Enter để mở thư mục Input...")
        os.startfile(INPUT_DIR)
        input("Đặt file xong rồi nhấn Enter để tiếp tục...")
        
        # Tìm lại file
        files_to_process = [
            f for f in os.listdir(INPUT_DIR) 
            if f.lower().endswith(('.pdf', '.jsf')) and not f.startswith('~$')
        ]
        if not files_to_process:
            print("❌ Vẫn không có file!")
            input("Nhấn Enter để thoát...")
            return
    
    print(f"🔎 Tìm thấy {len(files_to_process)} file:")
    for i, fn in enumerate(files_to_process, 1):
        print(f"   {i}. {fn}")
    print()
    
    # 6. Xử lý từng file
    success_count = 0
    total_uploaded = 0
    
    for i, filename in enumerate(files_to_process, 1):
        print(f"\n▶️ [{i}/{len(files_to_process)}] Xử lý: {filename}")
        file_path = os.path.join(INPUT_DIR, filename)
        
        # Trích xuất thành Excel
        excel_path = extract_data_to_excel(file_path)
        if not excel_path:
            print(f"❌ Không thể trích xuất dữ liệu từ {filename}")
            # Vẫn di chuyển file lỗi vào Done để không xử lý lại
            try:
                shutil.move(file_path, os.path.join(DONE_DIR, filename))
                print(f"🗂️ Đã di chuyển file lỗi '{filename}' vào Done")
            except Exception as e:
                print(f"⚠️ Lỗi di chuyển file lỗi: {e}")
            continue
        
        # Upload thông minh
        uploaded_files = upload_with_smart_handling(drive_service, excel_path)
        
        # DI CHUYỂN FILE ĐÃ XỬ LÝ VÀO DONE (LUÔN LUÔN)
        try:
            # Di chuyển file gốc từ Input vào Done
            shutil.move(file_path, os.path.join(DONE_DIR, filename))
            print(f"✅ Di chuyển '{filename}' vào Done")
            
            # Di chuyển file Excel từ Output vào Done  
            shutil.move(excel_path, os.path.join(DONE_DIR, os.path.basename(excel_path)))
            print(f"✅ Di chuyển Excel vào Done")
            
            success_count += 1
            
            if uploaded_files:
                total_uploaded += len(uploaded_files)
                print(f"🎉 Hoàn thành: {filename} → {len(uploaded_files)} file(s) trên Drive")
            else:
                print(f"⚠️ Upload thất bại nhưng file đã được di chuyển vào Done")
                
        except Exception as e:
            print(f"❌ Lỗi di chuyển file đã xử lý: {e}")
            print(f"⚠️ File có thể vẫn nằm trong Input: {filename}")
            # Không tăng success_count nếu không di chuyển được
    
    # 7. Kết quả
    print("\n" + "=" * 55)
    print(f"🎉 KẾT QUẢ:")
    print(f"   📄 Xử lý thành công: {success_count}/{len(files_to_process)} file")
    print(f"   📊 Tổng file upload: {total_uploaded}")
    print(f"   📁 Folder: https://drive.google.com/drive/folders/{FOLDER_ID}")
    
    # Hiển thị danh sách file mới nhất
    if total_uploaded > 0:
        list_files_in_folder(drive_service, FOLDER_ID, max_files=10)
    
    print("=" * 55)
    input("Nhấn Enter để thoát...")

if __name__ == '__main__':
    main()