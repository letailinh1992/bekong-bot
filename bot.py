import os
import requests
import logging
from openai import OpenAI

# ============================================================
# CẤU HÌNH — điền thông tin của anh/chị vào đây
# ============================================================
TELEGRAM_TOKEN = "8481737539:AAEjqMSnqpYHtwtKrjVnJOAiKzwNmMr6Dmk"
KEY4U_API_KEY  = "sk-a1bBh1m2t5kNCT9MMAoV4k7sByc7eXtuiXkQPfNFdbSsTdPt"
KEY4U_BASE_URL = "https://api.key4u.shop/v1"             # base URL của key4u.shop
MODEL_NAME     = "gemini-2.5-flash-lite"
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Khởi tạo OpenAI client trỏ đến key4u.shop
client = OpenAI(
    api_key=KEY4U_API_KEY,
    base_url=KEY4U_BASE_URL,
)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Lưu lịch sử chat theo từng user (in-memory)
chat_history: dict[int, list] = {}

SYSTEM_PROMPT = """# VAI TRÒ
Bạn là "Bé Kong", trợ lý kế toán ảo thông minh và tận tâm của công ty kiến trúc UNPAC Design & Build. Bạn làm việc trực tiếp dưới sự điều hành của Kiến trúc sư Lê Tài Linh (Sếp Linh).

# TÍNH CÁCH & GIAO TIẾP
- Xưng hô: Gọi Lê Tài Linh là "Anh" hoặc "Sếp", xưng là "Bé Kong" hoặc "Em".
- Thái độ: Nhanh nhẹn, chính xác, bảo mật và luôn cầu thị. Sử dụng các icon liên quan đến xây dựng, tiền bạc (🏗️, 💰, 📐) để cuộc hội thoại sinh động.
- Ngôn ngữ: Tiếng Việt chuyên ngành kiến trúc/xây dựng (MDF, HDF, bản vẽ, thi công, quyết toán...).

# NHIỆM VỤ CHÍNH
1. QUẢN LÝ THU CHI:
- Khi Sếp Linh nhập nội dung tiền bạc (Ví dụ: "Chi 5tr mua gỗ HDF cho Villa Bảo Duy"), hãy bóc tách ngay lập tức thành các trường:
  + Ngày: (Mặc định là ngày hiện tại trừ khi có yêu cầu khác)
  + Nội dung: (Mô tả chi tiết)
  + Số tiền: (Chuyển về dạng số nguyên)
  + Loại: (Thu hoặc Chi)
  + Hạng mục: (Vật tư, Nhân công, Mặt bằng, Marketing, Khác)
  + Dự án: (Ví dụ: Villa Bảo Duy, Nội thất UNPAC, Dự án Bình Dương...)

2. KIỂM SOÁT DỮ LIỆU:
- Nếu tin nhắn thu chi thiếu tên "Dự án", Bé Kong phải hỏi lại: "Dòng tiền này mình áp dụng cho công trình nào vậy Sếp?"
- Luôn xác nhận lại sau khi ghi chép: "Bé Kong đã ghi sổ: Chi 5.000.000đ mua gỗ cho dự án Villa Bảo Duy rồi nhé Anh!"

3. TRÍCH XUẤT HÓA ĐƠN (OCR):
- Nếu Sếp gửi ảnh hóa đơn, hãy tự động đọc: Tên nhà cung cấp, Tổng tiền, Ngày tháng và hỏi Sếp có muốn lưu vào sổ không.

4. BÁO CÁO:
- Khi có lệnh tổng hợp, hãy trình bày dữ liệu dạng BẢNG (Markdown) để Sếp dễ theo dõi trên điện thoại.

# RÀO CẢN & QUY TẮC
- Tuyệt đối không tiết lộ số liệu tài chính cho bất kỳ ai khác ngoài Sếp Linh.
- Nếu không chắc chắn về một con số, hãy hỏi lại thay vì tự đoán.
- Luôn ưu tiên độ chính xác hơn là trả lời dài dòng."""


def get_telegram_updates(offset: int = 0) -> list:
    """Lấy updates mới từ Telegram."""
    resp = requests.get(
        f"{TELEGRAM_API}/getUpdates",
        params={"offset": offset, "timeout": 30},
        timeout=35,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def send_message(chat_id: int, text: str) -> None:
    """Gửi tin nhắn đến user."""
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )


def chat_with_gemini(user_id: int, user_message: str) -> str:
    """Gửi tin nhắn đến Gemini qua key4u.shop và trả về phản hồi."""
    # Khởi tạo lịch sử nếu chưa có
    if user_id not in chat_history:
        chat_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Thêm tin nhắn mới của user
    chat_history[user_id].append({"role": "user", "content": user_message})

    # Giữ tối đa 20 tin nhắn (tránh vượt context)
    if len(chat_history[user_id]) > 21:
        chat_history[user_id] = [chat_history[user_id][0]] + chat_history[user_id][-20:]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=chat_history[user_id],
        max_tokens=2048,
    )

    reply = response.choices[0].message.content

    # Lưu phản hồi vào lịch sử
    chat_history[user_id].append({"role": "assistant", "content": reply})

    return reply


def handle_update(update: dict) -> None:
    """Xử lý từng update từ Telegram."""
    message = update.get("message")
    if not message:
        return

    chat_id  = message["chat"]["id"]
    user_id  = message["from"]["id"]
    username = message["from"].get("first_name", "bạn")
    text     = message.get("text", "")

    if not text:
        return

    logger.info(f"[{username}] {text}")

    # Lệnh /start
    if text.startswith("/start"):
        send_message(
            chat_id,
            f"Xin chào *{username}*! 👋\n\nTôi là *Kong Bot*, trợ lý AI được hỗ trợ bởi Gemini 2.5 Flash Lite.\n\nHãy nhắn bất kỳ điều gì để bắt đầu!"
        )
        return

    # Lệnh /reset — xóa lịch sử chat
    if text.startswith("/reset"):
        chat_history.pop(user_id, None)
        send_message(chat_id, "✅ Đã xóa lịch sử chat. Bắt đầu cuộc trò chuyện mới!")
        return

    # Lệnh /help
    if text.startswith("/help"):
        send_message(
            chat_id,
            "📚 *Hướng dẫn sử dụng Kong Bot*\n\n"
            "• Nhắn bất kỳ tin nhắn nào để chat với AI\n"
            "• /reset — Xóa lịch sử, bắt đầu lại\n"
            "• /help — Xem hướng dẫn này\n\n"
            f"🤖 Model: `{MODEL_NAME}`"
        )
        return

    # Chat thường — gửi đến Gemini
    try:
        send_message(chat_id, "⏳ Đang xử lý...")
        reply = chat_with_gemini(user_id, text)
        send_message(chat_id, reply)
    except Exception as e:
        logger.error(f"Lỗi: {e}")
        send_message(chat_id, f"❌ Có lỗi xảy ra: {str(e)}\n\nVui lòng thử lại hoặc gõ /reset.")


def main() -> None:
    logger.info(f"Kong Bot đang chạy với model {MODEL_NAME}...")
    offset = 0
    while True:
        try:
            updates = get_telegram_updates(offset)
            for update in updates:
                handle_update(update)
                offset = update["update_id"] + 1
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"Lỗi polling: {e}")


if __name__ == "__main__":
    main()
