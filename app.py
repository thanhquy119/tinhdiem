import streamlit as st
import os
from groq import Groq
import re

# Track chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I help you today?"}
    ]

# Hàm xử lý và phân loại chi tiêu
def process_expense_response(response: str, user_input: str) -> str:
    """
    Xử lý và phân loại chi tiêu từ đầu vào của người dùng.
    Trả về chuỗi đã được phân loại và định dạng.
    """
    # Danh sách các từ khóa để phân loại
    expense_categories = {
        "di chuyển": ["đi", "xăng", "vé", "chuyến", "taxi", "grab"],
        "mua sắm": ["mua", "bought", "shopee", "tiki", "lazada", "đồ", "quần", "áo", "giày", "sách", "đồng hồ"],
        "ăn uống": ["ăn", "food", "quán", "nhà hàng", "cơm", "phở", "bún", "mì", "bánh", "trà", "cà phê", "nước", "thức uống"],
        "hóa đơn": ["điện", "nước", "internet", "điện thoại", "bill", "hóa đơn"],
        "giải trí": ["xem", "phim", "rạp", "concert", "karaoke", "games", "trò chơi", "net", "pubg", "mobile", "pubg mobile"],
        "khác": []
    }

    # Lấy số tiền từ đầu vào
    numbers = re.findall(r'\d+', user_input)
    if numbers:
        money = numbers[-1] + "k"  # Giả sử đơn vị là nghìn đồng
    else:
        money = "Không rõ số tiền"

    # Phân loại chi tiêu
    category = "khác"
    for key, keywords in expense_categories.items():
        for word in keywords:
            if word in user_input.lower():
                category = key
                break
        if category != "khác":
            break

    # Tạo chuỗi đầu ra
    formatted_response = f"**Phân loại: {category.capitalize()}, Tiền: {money}**"

    return formatted_response

# Hàm loại bỏ <think>...</think>
def remove_think_tags(response: str) -> str:
    # Loại bỏ phần <think>...</think>
    return re.sub(r"<think>.*?</think>", "", response)

# Gọi API của Groq với model llama-3.3-70b-specdec
def deepseek_chat(messages: list) -> str:
    try:
        api_key = os.environ.get("api_key")  # Lấy API key từ biến môi trường
        if not api_key:
            raise ValueError("API key is missing or invalid.")

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-specdec",  # Cập nhật model mới
            messages=[{"role": "system", "content": """You are a helpful assistant. Always categorize expenses when possible. 
            Format: **Phân loại: [category], Tiền: [amount]**
            Examples:
            - Phân loại: Di chuyển, Tiền: 50k
            - Phân loại: Mua sắm, Tiền: 100k"""}, *messages],
            stream=False
        )
        # Trả về nội dung sau khi loại bỏ các thẻ <think>
        return remove_think_tags(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error occurred: {str(e)}")
        return ""

def main():
    st.title('🤖 HEHE Chatbot')

    # Sidebar with user guide
    with st.sidebar:
        st.header("📚 User Guide")
        st.markdown("""- Nhập chi tiêu của bạn, ví dụ: "Hôm nay tôi đi đổ xăng hết 50k"
        - Chatbot sẽ tự động phân loại và hiển thị kết quả theo dạng: **Phân loại: [category], Tiền: [amount]**
        - Ví dụ:
            - Phân loại: Di chuyển, Tiền: 50k
            - Phân loại: Mua sắm, Tiền: 100k""")

        if st.button("Reset Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! How can I help you today?"}
            ]
            st.rerun()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Handle user input
    if prompt := st.chat_input("What's on your mind?"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Truyền API key vào hàm deepseek_chat
                response = deepseek_chat(st.session_state.messages)  # Không cần truyền api_key nữa

                # Xử lý và phân loại chi tiêu
                if "phân loại:" not in response.lower():
                    processed_response = process_expense_response(response, prompt)
                    st.write(processed_response)
                else:
                    st.write(response)

                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
