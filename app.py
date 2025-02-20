import streamlit as st
import pandas as pd
import numpy as np

def parse_input_data(text):
    rows = []
    for line in text.strip().split('\n'):
        parts = line.split('\t')
        try:
            row = {
                'Kỳ/Năm học': parts[1],
                'Mã lớp học phần': parts[3],
                'Tên lớp học phần': parts[4],
                'Số TC': float(parts[5]) if parts[5] else 0,
                'Công thức điểm': parts[6],
                'BT': float(parts[7]) if parts[7] and parts[7].strip() else None,
                'GK': float(parts[8]) if parts[8] and parts[8].strip() else None,
                'CK': float(parts[9]) if parts[9] and parts[9].strip() else None,
                'QT': float(parts[10]) if len(parts) > 10 and parts[10].strip() else None,
                'TN': float(parts[11]) if len(parts) > 11 and parts[11].strip() else None,
                'Thang 10': float(parts[12]) if len(parts) > 12 and parts[12].strip() else None,
                'Thang 4': float(parts[13]) if len(parts) > 13 and parts[13].strip() else None,
                'Thang chữ': parts[14] if len(parts) > 14 else None
            }
            # Làm tròn các giá trị số đến 1 chữ số thập phân
            for key in ['BT', 'GK', 'CK', 'QT', 'TN', 'Thang 10', 'Thang 4']:
                if row[key] is not None:
                    row[key] = round(row[key], 1)
            rows.append(row)
        except (IndexError, ValueError) as e:
            continue
    
    df = pd.DataFrame(rows)
    df.insert(0, 'STT', range(1, len(df) + 1))
    return df

def get_classification(gpa_4):
    if gpa_4 >= 3.6:
        return "Xuất sắc"
    elif gpa_4 >= 3.2:
        return "Giỏi"
    elif gpa_4 >= 2.5:
        return "Khá"
    elif gpa_4 >= 2.0:
        return "Trung bình"
    elif gpa_4 >= 1.0:
        return "Trung bình yếu"
    else:
        return "Kém"

def calculate_gpa(df):
    try:
        valid_courses = df[
            (df['Thang 10'].notna()) & 
            (df['Thang chữ'].notna()) & 
            (df['Số TC'] > 0)
        ]
        
        total_credits = valid_courses['Số TC'].sum()
        if total_credits == 0:
            return 0, 0, 'N/A', 0

        total_points_10 = (valid_courses['Số TC'] * valid_courses['Thang 10']).sum()
        total_points_4 = (valid_courses['Số TC'] * valid_courses['Thang 4']).sum()
        
        gpa_10 = round(total_points_10 / total_credits, 1)
        gpa_4 = round(total_points_4 / total_credits, 1)
        
        classification = get_classification(gpa_4)
        
        return gpa_10, gpa_4, classification, total_credits
    except Exception as e:
        st.error(f"Lỗi khi tính GPA: {str(e)}")
        return 0, 0, 'N/A', 0

def main():
    st.title("Tính điểm học tập")
    
    st.markdown("""
    **Hướng dẫn sử dụng:**
    1. Copy toàn bộ bảng điểm
    2. Paste vào ô bên dưới
    3. Nhấn nút "Tính điểm" để xem kết quả
    """)
    
    input_text = st.text_area("Nhập dữ liệu điểm:", height=150)
    
    if st.button("Tính điểm"):
        if input_text:
            try:
                df = parse_input_data(input_text)
                
                st.write("**Bảng điểm chi tiết:**")
                
                # Định dạng các cột số
                display_df = df.copy()
                numeric_columns = ['Thang 10', 'Thang 4', 'BT', 'GK', 'CK', 'QT', 'TN']
                for col in numeric_columns:
                    display_df[col] = display_df[col].apply(lambda x: f'{x:.1f}' if pd.notnull(x) else '')
                
                st.dataframe(display_df.set_index('STT'), hide_index=False)
                
                gpa_10, gpa_4, classification, total_credits = calculate_gpa(df)
                
                st.write("**Kết quả tổng hợp:**")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Điểm TB (Thang 10)", f"{gpa_10:.1f}")
                with col2:
                    st.metric("Điểm TB (Thang 4)", f"{gpa_4:.1f}")
                with col3:
                    st.metric("Xếp loại", classification)
                with col4:
                    st.metric("Tổng số tín chỉ", f"{total_credits:.0f}")
                
            except Exception as e:
                st.error(f"Có lỗi xảy ra khi xử lý dữ liệu: {str(e)}")
        else:
            st.warning("Vui lòng nhập dữ liệu điểm")

if __name__ == "__main__":
    main()
