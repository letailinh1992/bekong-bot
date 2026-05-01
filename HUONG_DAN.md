# Hướng dẫn chạy Kong Bot

## Bước 1 — Điền API Key

Mở file `bot.py`, tìm dòng:
```
KEY4U_API_KEY  = "PASTE_API_KEY_CUA_ANH_CHI_VAO_DAY"
```
Thay bằng API key thật từ key4u.shop (click icon copy trên trang /token).

## Bước 2 — Cài thư viện

```bash
pip install -r requirements.txt
```

## Bước 3 — Chạy bot

```bash
python bot.py
```

## Lệnh bot hỗ trợ

| Lệnh | Chức năng |
|------|-----------|
| `/start` | Chào mừng |
| `/help` | Xem hướng dẫn |
| `/reset` | Xóa lịch sử chat |
| _(tin nhắn bất kỳ)_ | Chat với Gemini 2.5 Flash Lite |

## Thông tin kết nối

- **Bot**: @Kong_kt_bot
- **Model**: gemini-2.5-flash-lite
- **API**: https://api.key4u.shop/v1
- **Telegram Token**: 8481737539:AAEjqMSnqpYHtwtKrjVnJOAiKzwNmMr6Dmk
