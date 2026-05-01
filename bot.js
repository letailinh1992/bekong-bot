const https = require("https");

// ============================================================
const TELEGRAM_TOKEN = "8481737539:AAEjqMSnqpYHtwtKrjVnJOAiKzwNmMr6Dmk";
const KEY4U_API_KEY  = "sk-a1bBh1m2t5kNCT9MMAoV4k7sByc7eXtuiXkQPfNFdbSsTdPt";
const KEY4U_HOST     = "api.key4u.shop";
const MODEL_NAME     = "gemini-2.5-flash-lite";
// ============================================================

const SYSTEM_PROMPT = `# VAI TRÒ
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
- Luôn ưu tiên độ chính xác hơn là trả lời dài dòng.`;

const chatHistory = {};
const processing  = new Set(); // chống xử lý trùng lặp

function apiCall(host, path, data, extraHeaders = {}) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(data);
    const req = https.request(
      {
        host,
        path,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
          ...extraHeaders,
        },
      },
      (res) => {
        let raw = "";
        res.on("data", (c) => (raw += c));
        res.on("end", () => {
          try { resolve(JSON.parse(raw)); } catch { resolve(raw); }
        });
      }
    );
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

function getUpdates(offset) {
  return new Promise((resolve, reject) => {
    https.get(
      `https://api.telegram.org/bot${TELEGRAM_TOKEN}/getUpdates?offset=${offset}&timeout=30`,
      (res) => {
        let raw = "";
        res.on("data", (c) => (raw += c));
        res.on("end", () => {
          try { resolve(JSON.parse(raw).result || []); } catch { resolve([]); }
        });
      }
    ).on("error", reject);
  });
}

async function sendMessage(chatId, text) {
  await apiCall("api.telegram.org", `/bot${TELEGRAM_TOKEN}/sendMessage`, {
    chat_id: chatId,
    text,
    parse_mode: "Markdown",
  });
}

async function chatWithAI(userId, userMessage) {
  if (!chatHistory[userId]) {
    chatHistory[userId] = [{ role: "system", content: SYSTEM_PROMPT }];
  }
  chatHistory[userId].push({ role: "user", content: userMessage });
  if (chatHistory[userId].length > 21) {
    chatHistory[userId] = [chatHistory[userId][0], ...chatHistory[userId].slice(-20)];
  }

  const json = await apiCall(
    KEY4U_HOST,
    "/v1/chat/completions",
    { model: MODEL_NAME, messages: chatHistory[userId], max_tokens: 2048 },
    { Authorization: `Bearer ${KEY4U_API_KEY}` }
  );

  const reply = json.choices?.[0]?.message?.content || JSON.stringify(json);
  chatHistory[userId].push({ role: "assistant", content: reply });
  return reply;
}

async function handleUpdate(update) {
  const msg = update.message;
  if (!msg || !msg.text) return;

  const updateId = update.update_id;
  if (processing.has(updateId)) return; // chặn xử lý trùng
  processing.add(updateId);

  const chatId = msg.chat.id;
  const userId = msg.from.id;
  const name   = msg.from.first_name || "Sếp";
  const text   = msg.text;

  console.log(`[${name}] ${text}`);

  if (text.startsWith("/start")) {
    return sendMessage(chatId, `Chào *${name}*! 🏗️\n\nEm là *Bé Kong*, kế toán ảo của UNPAC Design & Build.\n\nAnh cứ nhắn thu chi, em ghi sổ ngay! 💰`);
  }
  if (text.startsWith("/reset")) {
    delete chatHistory[userId];
    return sendMessage(chatId, "✅ Đã xóa lịch sử. Bắt đầu sổ sách mới nhé Anh!");
  }
  if (text.startsWith("/help")) {
    return sendMessage(chatId,
      "📐 *Hướng dẫn dùng Bé Kong*\n\n" +
      "• Nhắn thu/chi bất kỳ → Em ghi sổ ngay\n" +
      "• Gửi ảnh hóa đơn → Em đọc và trích xuất\n" +
      "• /reset — Xóa lịch sử chat\n" +
      "• /help — Xem hướng dẫn\n\n" +
      `🤖 Model: \`${MODEL_NAME}\``
    );
  }

  try {
    const reply = await chatWithAI(userId, text);
    await sendMessage(chatId, reply);
  } catch (e) {
    console.error("Lỗi:", e.message);
    await sendMessage(chatId, `❌ Lỗi: ${e.message}\n\nAnh thử lại hoặc gõ /reset nhé!`);
  }
}

async function main() {
  console.log(`✅ Bé Kong đang chạy — model: ${MODEL_NAME}`);
  let offset = 0;
  while (true) {
    try {
      const updates = await getUpdates(offset);
      for (const u of updates) {
        handleUpdate(u); // không await → xử lý song song, không block
        offset = u.update_id + 1;
      }
    } catch (e) {
      console.error("Polling lỗi:", e.message);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
}

main();
