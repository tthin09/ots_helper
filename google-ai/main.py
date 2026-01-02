import os
import time
from google import genai
from google.genai import types
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CẤU HÌNH (SETUP)
# ==========================================
# Khởi tạo client với API Key
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Tên thư mục chứa tài liệu
DOCS_FOLDER = "../output"

# System Prompt (Yêu cầu của bạn)
SYSTEM_INSTRUCTION = """
You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
"""

# ==========================================
# HÀM XỬ LÝ FILE (FILE MANAGEMENT)
# ==========================================
def get_or_upload_file(local_path):
    """
    Upload file lên Google Server với MIME type phù hợp
    """
    local_path = Path(local_path)
    print(f"🔍 Uploading: {local_path.name}...", end=" ")

    # Xác định MIME type dựa trên phần mở rộng
    mime_types = {
        '.md': 'text/markdown',
        '.txt': 'text/plain',
        '.pdf': 'application/pdf',
        '.csv': 'text/csv'
    }
    
    mime_type = mime_types.get(local_path.suffix.lower(), 'text/plain')

    try:
        # Upload file với client mới
        with open(local_path, 'rb') as f:
            uploaded_file = client.files.upload(
                file=f,
                config=types.UploadFileConfig(
                    mime_type=mime_type,
                    display_name=local_path.name
                )
            )
        
        # Đợi file xử lý xong - state là string
        while uploaded_file.state == "PROCESSING":
            time.sleep(1)
            uploaded_file = client.files.get(name=uploaded_file.name)
            
        if uploaded_file.state == "FAILED":
            raise ValueError(f"File processing failed")
            
        print(f"✅ Upload xong!")
        return uploaded_file
    except Exception as e:
        print(f"❌ Lỗi upload: {e}")
        raise

def load_knowledge_base(folder):
    """Quét thư mục và chuẩn bị danh sách file cho Assistant"""
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"⚠️ Thư mục '{folder}' chưa tồn tại. Đã tạo mới. Hãy bỏ file vào đó!")
        return []

    knowledge_base = []
    # Hỗ trợ các định dạng file text phổ biến
    supported_extensions = ['*.md', '*.txt', '*.pdf', '*.csv']
    
    files_found = []
    for ext in supported_extensions:
        files_found.extend(Path(folder).glob(ext))
        
    if not files_found:
        print(f"⚠️ Không tìm thấy file nào trong '{folder}'.")
        return []

    print(f"🚀 Tìm thấy {len(files_found)} files. Bắt đầu xử lý...")
    
    for path in files_found:
        file_ref = get_or_upload_file(path)
        knowledge_base.append(file_ref)
        
    return knowledge_base

# ==========================================
# MAIN PROGRAM
# ==========================================
def main():
    # 1. Chuẩn bị dữ liệu
    print("--- BƯỚC 1: CHUẨN BỊ DỮ LIỆU ---")
    knowledge_docs = load_knowledge_base(DOCS_FOLDER)

    if not knowledge_docs:
        print("❌ Dừng chương trình vì không có tài liệu.")
        return

    # 2. Tạo nội dung cho context
    print("\n--- BƯỚC 2: KHỞI TẠO OPTIBOT ---")
    
    # Chuẩn bị parts cho tin nhắn đầu tiên - sử dụng Part constructor
    initial_parts = []
    for doc in knowledge_docs:
        initial_parts.append(
            types.Part(
                file_data=types.FileData(
                    file_uri=doc.uri,
                    mime_type=doc.mime_type
                )
            )
        )
    initial_parts.append(types.Part(text="Hi, I am ready to help."))

    print("\n🤖 OptiBot is online! (Gõ 'quit' để thoát)")
    print("-" * 50)

    # 3. Bắt đầu hội thoại với context
    chat_history = [
        types.Content(role="user", parts=initial_parts),
        types.Content(
            role="model",
            parts=[types.Part(text="Understood. I have read the documents and I am OptiBot, ready to assist.")]
        )
    ]

    # 4. Vòng lặp chat
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                print("👋 Tạm biệt!")
                break
            
            if not user_input.strip():
                continue
            
            # Thêm tin nhắn người dùng vào history
            chat_history.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=user_input)]
                )
            )
            
            # Gửi request với streaming
            response = client.models.generate_content_stream(
                model='gemini-1.5-flash',
                contents=chat_history,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.7
                )
            )
            
            print("OptiBot: ", end="", flush=True)
            full_response = ""
            
            for chunk in response:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_response += chunk.text
            
            print()  # New line after response
            
            # Thêm response vào history
            if full_response:
                chat_history.append(
                    types.Content(
                        role="model",
                        parts=[types.Part(text=full_response)]
                    )
                )
            
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()
            print("-" * 50)

if __name__ == "__main__":
    main()