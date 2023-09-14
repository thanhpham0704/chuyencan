import streamlit as st
import requests
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import streamlit_authenticator as stauth
import numpy as np
import io
buffer = io.BytesIO()


page_title = "Quản lý quá trình học tập"
page_icon = "👦🏻"
layout = "wide"
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)

# ----------------------------------------
names = ["Phạm Tấn Thành", "Phạm Minh Tâm", "Vận hành", "Kinh doanh", "SOL"]
usernames = ["thanhpham", "tampham",
             "vietopvanhanh", 'vietopkinhdoanh', 'vietop_sol']


# Load hashed password
file_path = Path(__file__).parent / 'hashed_pw.pkl'
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
                                    "sales_dashboard", "abcdef", cookie_expiry_days=1)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

if authentication_status:
    authenticator.logout("logout", "main")

    # Add CSS styling to position the button on the top right corner of the page
    st.markdown(
        """
            <style>
            .stButton button {
                position: absolute;
                top: 0px;
                right: 0px;
            }
            </style>
            """,
        unsafe_allow_html=True
    )
    st.title(page_title + " " + page_icon)
    st.markdown("---")
    # ----------------------#
    # Filter
    # now = datetime.now()
    # DEFAULT_START_DATE = datetime(now.year, now.month, 1)
    # DEFAULT_END_DATE = datetime(now.year, now.month, 1) + timedelta(days=32)
    # DEFAULT_END_DATE = DEFAULT_END_DATE.replace(day=1) - timedelta(days=1)

    @st.cache_data(ttl=timedelta(hours=3))
    def collect_data(link):
        return (pd.DataFrame((requests.get(link).json())))

    @st.cache_data(ttl=timedelta(hours=3))
    def collect_filtered_data(table, date_column='', start_time='', end_time=''):
        link = f"https://vietop.tech/api/get_data/{table}?column={date_column}&date_start={start_time}&date_end={end_time}"
        df = pd.DataFrame((requests.get(link).json()))
        df[date_column] = pd.to_datetime(df[date_column])
        return df

    @st.cache_data()
    def rename_lop(dataframe, column_name):
        dataframe[column_name] = dataframe[column_name].replace(
            {1: "Hoa Cúc", 2: "Gò Dầu", 3: "Lê Quang Định", 5: "Lê Hồng Phong"})
        return dataframe

    @st.cache_data()
    def grand_total(dataframe, column):
        # create a new row with the sum of each numerical column
        totals = dataframe.select_dtypes(include=[float, int]).sum()
        totals[column] = "Tổng giờ"
        # append the new row to the dataframe
        dataframe = dataframe.append(totals, ignore_index=True)
        return dataframe
    # Define a function

    @st.cache_data(ttl=timedelta(hours=3))
    def read_excel_cache(name):
        df = pd.read_excel(name)
        return df

    @st.cache_data(ttl=timedelta(hours=3))
    def bar(df, yvalue, xvalue, text, title, y_title, x_title, color=None, discrete_sequence=None, map=None):
        fig = px.bar(df, y=yvalue,
                     x=xvalue, text=text, color=color, color_discrete_sequence=discrete_sequence, color_discrete_map=map)
        fig.update_layout(
            title=title,
            yaxis_title=y_title,
            xaxis_title=x_title,
        )
        fig.update_traces(textposition='auto')
        return fig

    @st.cache_data(ttl=timedelta(hours=3))
    def chuyencan_converter(df):
        # Mapping diemdanh_details.chuyencan
        conditions = df.chuyencan == 1, df.chuyencan == 4, df.chuyencan == 7, df.chuyencan == 0
        choices = ["Đi học", "Không học", "Nghỉ học", "Thiếu data"]
        df.chuyencan = np.select(conditions, choices)
        return df
    # Import data
    lophoc = collect_data(
        'https://vietop.tech/api/get_data/lophoc')
    orders = collect_data('https://vietop.tech/api/get_data/orders')
    hocvien = collect_data(
        'https://vietop.tech/api/get_data/hocvien')
    molop = collect_data('https://vietop.tech/api/get_data/molop')
    lophoc_schedules = collect_data(
        'https://vietop.tech/api/get_data/lophoc_schedules')
    users = collect_data('https://vietop.tech/api/get_data/users')
    diemdanh_details = collect_filtered_data(
        table='diemdanh_details', date_column='date_created', start_time='2022-06-01', end_time='3000-01-01')
    history = collect_data('https://vietop.tech/api/get_data/history')
    history_nghi = history.query("action =='email' and object =='danger'")
    #%%
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------]\

    orders_ketthuc = orders[['ketoan_id', 'hv_id',
                             'ketoan_active']].query('ketoan_active == 5')
    orders_conlai = orders[['ketoan_id', 'hv_id']
                           ][orders.ketoan_active.isin([0, 1, 4])]
    hv_conlai = hocvien[['hv_id']].merge(orders_conlai, on='hv_id')
    orders_kt_that = orders_ketthuc[~orders_ketthuc['hv_id'].isin(
        hv_conlai['hv_id'])]
    orders_kt_that.drop("ketoan_active", axis=1, inplace=True)
    # Orders không có kết thúc thật
    orders_subset = orders[['ketoan_id',
                            'ketoan_sogio', 'hv_id', 'ketoan_active']]
    orders_ko_ktthat = orders_subset[~orders_subset['ketoan_id'].isin(
        orders_kt_that['ketoan_id'])]
    # diemdanh
    diemdanh_details_b2b = hocvien[['hv_id']]\
        .merge(molop.query('molop_active == 1')[['hv_id', 'ketoan_id']], on='hv_id')\
        .merge(diemdanh_details, on='ketoan_id')\
        .merge(lophoc[['lop_id', 'company']], on='lop_id')

    diemdanh_details_b2b.drop("hv_id", axis=1, inplace=True)
    conditions = diemdanh_details_b2b.baitap == 1, diemdanh_details_b2b.baitap == 2, diemdanh_details_b2b.baitap == 0, diemdanh_details_b2b.baitap == 3
    choices = ["Làm đủ", "Không làm bài tập", "Không học", "Làm thiếu bài tập"]
    diemdanh_details_b2b.baitap = np.select(conditions, choices)

    chuyencan = diemdanh_details_b2b.query("chuyencan == 1 or chuyencan == 9")[diemdanh_details_b2b.date_created > '2022-01-01']\
        .merge(orders[['ketoan_id', 'hv_id']], on='ketoan_id')\
        .merge(hocvien[['hv_id', 'hv_coso', 'hv_fullname']], on='hv_id')\
        .groupby(['hv_coso', 'hv_id', 'hv_fullname', 'baitap','company']).size().reset_index(name='baitap_count')\
        # Partition by hv_id
    chuyencan['total'] = chuyencan.groupby(
        ["hv_id"]).baitap_count.transform(np.sum)
    chuyencan['percent_homework'] = round(
        chuyencan['baitap_count'] / chuyencan['total'], 1)
    # chuyencan.drop(["ketoan_id", "hv_id"], axis = 1, inplace = True)
    chuyencan = chuyencan.merge(history_nghi.groupby(["hv_id"]).size(
    ).reset_index(name='email_nhac_nho'), on='hv_id', how='left')
    chuyencan.email_nhac_nho.fillna(0, inplace=True)
    # Danh sach ket thuc that
    orders_ketthuc = orders[['hv_id', 'ketoan_active', 'date_end']]\
        .query('ketoan_active == 5')
    # .query('created_at > "2022-10-01"')
    orders_conlai = orders[['hv_id']][orders.ketoan_active.isin([1])]
    hv_conlai = hocvien[['hv_id']].merge(orders_conlai, on='hv_id')
    orders_kt_that = orders_ketthuc[~orders_ketthuc['hv_id'].isin(
        hv_conlai['hv_id'])]
    orders_kt_that = orders_kt_that.merge(
        hocvien[['hv_id', 'hv_coso', 'hv_fullname', 'hv_status']], on='hv_id')
    orders_kt_that.drop("ketoan_active", axis=1, inplace=True)

    chuyencan = chuyencan[~chuyencan.hv_id.isin(orders_kt_that.hv_id)]

    chuyencan_pivot = chuyencan.pivot_table(
        index=['hv_id', 'hv_coso', 'hv_fullname','company', 'email_nhac_nho', 'total'], columns='baitap', values='baitap_count', fill_value=0).reset_index()

    chuyencan_pivot['Làm thiếu và không làm'] = chuyencan_pivot['Làm thiếu bài tập'] + \
        chuyencan_pivot['Không làm bài tập']
    # chuyencan_pivot = chuyencan_pivot.merge(hocvien[['hv_id']], on='hv_id')

    chuyencan_pivot_subset = chuyencan_pivot[['hv_id', 'company', 'hv_fullname', 'hv_coso', 'email_nhac_nho', 'Không học',
                                              'Làm đủ', 'Làm thiếu và không làm']]

    chuyencan_pivot_subset = rename_lop(chuyencan_pivot_subset, 'hv_coso')
    chuyencan_pivot_subset = chuyencan_pivot_subset.merge(
        orders_ko_ktthat.query('ketoan_active == 1'), on='hv_id', how='left')
    chuyencan_pivot_subset['Tổng buổi khoá học'] = chuyencan_pivot_subset['ketoan_sogio'] / 2
    chuyencan_pivot_subset = chuyencan_pivot_subset.groupby(['hv_id', 'company', 'hv_fullname', 'hv_coso', 'email_nhac_nho', 'Không học',
                                                             'Làm đủ', 'Làm thiếu và không làm'], as_index=False)['Tổng buổi khoá học'].sum()
    chuyencan_pivot_subset.set_index("hv_id", inplace=True)
    chuyencan_pivot_subset["Tỉ lệ làm thiếu và không làm theo tổng buổi khoá học"] = chuyencan_pivot_subset['Làm thiếu và không làm'] / \
        chuyencan_pivot_subset['Tổng buổi khoá học']
    chuyencan_pivot_subset['Phân loại tỉ lệ làm thiếu và không làm theo tổng buổi khoá học'] = ["bé hơn 10%" if i < 0.1 else "10% đến 15%" if i >= 0.1 and i < 0.15 else "từ 15% đến 20%" if i >= 0.15 and i < 0.2 else "từ 20% trở lên"
                                                                                                for i in chuyencan_pivot_subset["Tỉ lệ làm thiếu và không làm theo tổng buổi khoá học"]]
    # Create two columns
    col1, col2 = st.columns([1, 1])

    # Add the select boxes to the columns
    with col1:
        chinhanh_filter = st.selectbox(label="Select chi nhánh:",
                                    options=list(chuyencan_pivot_subset['hv_coso'].unique()))

    with col2:
        hocvien_filter = st.selectbox(label="Select loại học viên:",
                                    options=list(chuyencan_pivot_subset['company'].unique()))
    ""

    # submit_button = st.form_submit_button(
    #     label='Filter',  use_container_width=True)

    st.subheader(f"Làm bài tập ({chuyencan_pivot_subset.shape[0]} học viên)")
    st.dataframe(chuyencan_pivot_subset.query('hv_coso == @chinhanh_filter and company == @hocvien_filter').sort_values('Làm thiếu và không làm', ascending=False).style.background_gradient(
        cmap='YlOrRd').format({"Tỉ lệ làm thiếu và không làm theo tổng buổi khoá học": '{:,.2%}', 'email_nhac_nho': '{:,.0f}', 'Tổng buổi khoá học': '{:,.0f}'}))

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        chuyencan_pivot_subset.sort_values('Làm thiếu và không làm', ascending=False).sort_values(
            'Làm thiếu và không làm', ascending=False).to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download",
            data=buffer,
            file_name="Số lần làm bài tập của học viên.xlsx",
            mime="application/vnd.ms-excel"
        )
    #%%
    # Tỉ lệ nghỉ
   
    diemdanh_details_subset = diemdanh_details_b2b[diemdanh_details_b2b.chuyencan.isin([1, 4, 7, 0])]\
        .groupby(["ketoan_id","company", "chuyencan"]).size().reset_index(name='count_chuyencan')
    # Mapping
    diemdanh_details_subset['chuyencan'] = diemdanh_details_subset['chuyencan']\
        .replace({1: 'Đi học', 4: 'Không học', 7: 'Nghỉ học'})

    # Tỉ lệ nghỉ
    absent_rate = orders_ko_ktthat.merge(
        diemdanh_details_subset, on='ketoan_id', how='inner')
    # Pivot chuyencan
    absent_rate = absent_rate.pivot_table(
        index=['ketoan_id',"company", 'ketoan_sogio', 'hv_id'], columns='chuyencan', values='count_chuyencan', fill_value=0).reset_index()

    absent_rate['Tổng buổi khoá học'] = absent_rate['ketoan_sogio'] / 2
    absent_rate.drop(["ketoan_sogio"], axis='columns', inplace=True)

    # Email nhac nho
    count_history_nghi = history_nghi.groupby(
        "hv_id").size().reset_index(name='count_nhacnho')
    absent_rate = absent_rate.merge(count_history_nghi, on='hv_id', how='left')
    # Merge hocvien
    absent_rate = absent_rate.merge(hocvien[['hv_id', 'hv_coso', 'hv_fullname', 'hv_camket', ]]
                                    .query("hv_camket != 'Huỷ hợp đồng 1' and hv_camket != 'Huỷ hợp đồng 2'"), on='hv_id')
    absent_rate.fillna(0, inplace=True)  # Fillna
    absent_rate = absent_rate.groupby(["hv_id", "company","hv_fullname", "hv_coso", "hv_camket", "count_nhacnho",])['Đi học', 'Nghỉ học', 'Không học', 'Tổng buổi khoá học']\
        .sum().reset_index()

    # Add colum absent_rate
    absent_rate["Tỉ lệ nghỉ theo tổng buổi khoá học"] = absent_rate['Nghỉ học'] / \
        absent_rate['Tổng buổi khoá học']

    absent_rate['Phân loại tỉ lệ nghỉ theo tổng buổi khoá học'] = ["bé hơn 6%" if i < 0.06 else "6% đến 10%" if i >= 0.06 and i < 0.1 else "từ 10% đến 12%" if i >= 0.1 and i < 0.12 else "từ 12% trở lên"
                                                                   for i in absent_rate["Tỉ lệ nghỉ theo tổng buổi khoá học"]]

    # Mapping hv_camket
    conditions = [absent_rate['hv_camket'] == 0, absent_rate['hv_camket'] == 1, absent_rate['hv_camket'] == 2,
                  absent_rate['hv_camket'] == 3, absent_rate['hv_camket'] == 4]
    choices = ["Không cam kết", "Cam kết tiêu chuẩn",
               "Huỷ hợp đồng 1", "Huỷ hợp đồng 2", "Cam kết thi thật"]
    absent_rate['hv_camket'] = np.select(conditions, choices)
    absent_rate = rename_lop(absent_rate, 'hv_coso')

    absent_rate.rename(
        columns={'count_nhacnho': 'email_nhac_nho'}, inplace=True)

    # Total remaining_time (thuc gio dang ky)
    total_remaining_time = molop.query("molop_active == 1")[['hv_id', 'ketoan_id']]\
        .merge(orders.query("ketoan_active == 1")[['ketoan_id', 'remaining_time']], on='ketoan_id')\
        .groupby(['hv_id'], as_index=False)['remaining_time'].sum()

    total_remaining_time['Tổng thực buổi của pđk đang học'] = total_remaining_time['remaining_time'] / 2

    absent_rate = absent_rate.merge(
        total_remaining_time, on='hv_id', how='left')
    absent_rate.drop(['remaining_time'], axis=1, inplace=True)
    absent_rate['Tỉ lệ nghỉ theo tổng thực buổi của pđk đang học'] = absent_rate['Nghỉ học'] / \
        absent_rate['Tổng thực buổi của pđk đang học']
    # Category
    absent_rate['Phân loại tỉ lệ nghỉ theo thực buổi của pđk đang học'] = ["bé hơn 6%" if i < 0.06 else "6% đến 10%" if i >= 0.06 and i < 0.1 else "từ 10% đến 12%" if i >= 0.1 and i < 0.12 else "từ 12% trở lên"
                                                                           for i in absent_rate['Tỉ lệ nghỉ theo tổng thực buổi của pđk đang học']]

    absent_rate.set_index("hv_id", inplace=True)
    #%%
    # Create two columns
    col1, col2 = st.columns([1, 1])

    # Add the select boxes to the columns
    with col1:
        chinhanh_filter = st.selectbox(label="Select chi nhánh:",
                                    options=list(absent_rate['hv_coso'].unique()), key='hv_coso_absent')

    with col2:
        hocvien_filter = st.selectbox(label="Select loại học viên:",
                                    options=list(absent_rate['company'].unique()), key='hv_category')
    ""

    st.subheader(f"Chuyên cần ({absent_rate.shape[0]} học viên)")
    st.dataframe(absent_rate.query('hv_coso == @chinhanh_filter and company == @hocvien_filter').sort_values('Tỉ lệ nghỉ theo tổng thực buổi của pđk đang học', ascending=False).style.background_gradient(
        cmap='YlOrRd').format({'email_nhac_nho': '{:,.0f}',
                               'Tổng buổi khoá học': '{:,.2f}',
                               'Tổng thực buổi của pđk đang học': '{:,.2f}',
                               'Tỉ lệ nghỉ theo tổng buổi khoá học': '{:.2%}',
                               'Tỉ lệ nghỉ theo tổng thực buổi của pđk đang học': '{:.2%}'}))
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        absent_rate.sort_values('Tỉ lệ nghỉ theo tổng thực buổi của pđk đang học',
                                ascending=False).to_excel(writer, sheet_name='Sheet1')
        # Close the Pandas Excel writer and output the Excel file to the buffer
        writer.save()
        st.download_button(
            label="Download",
            data=buffer,
            file_name="Tỉ lệ nghỉ học viên.xlsx",
            mime="application/vnd.ms-excel"
        )
