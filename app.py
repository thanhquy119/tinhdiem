import streamlit as st
import pandas as pd
import numpy as np
import tempfile
import os
import dataframe_image as dfi  # pip install dataframe_image
from PIL import Image
import io
import base64
import matplotlib.pyplot as plt

def safe_parse_float(value):
    try:
        return float(value) if value and value.strip() else None
    except ValueError:
        return None

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
                'BT': safe_parse_float(parts[7]),
                'GK': safe_parse_float(parts[8]),
                'CK': safe_parse_float(parts[9]),
                'QT': safe_parse_float(parts[10]) if len(parts) > 10 else None,
                'TN': safe_parse_float(parts[11]) if len(parts) > 11 else None,
                'Thang 10': safe_parse_float(parts[12]) if len(parts) > 12 else None,
                'Thang 4': safe_parse_float(parts[13]) if len(parts) > 13 else None,
                'Thang chữ': parts[14] if len(parts) > 14 else None
            }
            # Làm tròn các giá trị số về 1 số sau dấu phẩy
            for key in ['BT', 'GK', 'CK', 'QT', 'TN', 'Thang 10', 'Thang 4']:
                if row[key] is not None:
                    row[key] = round(row[key], 1)
            rows.append(row)
        except (IndexError, ValueError):
            continue

    df = pd.DataFrame(rows)
    df.insert(0, 'STT', range(1, len(df) + 1))
    return df

def parse_timetable_data(text):
    rows = []
    for line in text.strip().split('\n'):
        if "Tổng cộng:" in line:
            continue
        parts = line.split('\t')
        try:
            if len(parts) < 8:
                continue
                
            # Extract time and room information
            time_info = parts[7].strip()
            time_parts = time_info.split(',')
            
            # Initialize variables
            day = ""
            periods = ""
            room = ""
            
            if len(time_parts) >= 3:
                day = time_parts[0].strip()  # e.g., "Thứ 2"
                periods = time_parts[1].strip()  # e.g., "1-4"
                room = time_parts[2].strip()  # e.g., "P3"
            
            row = {
                'STT': parts[0].strip(),
                'Mã học phần': parts[1].strip(),
                'Tên lớp học phần': parts[2].strip(),
                'Giảng viên': parts[6].strip(),
                'Thứ': day,
                'Tiết': periods,
                'Phòng': room,
                'Thời gian': f"{day},{periods}"  # Keep original format for timetable generation
            }
            
            if row['Thời gian']:
                rows.append(row)
        except Exception as e:
            continue
            
    return pd.DataFrame(rows)

# Chuyển đổi từ giờ phút sang tiết học
def time_to_period(hour, minute):
    # Tạo bảng ánh xạ giờ phút sang tiết học
    time_mappings = [
        ((7, 0), (7, 50), 1),    # 07:00 → 07:50 = Tiết 1
        ((8, 0), (8, 50), 2),    # 08:00 → 08:50 = Tiết 2
        ((9, 0), (9, 50), 3),    # 09:00 → 09:50 = Tiết 3
        ((10, 0), (10, 50), 4),  # 10:00 → 10:50 = Tiết 4
        ((11, 0), (11, 50), 5),  # 11:00 → 11:50 = Tiết 5
        ((12, 30), (13, 20), 6), # 12:30 → 13:20 = Tiết 6
        ((13, 30), (14, 20), 7), # 13:30 → 14:20 = Tiết 7
        ((14, 30), (15, 20), 8), # 14:30 → 15:20 = Tiết 8
        ((15, 30), (16, 20), 9), # 15:30 → 16:20 = Tiết 9
        ((16, 30), (17, 20), 10),# 16:30 → 17:20 = Tiết 10
        ((17, 30), (18, 15), 11),# 17:30 → 18:15 = Tiết 11
        ((18, 15), (19, 0), 12), # 18:15 → 19:00 = Tiết 12
        ((19, 10), (19, 55), 13),# 19:10 → 19:55 = Tiết 13
        ((19, 55), (20, 40), 14) # 19:55 → 20:40 = Tiết 14
    ]
    
    # Chuyển đổi giờ phút thành số phút từ 00:00
    time_in_minutes = hour * 60 + minute
    
    # Tìm tiết học tương ứng
    for start_time, end_time, period in time_mappings:
        start_minutes = start_time[0] * 60 + start_time[1]
        end_minutes = end_time[0] * 60 + end_time[1]
        
        # Nếu thời gian nằm trong khoảng của tiết học, trả về tiết đó
        if start_minutes <= time_in_minutes <= end_minutes:
            return period
        
        # Nếu thời gian nằm giữa các tiết, trả về tiết gần nhất
        if time_in_minutes < start_minutes and (period == 1 or 
           time_in_minutes > time_mappings[period-2][1][0] * 60 + time_mappings[period-2][1][1]):
            return period
    
    # Nếu thời gian sau tiết cuối cùng
    if time_in_minutes > time_mappings[-1][1][0] * 60 + time_mappings[-1][1][1]:
        return 14
    
    # Mặc định trả về tiết 1 nếu không tìm thấy
    return 1

def generate_timetable(df, custom_courses=None):
    # Tạo danh sách thời gian chính xác
    time_slots = [
        "07:00 → 07:50",
        "08:00 → 08:50",
        "09:00 → 09:50",
        "10:00 → 10:50",
        "11:00 → 11:50",
        "12:30 → 13:20",
        "13:30 → 14:20",
        "14:30 → 15:20",
        "15:30 → 16:20",
        "16:30 → 17:20",
        "17:30 → 18:15",
        "18:15 → 19:00",
        "19:10 → 19:55",
        "19:55 → 20:40"
    ]
    
    timetable = pd.DataFrame(
        index=time_slots,
        columns=["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
    )
    
    # Dictionary ánh xạ tiết học với index thời gian
    period_to_time = {
        1: "07:00 → 07:50",
        2: "08:00 → 08:50",
        3: "09:00 → 09:50",
        4: "10:00 → 10:50",
        5: "11:00 → 11:50",
        6: "12:30 → 13:20",
        7: "13:30 → 14:20",
        8: "14:30 → 15:20",
        9: "15:30 → 16:20",
        10: "16:30 → 17:20",
        11: "17:30 → 18:15",
        12: "18:15 → 19:00",
        13: "19:10 → 19:55",
        14: "19:55 → 20:40"
    }
    
    # Keep track of which time slots are used
    used_time_slots = set()
    
    for _, row in df.iterrows():
        class_time = row.get("Thời gian")
        room = row.get("Phòng", "")
        if class_time:
            parts = class_time.split(',')
            if len(parts) >= 2:
                day = parts[0].strip()
                time_range_str = parts[1].strip()
                try:
                    period_start, period_end = map(int, time_range_str.split('-'))
                    for period in range(period_start, period_end + 1):
                        if period in period_to_time:
                            time_slot = period_to_time[period]
                            used_time_slots.add(time_slot)  # Mark this time slot as used
                            if day in timetable.columns and time_slot in timetable.index:
                                class_info = f"{row['Tên lớp học phần']}"
                                if room:
                                    class_info += f"\n{room}"
                                if pd.isna(timetable.at[time_slot, day]) or timetable.at[time_slot, day] == "":
                                    timetable.at[time_slot, day] = class_info
                                else:
                                    timetable.at[time_slot, day] = f"{timetable.at[time_slot, day]}\n{class_info}"
                except:
                    continue
    
    # Add custom courses if provided
    if custom_courses:
        for course in custom_courses:
            day = course['day']
            # Chuyển đổi giờ bắt đầu và kết thúc sang tiết học
            period_start = course['period_start']
            period_end = course['period_end']
            course_name = course['course_name']
            room = course['room']
            
            for period in range(period_start, period_end + 1):
                if period in period_to_time:
                    time_slot = period_to_time[period]
                    used_time_slots.add(time_slot)  # Mark this time slot as used
                    if day in timetable.columns and time_slot in timetable.index:
                        class_info = f"{course_name}"
                        if room:
                            class_info += f"\n{room}"
                        if pd.isna(timetable.at[time_slot, day]) or timetable.at[time_slot, day] == "":
                            timetable.at[time_slot, day] = class_info
                        else:
                            timetable.at[time_slot, day] = f"{timetable.at[time_slot, day]}\n{class_info}"
    
    # Filter to only include used time slots
    if used_time_slots:
        # Sort time slots to maintain correct order
        used_time_slots = sorted(list(used_time_slots), key=lambda x: time_slots.index(x))
        timetable = timetable.loc[used_time_slots]
    else:
        # If no time slots are used, return an empty dataframe with the correct structure
        timetable = pd.DataFrame(columns=timetable.columns)
    
    # Điền các ô trống bằng chuỗi rỗng thay vì NaN
    timetable = timetable.fillna("")
    return timetable

def validate_timetable_data(df):
    required_columns = ['Tên lớp học phần', 'Thời gian']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    return True

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

        # Changed rounding to 2 decimal places
        gpa_10 = round(total_points_10 / total_credits, 2)
        gpa_4 = round(total_points_4 / total_credits, 2)

        classification = get_classification(gpa_4)

        return gpa_10, gpa_4, classification, total_credits
    except Exception as e:
        st.error(f"Lỗi khi tính GPA: {e}")
        return 0, 0, 'N/A', 0

def calculate_required_gpa(current_gpa, current_credits, total_program_credits, target_gpa):
    """
    Calculate the required GPA for remaining courses to achieve the target GPA
    
    Parameters:
    - current_gpa: Current GPA (either on 4.0 or 10.0 scale)
    - current_credits: Total credits completed so far
    - total_program_credits: Total credits required for graduation
    - target_gpa: Desired final GPA (on same scale as current_gpa)
    
    Returns:
    - required_gpa: GPA needed for remaining courses
    - remaining_credits: Number of credits remaining
    """
    if current_credits >= total_program_credits:
        return None, 0  # Already completed all credits
        
    remaining_credits = total_program_credits - current_credits
    
    # Formula: (target_gpa * total_credits - current_gpa * current_credits) / remaining_credits
    required_gpa = (target_gpa * total_program_credits - current_gpa * current_credits) / remaining_credits
    
    return round(required_gpa, 2), remaining_credits

def style_timetable_for_export(df, theme="light"):
    """Create a styled version of the timetable for export"""
    # Define colors based on theme
    if theme == "dark":
        header_color = '#1E293B'  # Dark blue
        alt_row_color = '#334155'  # Dark blue-gray
        row_color = '#1E293B'      # Dark blue
        border_color = '#475569'   # Medium gray
        text_color = '#F1F5F9'     # Light gray/white
    else:  # Light theme
        header_color = '#4472C4'   # Professional blue
        alt_row_color = '#EDF2F7'  # Light blue/gray
        row_color = '#F8FAFC'      # Very light blue
        border_color = '#BFBFBF'   # Medium gray
        text_color = '#333333'     # Dark gray
    
    # Create a styled dataframe
    styled = df.style.set_properties(**{
        'background-color': row_color,
        'color': text_color,
        'border': f'1px solid {border_color}',
        'padding': '8px',
        'text-align': 'center',
        'font-size': '11pt',
        'font-family': 'Arial, sans-serif',
        'white-space': 'pre-wrap'  # Allow text wrapping
    })
    
    # Apply alternating row colors
    def highlight_rows(x):
        df1 = pd.DataFrame('', index=x.index, columns=x.columns)
        for i in range(len(x)):
            if i % 2 == 1:
                df1.iloc[i, :] = 'background-color: ' + alt_row_color
            else:
                df1.iloc[i, :] = 'background-color: ' + row_color
        return df1
    
    styled = styled.apply(highlight_rows, axis=None)
    
    # Style header
    styled = styled.set_table_styles([
        {'selector': 'thead th', 
         'props': [('background-color', header_color),
                   ('color', text_color),
                   ('font-weight', 'bold'),
                   ('border', f'1px solid {border_color}'),
                   ('padding', '8px'),
                   ('text-align', 'center'),
                   ('font-size', '12pt')]},
        # Add some spacing between cells
        {'selector': 'td, th', 
         'props': [('padding', '8px')]},
        # Give the table a border
        {'selector': 'table',
         'props': [('border-collapse', 'collapse'),
                   ('border', f'2px solid {border_color}'),
                   ('width', '100%')]},
        # Style the index column
        {'selector': 'th.row_heading',
         'props': [('background-color', header_color),
                   ('color', text_color),
                   ('font-weight', 'bold'),
                   ('border', f'1px solid {border_color}'),
                   ('text-align', 'center')]}
    ])
    
    # Add a caption/title
    styled = styled.set_caption("Thời Khóa Biểu")
    
    return styled

def export_table_to_png(df, theme="light"):
    """Export DataFrame to PNG with styling based on theme and improved fonts"""
    try:
        # Define colors based on theme
        if theme == "dark":
            header_color = '#1E293B'  # Dark blue
            alt_row_color = '#334155'  # Dark blue-gray
            row_color = '#1E293B'      # Dark blue
            border_color = '#475569'   # Medium gray
            text_color = '#F1F5F9'     # Light gray/white
            bg_color = '#0F172A'       # Very dark blue
            title_color = '#F1F5F9'    # Light gray/white
        else:  # Light theme
            header_color = '#4472C4'   # Professional blue
            alt_row_color = '#EDF2F7'  # Light blue/gray
            row_color = '#F8FAFC'      # Very light blue
            border_color = '#BFBFBF'   # Medium gray
            text_color = '#333333'     # Dark gray
            bg_color = 'white'         # White
            title_color = '#333333'    # Dark gray
        
        # Set up better fonts
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'DejaVu Sans', 'Verdana', 'Helvetica']
        
        # Use matplotlib for better control over the image generation
        fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
        ax.axis('off')
        fig.patch.set_facecolor(bg_color)  # Set figure background
        
        # Create and style table
        cell_text = []
        for i in range(len(df)):
            cell_text.append(df.iloc[i].tolist())
            
        table = ax.table(
            cellText=cell_text,
            rowLabels=df.index,
            colLabels=df.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1]
        )
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)  # Slightly larger font
        table.scale(1.2, 1.8)
        
        # Style headers with better fonts
        for j, key in enumerate(df.columns):
            table[(0, j)].set_facecolor(header_color)
            table[(0, j)].set_text_props(color=text_color, fontweight='bold', 
                                        family='sans-serif', size=11)  # Improved header font
        
        # Style row labels (time slots) with better fonts
        for i, key in enumerate(df.index):
            table[(i+1, -1)].set_facecolor(header_color)
            table[(i+1, -1)].set_text_props(color=text_color, fontweight='bold', 
                                          family='sans-serif', size=10)  # Improved label font
        
        # Style cells with better fonts
        for i in range(len(df)):
            for j in range(len(df.columns)):
                if i % 2 == 1:
                    table[(i+1, j)].set_facecolor(alt_row_color)
                else:
                    table[(i+1, j)].set_facecolor(row_color)
                # Improved cell font
                table[(i+1, j)].set_text_props(color=text_color, family='sans-serif', size=10,
                                             weight='normal', style='normal')
                
                # Add padding to cell text for better readability
                cell = table[(i+1, j)]
                cell_text = cell.get_text().get_text()
                if '\n' in cell_text:
                    # Improve line spacing for multi-line text
                    lines = cell_text.split('\n')
                    formatted_text = '\n'.join([line.strip() for line in lines])
                    cell.get_text().set_text(formatted_text)
        
        # Add title with better font
        plt.suptitle('Thời Khóa Biểu', fontsize=20, fontweight='bold', 
                   family='sans-serif', y=0.98, color=title_color)
        
        # Add a subtle grid effect
        for pos, cell in table._cells.items():
            cell.set_edgecolor(border_color)
            cell.set_linewidth(0.5)  # Thinner borders for cleaner look
        
        # Save to bytes with better quality
        buf = io.BytesIO()
        plt.savefig(buf, format='png', 
                   bbox_inches='tight',
                   pad_inches=0.5,
                   facecolor=bg_color,
                   edgecolor='none',
                   dpi=300)
        plt.close()
        buf.seek(0)
        return buf.getvalue()
            
    except Exception as e:
        st.error(f"Error exporting table: {str(e)}")
        st.exception(e)
        return None

# Định nghĩa ánh xạ giữa thời gian bắt đầu và kết thúc
def get_time_mappings():
    """
    Trả về hai danh sách:
    1. Danh sách thời gian bắt đầu
    2. Danh sách thời gian kết thúc tương ứng
    """
    # Danh sách các khung giờ học bắt đầu
    start_times = [
        "07:00", "08:00", "09:00", "10:00", "11:00", 
        "12:30", "13:30", "14:30", "15:30", "16:30", 
        "17:30", "18:15", "19:10", "19:55"
    ]
    
    # Danh sách thời gian kết thúc tương ứng với tiết học
    end_times = [
        "07:50", "08:50", "09:50", "10:50", "11:50", 
        "13:20", "14:20", "15:20", "16:20", "17:20", 
        "18:15", "19:00", "19:55", "20:40"
    ]
    
    return start_times, end_times

def main():
    st.title("Ứng dụng Tính điểm học tập và Tạo thời khóa biểu")
    
    # Initialize session state variables if they don't exist
    if "timetable_df" not in st.session_state:
        st.session_state.timetable_df = None
    if "calculated_gpa" not in st.session_state:
        st.session_state.calculated_gpa = False
    if "gpa_data" not in st.session_state:
        st.session_state.gpa_data = None
    if "show_target_calc" not in st.session_state:
        st.session_state.show_target_calc = False
    if "show_png" not in st.session_state:
        st.session_state.show_png = False
    if "png_data" not in st.session_state:
        st.session_state.png_data = None
    if "custom_courses" not in st.session_state:
        st.session_state.custom_courses = []
    if "current_theme" not in st.session_state:
        st.session_state.current_theme = "light"
    if "last_custom_courses_hash" not in st.session_state:
        st.session_state.last_custom_courses_hash = hash(str(st.session_state.custom_courses))
    if "timetable_input" not in st.session_state:
        st.session_state.timetable_input = ""
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0  # Sử dụng để reset form
    
    tabs = st.tabs(["Tính điểm", "Tạo thời khóa biểu"])
    
    with tabs[0]:
        st.header("Chức năng Tính điểm")
        st.markdown("""
        **Hướng dẫn sử dụng:**
        1. Copy toàn bộ bảng điểm và dán vào ô bên dưới.
        2. Nhấn nút "Tính điểm" để xem chi tiết bảng điểm và kết quả tổng hợp.
        """)
        input_text = st.text_area("Nhập dữ liệu điểm:", height=150)
    
        # Button to calculate GPA
        if st.button("Tính điểm", key="calculate_score"):
            if input_text:
                try:
                    df = parse_input_data(input_text)
    
                    gpa_10, gpa_4, classification, total_credits = calculate_gpa(df)
                    
                    # Store results in session state
                    st.session_state.calculated_gpa = True
                    st.session_state.gpa_data = {
                        "df": df,
                        "gpa_10": gpa_10,
                        "gpa_4": gpa_4,
                        "classification": classification,
                        "total_credits": total_credits
                    }
                except Exception as e:
                    st.error(f"Có lỗi xảy ra khi xử lý dữ liệu: {e}")
            else:
                st.warning("Vui lòng nhập dữ liệu điểm!")
        
        # Display GPA results if calculated
        if st.session_state.calculated_gpa and st.session_state.gpa_data:
            df = st.session_state.gpa_data["df"]
            gpa_10 = st.session_state.gpa_data["gpa_10"]
            gpa_4 = st.session_state.gpa_data["gpa_4"]
            classification = st.session_state.gpa_data["classification"]
            total_credits = st.session_state.gpa_data["total_credits"]
            
            st.write("**Bảng điểm chi tiết:**")
            display_df = df.copy()
            numeric_columns = ['Thang 10', 'Thang 4', 'BT', 'GK', 'CK', 'QT', 'TN']
            for col in numeric_columns:
                display_df[col] = display_df[col].apply(lambda x: f'{x:.1f}' if pd.notnull(x) else '')

            st.dataframe(display_df.set_index('STT'), use_container_width=True)
            
            st.write("**Kết quả tổng hợp:**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Điểm TB (Thang 10)", f"{gpa_10:.2f}")
            with col2:
                st.metric("Điểm TB (Thang 4)", f"{gpa_4:.2f}")
            with col3:
                st.metric("Xếp loại", classification)
            with col4:
                st.metric("Tổng số tín chỉ", f"{total_credits:.0f}")
            # Toggle for target GPA calculation
            if st.button("Tính GPA mong ước", key="toggle_target_calc"):
                st.session_state.show_target_calc = True
            
            # Show target GPA section if toggled
            if st.session_state.show_target_calc:
                with st.form(key="target_gpa_form"):
                    st.write("**Tính GPA mong ước:**")
                    st.markdown("""
                    Nhập thông tin để tính điểm trung bình cần đạt cho các môn học còn lại 
                    để đạt được GPA mong muốn khi tốt nghiệp.
                    """)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        program_credits = st.number_input("Tổng số tín chỉ của khung chương trình:", 
                                                        min_value=float(total_credits), value=float(180), step=1.0)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        target_gpa_10 = st.number_input("GPA mong muốn (thang 10):", 
                                                     min_value=0.0, max_value=10.0, value=min(float(0), 10.0), step=0.1)
                    with col2:
                        target_gpa_4 = st.number_input("GPA mong muốn (thang 4):", 
                                                    min_value=0.0, max_value=4.0, value=min(float(0), 4.0), step=0.1)
                    
                    # Submit button for the form
                    submit_button = st.form_submit_button(label="Tính điểm cần đạt")
                    
                    if submit_button:
                        # Calculate required GPA for both scales
                        required_gpa_10, remaining_credits = calculate_required_gpa(
                            gpa_10, total_credits, program_credits, target_gpa_10)
                        
                        required_gpa_4, _ = calculate_required_gpa(
                            gpa_4, total_credits, program_credits, target_gpa_4)
                        
                        st.write("**Kết quả tính toán:**")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Số tín chỉ còn lại", f"{remaining_credits:.0f}")
                        
                        with col2:
                            if required_gpa_10 is not None:
                                if required_gpa_10 > 10:
                                    st.error(f"Không thể đạt GPA {target_gpa_10:.1f}/10 với số tín chỉ còn lại")
                                else:
                                    st.metric("Điểm trung bình cần đạt (thang 10)", f"{required_gpa_10:.1f}")
                            else:
                                st.info("Đã hoàn thành đủ tín chỉ")
                        
                        with col3:
                            if required_gpa_4 is not None:
                                if required_gpa_4 > 4:
                                    st.error(f"Không thể đạt GPA {target_gpa_4:.1f}/4 với số tín chỉ còn lại")
                                else:
                                    st.metric("Điểm trung bình cần đạt (thang 4)", f"{required_gpa_4:.1f}")
                            else:
                                st.info("Đã hoàn thành đủ tín chỉ")
                                
                        # Add interpretation
                        if required_gpa_10 is not None and required_gpa_4 is not None:
                            st.write("**Giải thích:**")
                            if required_gpa_10 <= 10 and required_gpa_4 <= 4:
                                st.success(f"""
                                Để đạt được GPA mong muốn khi tốt nghiệp, bạn cần đạt điểm trung bình 
                                **{required_gpa_10:.1f}/10** (tương đương **{required_gpa_4:.1f}/4**) 
                                cho **{remaining_credits:.0f}** tín chỉ còn lại.
                                """)
                                
                                # Add classification for the required GPA
                                required_classification = get_classification(required_gpa_4)
                                st.info(f"Mức điểm này tương đương với xếp loại: **{required_classification}**")
                            else:
                                st.warning("""
                                Mục tiêu GPA đặt ra quá cao so với GPA hiện tại và số tín chỉ còn lại.
                                Hãy xem xét điều chỉnh mục tiêu GPA hoặc đăng ký thêm tín chỉ nếu có thể.
                                """)
    
    with tabs[1]:
        st.header("Chức năng Tạo thời khóa biểu")
        st.markdown("""
        **Hướng dẫn sử dụng:**
        1. Copy bảng thời khóa biểu và dán vào ô bên dưới.
        2. Nhấn nút "Tạo thời khóa biểu" để xem kết quả.
        3. Bạn có thể thêm các môn học tùy chỉnh nếu cần.
        """)
        
        # Theme selection (đặt ở đầu để có thể sử dụng cho tất cả các thao tác)
        theme = st.radio("Chọn kiểu giao diện xuất ảnh:", ["Light Mode", "Dark Mode"], horizontal=True)
        selected_theme = "light" if theme == "Light Mode" else "dark"
        
        # Cập nhật theme nếu có thay đổi
        if selected_theme != st.session_state.current_theme:
            st.session_state.current_theme = selected_theme
            # Tự động tạo lại ảnh PNG nếu đã có thời khóa biểu
            if st.session_state.timetable_df is not None and not st.session_state.timetable_df.empty:
                try:
                    png_bytes = export_table_to_png(st.session_state.timetable_df, selected_theme)
                    if png_bytes:
                        st.session_state.png_data = png_bytes
                        st.rerun()  # Rerun để hiển thị ảnh mới
                except Exception as e:
                    st.error(f"Lỗi khi tạo ảnh PNG: {str(e)}")
        
        # Lưu dữ liệu thời khóa biểu vào session state để theo dõi thay đổi
        timetable_input = st.text_area("Nhập dữ liệu thời khóa biểu:", height=150)
        
        # Kiểm tra nếu dữ liệu đầu vào thay đổi
        if timetable_input != st.session_state.timetable_input:
            st.session_state.timetable_input = timetable_input
            # Nếu đã có dữ liệu mới và có dữ liệu cũ, tự động tạo lại thời khóa biểu
            if timetable_input and st.session_state.timetable_df is not None:
                try:
                    tt_df = parse_timetable_data(timetable_input)
                    validate_timetable_data(tt_df)
                    timetable_table = generate_timetable(tt_df, st.session_state.custom_courses)
                    st.session_state.timetable_df = timetable_table
                    
                    # Tạo lại ảnh PNG với theme hiện tại
                    png_bytes = export_table_to_png(timetable_table, st.session_state.current_theme)
                    if png_bytes:
                        st.session_state.png_data = png_bytes
                except Exception:
                    # Bỏ qua lỗi, sẽ xử lý khi người dùng bấm nút tạo thời khóa biểu
                    pass

        # Custom course addition
        with st.expander("Thêm môn học tùy chỉnh"):
            st.markdown("Thêm các môn học không có trong dữ liệu thời khóa biểu.")
            
            # Lấy danh sách thời gian
            start_times, end_times = get_time_mappings()
            
            # Sử dụng form_key để reset form sau khi thêm môn học
            with st.form(f"custom_course_form_{st.session_state.form_key}"):
                c1, c2 = st.columns(2)
                with c1:
                    course_name = st.text_input("Tên môn học:")
                with c2:
                    room = st.text_input("Phòng học:")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    day = st.selectbox("Thứ:", ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"])
                
                # Tạo key duy nhất cho mỗi lần form được render
                start_time_key = f"start_time_{st.session_state.form_key}"
                end_time_key = f"end_time_{st.session_state.form_key}"
                
                # Lưu giá trị start_time vào session_state để sử dụng cho việc lọc end_time
                if start_time_key not in st.session_state:
                    st.session_state[start_time_key] = start_times[0]
                
                with c2:
                    # Chọn giờ bắt đầu
                    start_time = st.selectbox(
                        "Giờ bắt đầu:", 
                        start_times,
                        key=start_time_key
                    )
                    
                    # Chuyển đổi sang tiết học
                    hour, minute = map(int, start_time.split(':'))
                    period_start = time_to_period(hour, minute)
                
                # Lấy index của thời gian bắt đầu trong danh sách
                start_index = start_times.index(start_time)
                
                # Lọc danh sách thời gian kết thúc để chỉ hiển thị từ thời gian kết thúc của tiết bắt đầu trở đi
                valid_end_times = end_times[start_index:]
                
                # Đảm bảo giá trị mặc định của end_time là hợp lệ
                if end_time_key not in st.session_state or st.session_state[end_time_key] not in valid_end_times:
                    st.session_state[end_time_key] = valid_end_times[0]
                
                with c3:
                    # Chọn giờ kết thúc từ danh sách đã lọc
                    end_time = st.selectbox(
                        "Giờ kết thúc:", 
                        valid_end_times,
                        key=end_time_key
                    )
                    
                    # Chuyển đổi sang tiết học
                    hour, minute = map(int, end_time.split(':'))
                    period_end = time_to_period(hour, minute)
                
                submit_custom = st.form_submit_button("Thêm môn học")
                
                if submit_custom:
                    if course_name and period_start <= period_end:
                        new_course = {
                            'course_name': course_name,
                            'room': room,
                            'day': day,
                            'period_start': period_start,
                            'period_end': period_end
                        }
                        st.session_state.custom_courses.append(new_course)
                        
                        # Tự động cập nhật thời khóa biểu nếu đã có dữ liệu
                        if st.session_state.timetable_df is not None or timetable_input:
                            try:
                                # Tạo DataFrame từ dữ liệu hiện có
                                if timetable_input:
                                    tt_df = parse_timetable_data(timetable_input)
                                else:
                                    tt_df = pd.DataFrame(columns=['Tên lớp học phần', 'Thời gian', 'Phòng'])
                                
                                # Tạo lại thời khóa biểu
                                timetable_table = generate_timetable(tt_df, st.session_state.custom_courses)
                                st.session_state.timetable_df = timetable_table
                                
                                # Tạo lại ảnh PNG với theme hiện tại
                                png_bytes = export_table_to_png(timetable_table, st.session_state.current_theme)
                                if png_bytes:
                                    st.session_state.png_data = png_bytes
                                
                                # Thông báo thành công
                                st.success(f"Đã thêm môn học: {course_name}")
                                
                                # Tăng form_key để reset form
                                st.session_state.form_key += 1
                                
                                # Rerun để hiển thị thời khóa biểu mới và reset form
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi cập nhật thời khóa biểu: {e}")
                        else:
                            # Nếu chưa có thời khóa biểu
                            st.success(f"Đã thêm môn học: {course_name}")
                            # Tăng form_key để reset form
                            st.session_state.form_key += 1
                            st.rerun()
                    else:
                        st.error("Vui lòng nhập tên môn học và thời gian hợp lệ!")
        
        # Display custom courses
        if st.session_state.custom_courses:
            st.write("**Các môn học đã thêm:**")
            custom_courses_changed = False
            
            for i, course in enumerate(st.session_state.custom_courses):
                cols = st.columns([3, 1, 2, 1, 1])
                with cols[0]:
                    st.write(f"{course['course_name']}")
                with cols[1]:
                    st.write(f"{course['day']}")
                with cols[2]:
                    # Hiển thị giờ học thay vì tiết
                    period_to_time_map = {
                        1: "07:00-07:50", 2: "08:00-08:50", 3: "09:00-09:50",
                        4: "10:00-10:50", 5: "11:00-11:50", 6: "12:30-13:20",
                        7: "13:30-14:20", 8: "14:30-15:20", 9: "15:30-16:20",
                        10: "16:30-17:20", 11: "17:30-18:15", 12: "18:15-19:00",
                        13: "19:10-19:55", 14: "19:55-20:40"
                    }
                    start_time = period_to_time_map.get(course['period_start'], "")
                    end_time = period_to_time_map.get(course['period_end'], "")
                    if start_time and end_time:
                        start_hour = start_time.split('-')[0]
                        end_hour = end_time.split('-')[1]
                        st.write(f"{start_hour} - {end_hour}")
                    else:
                        st.write(f"Tiết {course['period_start']}-{course['period_end']}")
                with cols[3]:
                    st.write(f"{course['room']}")
                with cols[4]:
                    if st.button("Xóa", key=f"delete_{i}"):
                        st.session_state.custom_courses.pop(i)
                        custom_courses_changed = True
                        break  # Dừng vòng lặp sau khi xóa để tránh lỗi index
            
            if st.button("Xóa tất cả môn học tùy chỉnh"):
                st.session_state.custom_courses = []
                custom_courses_changed = True
            
            # Nếu có thay đổi trong danh sách môn học tùy chỉnh, cập nhật thời khóa biểu
            if custom_courses_changed:
                try:
                    # Tạo DataFrame từ dữ liệu hiện có
                    if timetable_input:
                        tt_df = parse_timetable_data(timetable_input)
                    else:
                        tt_df = pd.DataFrame(columns=['Tên lớp học phần', 'Thời gian', 'Phòng'])
                    
                    # Tạo lại thời khóa biểu
                    timetable_table = generate_timetable(tt_df, st.session_state.custom_courses)
                    st.session_state.timetable_df = timetable_table
                    
                    # Tạo lại ảnh PNG với theme hiện tại
                    png_bytes = export_table_to_png(timetable_table, st.session_state.current_theme)
                    if png_bytes:
                        st.session_state.png_data = png_bytes
                    
                    # Rerun để hiển thị thời khóa biểu mới
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi cập nhật thời khóa biểu: {e}")

        if st.button("Tạo thời khóa biểu", key="generate_timetable"):
            if timetable_input or st.session_state.custom_courses:
                try:
                    if timetable_input:
                        tt_df = parse_timetable_data(timetable_input)
                        validate_timetable_data(tt_df)
                    else:
                        # Create an empty DataFrame if only custom courses are provided
                        tt_df = pd.DataFrame(columns=['Tên lớp học phần', 'Thời gian', 'Phòng'])
                    
                    # Generate timetable with custom courses
                    timetable_table = generate_timetable(tt_df, st.session_state.custom_courses)

                    # Store in session state
                    st.session_state.timetable_df = timetable_table
                    
                    # Kiểm tra nếu timetable trống
                    if timetable_table.empty:
                        st.warning("Không có lớp học nào được tìm thấy trong thời khóa biểu.")
                    else:
                        # Generate PNG immediately with current theme
                        try:
                            png_bytes = export_table_to_png(timetable_table, st.session_state.current_theme)
                            if png_bytes:
                                st.session_state.png_data = png_bytes
                                
                                # Display success message
                                st.success("Đã tạo thời khóa biểu thành công!")
                                
                                # Show PNG image
                                st.image(png_bytes, caption="Thời khóa biểu", use_container_width=True)
                                
                                # Add download button
                                st.download_button(
                                    label="Tải ảnh PNG",
                                    data=png_bytes,
                                    file_name="timetable.png",
                                    mime="image/png",
                                    key="download_png"
                                )
                        except Exception as e:
                            st.error(f"Lỗi khi tạo ảnh PNG: {str(e)}")
                            # Fall back to displaying the DataFrame if PNG generation fails
                            st.dataframe(timetable_table, use_container_width=True)

                except Exception as e:
                    st.error(f"Có lỗi khi tạo thời khóa biểu: {e}")
            else:
                st.warning("Vui lòng nhập dữ liệu thời khóa biểu hoặc thêm ít nhất một môn học tùy chỉnh!")

        # Display existing PNG if available but no new timetable was generated
        elif st.session_state.timetable_df is not None and st.session_state.png_data is not None:
            st.write("**Thời khóa biểu:**")
            
            # Display the PNG image
            st.image(st.session_state.png_data, caption="Thời khóa biểu", use_container_width=True)
            
            # Add download button
            st.download_button(
                label="Tải ảnh PNG",
                data=st.session_state.png_data,
                file_name="timetable.png",
                mime="image/png",
                key="download_png"
            )

if __name__ == "__main__":
    main()
