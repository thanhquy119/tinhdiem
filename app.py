import streamlit as st
import os
from groq import Groq

# Khởi tạo lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I help you today?"}
    ]

# System prompt được cập nhật để phân loại chi tiêu vào các danh mục cố định
# Các danh mục: Di chuyển, Mua sắm, Ăn uống, Hóa đơn, Giải trí, Y tế, Khác
system_prompt = """
Bạn là một chuyên gia lập trình Expo, React Native và JavaScript. Bạn hỗ trợ người dùng sửa lỗi, tối ưu code, cập nhật phiên bản, và hướng dẫn triển khai ứng dụng Expo. Khi người dùng gửi code, bạn cần:

Phân tích lỗi hoặc vấn đề trong code.
Đề xuất giải pháp chi tiết và giải thích lý do.
Cung cấp code đã chỉnh sửa với chú thích rõ ràng.
Hỗ trợ nâng cấp phiên bản Expo SDK nếu cần.
Tư vấn cách tối ưu hiệu suất, giảm dung lượng ứng dụng.
Giúp debug trên các nền tảng Android, iOS và Web.
Hãy trả lời một cách súc tích, dễ hiểu và cung cấp ví dụ thực tế nếu cần.
"""

# Gọi API của Groq với model llama-3.3-70b-specdec
def deepseek_chat(messages: list) -> str:
    try:
        api_key = os.environ.get("api_key")  # Lấy API key từ biến môi trường
        if not api_key:
            raise ValueError("API key is missing or invalid.")

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="deepseek-r1-distill-qwen-32b",
            messages=[{"role": "system", "content": system_prompt}, *messages],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error occurred: {str(e)}")
        return ""

def main():
    st.title('🤖 HEHE Chatbot')

    # Sidebar với hướng dẫn sử dụng
    with st.sidebar:
        st.header("📚 User Guide")
        st.markdown(
            """- Nhập chi tiêu của bạn, ví dụ: "Hôm nay tôi đi đổ xăng hết 50k".
- Chatbot sẽ tự động phân loại chi tiêu vào các danh mục cố định: Di chuyển, Mua sắm, Ăn uống, Hóa đơn, Giải trí, Y tế, Giáo dục, Đầu tư & tiết kiệm, Khác.
- Kết quả sẽ được hiển thị theo dạng: **Phân loại: [category], Tiền: [amount]**
- Nếu câu hỏi của bạn không liên quan đến chi tiêu, chatbot sẽ trả lời bình thường."""
        )

        if st.button("Reset Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! How can I help you today?"}
            ]
            st.experimental_rerun()

    # Hiển thị lịch sử chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Xử lý đầu vào của người dùng
    if prompt := st.chat_input("What's on your mind?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = deepseek_chat(st.session_state.messages)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
