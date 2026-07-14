import streamlit as st
import pandas as pd
import json
import os
import re
import datetime
import base64
from PIL import Image

try:
    logo_img = Image.open("logo.png")
except:
    logo_img = "📦"

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="에르메스로직스 웹 시스템", page_icon=logo_img, layout="wide")

DB_FILE = "products_master.json"
CATEGORY_LIST = ["캔", "대캔", "병", "PET", "피쳐", "와인", "사케", "보드카", "PACK", "6PACK", "RFID", "미분류"]

# --- 마스터 데이터 로드/저장 ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return [{"code": "A200606221", "name": "_곰표맥주_500ML", "pack": 24, "category": "캔"}]

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'product_list' not in st.session_state:
    st.session_state.product_list = load_db()

if 'current_page' not in st.session_state:
    st.session_state.current_page = "PK_출고작업"

def navigate_to(page):
    st.session_state.current_page = page

# --- 사이드바 (메뉴) ---
with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.title("📦 에르메스로직스")
    st.caption("웹 기반 물류 자동화 시스템 v4.0")
    st.divider()
    
    with st.expander("📦 피케이유통", expanded=True):
        if st.button("✔️ 출고작업 (피킹지)", use_container_width=True): navigate_to("PK_출고작업")
        if st.button("✨ 상품마스터", use_container_width=True): navigate_to("COMMON_PK_마스터")
            
    with st.expander("🥛 남양유업", expanded=False):
        if st.button("📊 재고현황", use_container_width=True): navigate_to("NY_재고현황")
        if st.button("📍 로케이션 정보", use_container_width=True): navigate_to("NY_로케이션")
        if st.button("🖨️ 물표 뽑기", use_container_width=True): navigate_to("NY_물표")
        if st.button("📥 입고정보 (탈지분유)", use_container_width=True): navigate_to("NY_입고")
        if st.button("📦 출고 DATA 정리", use_container_width=True): navigate_to("NY_출고")
        if st.button("✨ 남양 상품마스터", use_container_width=True): navigate_to("NY_마스터")
        
    st.divider()
    st.markdown("<p style='text-align: center; color: gray; font-size: 14px;'>Developed by <b>BY_JIN</b></p>", unsafe_allow_html=True)


# ==========================================
# 1. 공통 마스터 관리
# ==========================================
if st.session_state.current_page == "COMMON_PK_마스터":
    st.header("✨ 피킹 상품 · 중분류 관리 마스터")
    with st.form("add_product_form"):
        col1, col2, col3, col4, col5 = st.columns(5)
        new_code = col1.text_input("물품코드*")
        new_name = col2.text_input("물품명")
        new_pack = col3.number_input("본입수", min_value=1, value=24)
        new_cat = col4.selectbox("소분류명(유형)", CATEGORY_LIST)
        submitted = col5.form_submit_button("추가")
        
        if submitted and new_code and new_name:
            st.session_state.product_list.insert(0, {"code": new_code, "name": new_name, "pack": int(new_pack), "category": new_cat})
            save_db(st.session_state.product_list)
            st.success("추가 완료!")
            st.rerun()

    st.subheader("등록된 마스터 데이터")
    df_master_view = pd.DataFrame(st.session_state.product_list)
    if not df_master_view.empty:
        st.dataframe(df_master_view, use_container_width=True)


# ==========================================
# 2. 피케이유통 - 핵심 로직 (main.py 포팅)
# ==========================================
def process_data(df_raw, mode="client", chk_sum=True):
    df = df_raw.copy()
    if '수량' not in df.columns or '상품코드' not in df.columns or '납품처_약어' not in df.columns:
        st.error("원본 파일에 '수량', '상품코드', '납품처_약어' 열이 완벽히 있는지 확인해주세요!")
        return None
        
    df = df.dropna(subset=['납품처_약어'])
    df = df[~df['납품처_약어'].astype(str).str.contains('소계', na=False)]
    df = df[df['납품처_약어'].astype(str).str.strip() != '']
    
    df['납품처_정제'] = df['납품처_약어'].astype(str).str.replace('홈플러스(주)익스프레스', '', regex=False).str.replace('홈플러스㈜익스프레스', '', regex=False).str.strip()

    if '예상배차' in df.columns: df['예상배차_최종'] = df['예상배차']
    elif len(df.columns) >= 20: df['예상배차_최종'] = df.iloc[:, 19] 
    else: df['예상배차_최종'] = '(미배차)'
    df['예상배차_최종'] = df['예상배차_최종'].replace(r'^\s*$', '(미배차)', regex=True).fillna('(미배차)')

    df_master = pd.DataFrame(st.session_state.product_list)
    if not df_master.empty:
        df_master = df_master.rename(columns={'code': '상품코드', 'category': '마스터분류', 'pack': '마스터본입수', 'name': '마스터상품명'})
        df_merged = pd.merge(df, df_master[['상품코드', '마스터분류', '마스터본입수']], on='상품코드', how='left')
        df_merged['마스터분류'] = df_merged['마스터분류'].fillna('미분류')
        if '본입수' in df_merged.columns: df_merged['마스터본입수'] = df_merged['마스터본입수'].fillna(df_merged['본입수']).fillna(1)
        else: df_merged['마스터본입수'] = df_merged['마스터본입수'].fillna(1)
    else:
        df_merged = df.copy()
        df_merged['마스터분류'] = '미분류'
        df_merged['마스터본입수'] = df_merged.get('본입수', 1)

    df_merged['수량'] = pd.to_numeric(df_merged['수량'], errors='coerce').fillna(0).astype(int)
    df_merged['마스터본입수'] = pd.to_numeric(df_merged['마스터본입수'], errors='coerce').fillna(1).astype(int).replace(0, 1)

    if mode == "client":
        if chk_sum:
            df_grouped = df_merged.groupby(['예상배차_최종', '납품처_정제', '마스터분류', '상품코드', '상품명', '마스터본입수'], as_index=False)['수량'].sum()
        else: df_grouped = df_merged.copy()
        df_grouped['박스'] = (df_grouped['수량'] // df_grouped['마스터본입수']).astype(int)
        df_grouped['마스터분류'] = pd.Categorical(df_grouped['마스터분류'], categories=CATEGORY_LIST, ordered=True)
        df_sorted = df_grouped.sort_values(by=['예상배차_최종', '납품처_정제', '마스터분류', '상품코드'], ascending=[True, True, True, True], na_position='last')
        df_final = df_sorted[['예상배차_최종', '납품처_정제', '마스터분류', '상품명', '박스', '마스터본입수', '수량']]
        df_final.columns = ['배차내역', '납품처', '유형', '상품명', '박스 수', '본입 수', '수량']
    
    elif mode == "product":
        df_temp = df_merged.copy()
        df_temp['박스_임시'] = (df_temp['수량'] // df_temp['마스터본입수']).astype(int)
        client_totals = df_temp.groupby('납품처_정제')['박스_임시'].sum().reset_index()
        client_totals.rename(columns={'박스_임시': '거래처총박스'}, inplace=True)
        client_totals = client_totals.sort_values(by=['거래처총박스', '납품처_정제'], ascending=[True, True])
        client_totals['순번'] = range(1, len(client_totals) + 1)
        
        df_merged = pd.merge(df_merged, client_totals, on='납품처_정제', how='left')
        
        df_grouped = df_merged.groupby(['마스터분류', '상품명', '마스터본입수', '납품처_정제', '거래처총박스', '순번'], as_index=False)['수량'].sum()
        df_grouped['박스'] = (df_grouped['수량'] // df_grouped['마스터본입수']).astype(int)
        df_grouped['마스터분류'] = pd.Categorical(df_grouped['마스터분류'], categories=CATEGORY_LIST, ordered=True)
        df_sorted = df_grouped.sort_values(by=['마스터분류', '상품명', '순번'], ascending=[True, True, True])
        
        df_final = df_sorted[['마스터분류', '상품명', '순번', '납품처_정제', '박스', '마스터본입수', '수량', '거래처총박스']]
        df_final.columns = ['유형', '상품명', '순번', '납품처', '박스 수', '본입 수', '수량', '거래처총박스']

    return df_final

def generate_summary_html(df_client):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    client_summary = df_client.groupby('납품처', as_index=False)[['박스 수', '수량']].sum()
    client_summary = client_summary[client_summary['박스 수'] > 0].sort_values(by='납품처')
    product_summary = df_client.groupby(['유형', '상품명'], as_index=False)[['박스 수', '수량']].sum()
    product_summary = product_summary[product_summary['박스 수'] > 0].sort_values(by=['유형', '박스 수', '상품명'], ascending=[True, False, True])
    total_boxes = int(client_summary['박스 수'].sum())
    total_qty = int(client_summary['수량'].sum())
    
    html = f"""<html><head><meta charset="utf-8"><style>
        body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; font-size: 16px; color: #000; }}
        h1 {{ text-align: center; font-size: 28px; margin-bottom: 10px; }}
        .total-info {{ text-align: right; font-size: 22px; font-weight: bold; color: #DC2626; margin-bottom: 20px; }}
        .section-title {{ font-size: 22px; font-weight: bold; margin-top: 30px; margin-bottom: 10px; background-color: #1e3a8a; color: white; padding: 10px; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ border: 1px solid black; padding: 10px; text-align: center; font-size: 16px; }}
        th {{ background-color: #f2f2f2; font-weight: bold; font-size: 18px; }}
        .left-align {{ text-align: left; padding-left: 15px; }}
        .total-row {{ background-color: #d9e1f2; font-weight: bold; font-size: 18px; }}
        .highlight-ml {{ font-weight: 900; font-size: 1.2em; text-decoration: underline; }}
        @media print {{ .page-break {{ page-break-after: always; }} thead {{ display: table-header-group; }} }}
        </style></head><body>
        <h1>📊 당일 출고 총괄 요약판 ({today_str})</h1>
        <div class="total-info">총 출고 : {total_boxes:,} 박스 (낱개 {total_qty:,} 개)</div>
        <div class="section-title">🏢 1. 거래처별 총 출고 현황</div><table><thead><tr><th style="width:10%;">연번</th><th style="width:50%;">납품처명</th><th style="width:20%;">총 박스 수</th><th style="width:20%;">총 수량</th></tr></thead><tbody>"""
    for idx, row in enumerate(client_summary.iterrows(), 1):
        _, r = row
        html += f"<tr><td>{idx}</td><td class='left-align'>{r['납품처']}</td><td><b>{int(r['박스 수']):,}</b></td><td>{int(r['수량']):,}</td></tr>"
    html += f"<tr class='total-row'><td colspan='2'>합 계</td><td>{total_boxes:,}</td><td>{total_qty:,}</td></tr></tbody></table><div class='page-break'></div>"
    
    html += """<div class="section-title">📦 2. 상품별 총 출고 현황</div><table><thead><tr><th style="width:10%;">연번</th><th style="width:15%;">유형</th><th style="width:35%;">상품명</th><th style="width:20%;">총 박스 수</th><th style="width:20%;">총 수량</th></tr></thead><tbody>"""
    for idx, row in enumerate(product_summary.iterrows(), 1):
        _, r = row
        name_bold = re.sub(r'([0-9]+(?:\.[0-9]+)?\s*(?:ML|L|ml|l)(?:\*[0-9]+)?)', r'<span class="highlight-ml">\1</span>', str(r['상품명']))
        html += f"<tr><td>{idx}</td><td>{r['유형']}</td><td class='left-align'>{name_bold}</td><td><b>{int(r['박스 수']):,}</b></td><td>{int(r['수량']):,}</td></tr>"
    html += f"<tr class='total-row'><td colspan='3'>합 계</td><td>{total_boxes:,}</td><td>{total_qty:,}</td></tr></tbody></table></body></html>"
    return html

def generate_pdf_client_html(df_client):
    html = """<html><head><meta charset="utf-8"><style>
        body { font-family: 'Malgun Gothic', sans-serif; padding: 20px; font-size: 16px; color: #000; }
        .page-container { margin-bottom: 50px; }
        .header-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
        .header-table td { border: 2px solid black; padding: 8px; font-weight: bold; }
        .title-td { font-size: 24px; text-align: left; }
        .dispatch-td { text-align: center; width: 140px; font-size: 18px; }
        .main-table { width: 100%; border-collapse: collapse; }
        .main-table th, .main-table td { border: 1px solid black; padding: 10px; text-align: center; font-size: 16px; }
        .main-table th { background-color: #1a237e; color: white; font-weight: bold; font-size: 18px; }
        .main-table td.left-align { text-align: left; font-size: 17px; }
        .highlight-ml { font-weight: 900; font-size: 1.2em; text-decoration: underline; color: #000; }
        .summary-table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 18px; }
        .summary-table th, .summary-table td { border: 1px solid black; padding: 12px; text-align: center; }
        .summary-table th { background-color: #f2f2f2; font-weight: bold; }
        .summary-table td.sum-client { text-align: left; padding-left: 20px; }
        .total-row { background-color: #d9e1f2; font-weight: bold; font-size: 20px; }
        @media print { .page-break { page-break-after: always; } thead { display: table-header-group; } }
        </style></head><body>"""
    summary_group = df_client.groupby(['배차내역', '납품처'], sort=False)['박스 수'].sum().reset_index()
    html += """<div class="page-container"><h2 style="text-align: left; font-size: 26px; margin-bottom: 20px;">배차 및 거래처별 출고 요약 현황</h2><table class="summary-table"><thead><tr><th style="width:25%;">예상배차내역</th><th style="width:55%;">거래처명</th><th style="width:20%;">총 출고 박스 수</th></tr></thead><tbody>"""
    total_all_boxes = 0
    for _, row in summary_group.iterrows():
        b_count = int(row['박스 수'])
        if b_count > 0:
            total_all_boxes += b_count
            html += f"<tr><td>{row['배차내역']}</td><td class='sum-client'>{row['납품처']}</td><td>{b_count}</td></tr>"
    html += f"<tr class='total-row'><td colspan='2' style='text-align: center;'>총 합계</td><td>{total_all_boxes}</td></tr></tbody></table></div><div class='page-break'></div>"
    
    grouped = df_client.groupby(['배차내역', '납품처'], sort=False)
    for (vehicle, client), group in grouped:
        total_box = group['박스 수'].sum()
        if total_box <= 0: continue 
        html += f"""<div class="page-container"><table class="header-table"><tr><td rowspan="2" class="title-td">{client}</td><td class="dispatch-td">배차<br>{vehicle}</td></tr><tr><td class="dispatch-td">총 박스 &nbsp;&nbsp;&nbsp; {total_box}</td></tr></table>
            <table class="main-table"><thead><tr><th style="width:12%;">유형</th><th style="width:48%;">상품명</th><th style="width:10%;">박스 수</th><th style="width:15%;">본입 수</th><th style="width:15%;">수량</th></tr></thead><tbody>"""
        for _, row in group.iterrows():
            name_bold = re.sub(r'([0-9]+(?:\.[0-9]+)?\s*(?:ML|L|ml|l)(?:\*[0-9]+)?)', r'<span class="highlight-ml">\1</span>', str(row['상품명']))
            html += f"<tr><td><b>{row['유형']}</b></td><td class='left-align'>{name_bold}</td><td><b>{row['박스 수']}</b></td><td>{row['본입 수']}</td><td><b>{row['수량']}</b></td></tr>"
        html += "</tbody></table></div><div class='page-break'></div>"
    html += "</body></html>"
    return html

def generate_pdf_product_html(df_product):
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    html = f"""<html><head><meta charset="utf-8"><style>
        body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; font-size: 16px; color: #000; }}
        .page-container {{ margin-bottom: 50px; }}
        .header-title {{ font-size: 26px; font-weight: bold; margin-bottom: 20px; text-align: left; }}
        .main-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .main-table th, .main-table td {{ border: 1px solid black; padding: 10px; text-align: center; font-size: 16px; }}
        .main-table th {{ background-color: #b4c6e7; color: black; font-weight: bold; font-size: 18px; }}
        .main-table td.left-align {{ text-align: left; font-size: 16px; }}
        .highlight-ml {{ font-weight: 900; font-size: 1.2em; text-decoration: underline; color: #000; }}
        @media print {{ .page-break {{ page-break-after: always; }} thead {{ display: table-header-group; }} }}
        </style></head><body>
        <div class="page-container">
        <div class="header-title">📋 상품별 피킹지 (씨뿌리기용) - {today_str}</div>
        <table class="main-table"><thead><tr>
        <th style="width:8%;">유형</th><th style="width:25%;">상품명</th><th style="width:10%;">총 수량</th><th style="width:7%;">순번</th>
        <th style="width:20%;">납품처</th><th style="width:10%;">박스 수</th><th style="width:10%;">본입 수</th><th style="width:10%;">수량</th>
        </tr></thead><tbody>"""
    grouped = df_product.groupby(['유형', '상품명'], sort=False)
    for (cat, prod_name), group in grouped:
        total_prod_boxes = group['박스 수'].sum()
        if total_prod_boxes <= 0: continue
        row_count = len(group)
        is_first = True
        for _, row in group.iterrows():
            html += "<tr>"
            if is_first:
                html += f"<td rowspan='{row_count}' style='font-weight:bold; font-size:16px;'>{cat}</td>"
                name_bold = re.sub(r'([0-9]+(?:\.[0-9]+)?\s*(?:ML|L|ml|l)(?:\*[0-9]+)?)', r'<span class="highlight-ml">\1</span>', str(row['상품명']))
                html += f"<td rowspan='{row_count}' style='font-weight:bold; font-size:18px;'>{name_bold}</td>"
                html += f"<td rowspan='{row_count}' style='font-weight:bold; font-size:18px;'>{total_prod_boxes}박스</td>"
                is_first = False
            html += f"<td><b>{row['순번']}</b></td><td class='left-align'>{row['납품처']}</td><td>{row['박스 수']}</td><td>{row['본입 수']}</td><td>{row['수량']}</td></tr>"
    html += "</tbody></table></div></body></html>"
    return html

def generate_seed_label_html(df_product):
    unique_clients = df_product[['순번', '납품처']].drop_duplicates().sort_values('순번')
    html = """<html><head><meta charset="utf-8"><style>
        @page { size: A4 landscape; margin: 8mm; }
        body { margin: 0; padding: 0; font-family: 'Malgun Gothic', sans-serif; box-sizing: border-box; }
        .label-container { width: 100%; height: 92vh; margin: 0 auto; display: flex; flex-direction: column; padding: 5px; box-sizing: border-box; page-break-after: always; }
        .label-table { width: 100%; height: 100%; border-collapse: collapse; border: 8px solid black; table-layout: fixed; }
        .label-table td { border: 5px solid black; text-align: center; vertical-align: middle; color: black; font-weight: bold; padding: 0; }
        .num-cell { height: 35%; font-size: 15vw; letter-spacing: 0.5vw; }
        .client-cell { height: 65%; font-size: 16vw; letter-spacing: 0vw; }
        </style></head><body>"""
    for _, row in unique_clients.iterrows():
        html += f"""<div class="label-container"><table class="label-table"><tr><td class="num-cell">{row['순번']}번</td></tr><tr><td class="client-cell">{row['납품처']}</td></tr></table></div>"""
    html += "</body></html>"
    return html

def generate_seed_sequence_html(df_product):
    unique_clients = df_product[['순번', '납품처', '거래처총박스']].drop_duplicates().sort_values('순번')
    total_all_boxes = unique_clients['거래처총박스'].sum()
    
    html = f"""<html><head><meta charset="utf-8"><style>
        body {{ font-family: 'Malgun Gothic', sans-serif; padding: 30px; font-size: 18px; color: #000; }}
        h1 {{ text-align: center; font-size: 32px; margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ border: 2px solid black; padding: 15px; text-align: center; font-size: 20px; }}
        th {{ background-color: #f2f2f2; font-weight: bold; font-size: 22px; }}
        .left-align {{ text-align: left; padding-left: 20px; }}
        .total-row {{ background-color: #d9e1f2; font-weight: bold; font-size: 24px; }}
        </style></head><body>
        <h1>📜 씨뿌리기 거래처 순번 요약표</h1>
        <table><thead><tr><th style="width:15%;">순번</th><th style="width:60%;">거래처명 (납품처)</th><th style="width:25%;">총 박스 수</th></tr></thead><tbody>"""
        
    for _, row in unique_clients.iterrows():
        html += f"<tr><td><b>{row['순번']}</b></td><td class='left-align'>{row['납품처']}</td><td><b>{row['거래처총박스']}</b></td></tr>"
        
    html += f"<tr class='total-row'><td colspan='2'>총 합계</td><td>{total_all_boxes}</td></tr></tbody></table></body></html>"
    return html

def parse_date(d_str):
    d_str = "".join(filter(str.isdigit, str(d_str)))
    if len(d_str) >= 8:
        try:
            dt = datetime.datetime.strptime(d_str[:8], "%Y%m%d")
            days = ["월", "화", "수", "목", "금", "토", "일"]
            return f"{dt.strftime('%y')}-{dt.month}-{dt.day}", days[dt.weekday()]
        except: pass
    return "26-7-15", "수"

def clean_car_name(raw):
    raw = str(raw)
    disp = re.sub(r'[()\[\]┌┐]', '', raw)
    if '장림DC' in disp: clean_part = '장림CJ'
    elif '칠곡' in disp: clean_part = '칠곡' 
    else:
        match = re.match(r'^[^0-9A-Za-z]+', disp)
        clean_part = match.group(0).strip() if match else disp
    if not clean_part: clean_part = disp
    return " ".join(list(clean_part)) 

def generate_labels_html(df_raw, mode="seed"):
    df = df_raw.copy()
    if '납품처_약어' not in df.columns: return ""
    df = df.dropna(subset=['납품처_약어'])
    df = df[~df['납품처_약어'].astype(str).str.contains('소계', na=False)]
    df = df[df['납품처_약어'].astype(str).str.strip() != '']
    df['납품처_원본'] = df['납품처_약어'].astype(str)
    df['납품처_정제'] = df['납품처_약어'].astype(str).str.replace('홈플러스(주)익스프레스', '', regex=False).str.replace('홈플러스㈜익스프레스', '', regex=False).str.strip()
    
    df['날짜_Raw'] = df.iloc[:, 1].astype(str) if len(df.columns) > 1 else ""
    barcode_cols = [c for c in df.columns if '전표' in c or '바코드' in c]
    df['바코드'] = df[barcode_cols[0]].astype(str) if barcode_cols else (df.iloc[:, 17].astype(str) if len(df.columns) >= 18 else "")
    df['배차_Raw'] = df['예상배차'] if '예상배차' in df.columns else (df.iloc[:, 19] if len(df.columns) >= 20 else "(미배차)")
    df['배차_Raw'] = df['배차_Raw'].replace(r'^\s*$', '(미배차)', regex=True).fillna('(미배차)')

    df_master = pd.DataFrame(st.session_state.product_list).rename(columns={'code': '상품코드', 'pack': '마스터본입수'})
    if not df_master.empty and '상품코드' in df.columns:
        df = pd.merge(df, df_master[['상품코드', '마스터본입수']], on='상품코드', how='left')
        if '본입수' in df.columns: df['마스터본입수'] = df['마스터본입수'].fillna(df['본입수'])
    else: df['마스터본입수'] = df.get('본입수', 1)

    df['수량'] = pd.to_numeric(df['수량'], errors='coerce').fillna(0).astype(int)
    df['마스터본입수'] = pd.to_numeric(df['마스터본입수'], errors='coerce').fillna(1).astype(int).replace(0, 1)
    df['박스_임시'] = (df['수량'] // df['마스터본입수']).astype(int)

    records = []
    if mode == "seed":
        client_totals = df.groupby('납품처_정제')['박스_임시'].sum().reset_index()
        client_totals.rename(columns={'박스_임시': '거래처총박스'}, inplace=True)
        client_totals = client_totals.sort_values(by=['거래처총박스', '납품처_정제'], ascending=[True, True])
        client_totals['순번'] = range(1, len(client_totals) + 1)
        df = pd.merge(df, client_totals[['납품처_정제', '순번']], on='납품처_정제', how='left')
        for client_orig, group in df.groupby('납품처_원본'):
            total_boxes = group['박스_임시'].sum()
            if total_boxes <= 0: continue
            first = group.iloc[0]
            date_str, day_str = parse_date(first['날짜_Raw'])
            seq = first['순번']
            clean_client_name = client_orig.replace('홈플러스(주)익스프레스', '홈플러스㈜익스프레스')
            records.append({'client': clean_client_name, 'total_boxes': total_boxes, 'date': date_str, 'day': day_str, 'barcode': str(first['바코드']).replace(".0", ""), 'raw_car': first['배차_Raw'], 'clean_car': clean_car_name(first['배차_Raw']), 'seq': seq})
        records.sort(key=lambda x: x['seq'])
        seq_style = ".seq-text { color: #DC2626; font-weight: 900; margin-right: 1.5vw; }"
    else:
        for client, group in df.groupby('납품처_약어'):
            total_boxes = group['박스_임시'].sum()
            if total_boxes <= 0: continue
            first = group.iloc[0]
            date_str, day_str = parse_date(first['날짜_Raw'])
            records.append({'client': client, 'total_boxes': total_boxes, 'date': date_str, 'day': day_str, 'barcode': str(first['바코드']).replace(".0", ""), 'raw_car': first['배차_Raw'], 'clean_car': clean_car_name(first['배차_Raw'])})
        records.sort(key=lambda x: (x['raw_car'], x['client']))
        seq_style = ""

    html = f"""<html><head><meta charset="utf-8"><style>
        @page {{ size: A4 landscape; margin: 8mm; }}
        body {{ margin: 0; padding: 0; font-family: 'Malgun Gothic', sans-serif; box-sizing: border-box; }}
        .label-container {{ width: 100%; height: 92vh; margin: 0 auto; display: flex; flex-direction: column; padding: 5px; box-sizing: border-box; page-break-after: always; }}
        .label-table {{ width: 100%; height: 100%; border-collapse: collapse; border: 8px solid black; table-layout: fixed; }}
        .label-table td {{ border: 4px solid black; text-align: center; vertical-align: middle; padding: 0; color: black; }}
        .date-cell {{ font-size: 5vw; font-weight: bold; width: 22%; }}
        .day-cell {{ font-size: 7.5vw; font-weight: bold; width: 13%; }}
        .company-cell {{ font-size: 2.8vw; font-weight: bold; width: 30%; height: 15vh; }}
        .barcode-cell {{ font-size: 5vw; font-family: 'Code 128', sans-serif; width: 35%; height: 15vh; }}
        .box-title-cell {{ font-size: 4vw; font-weight: bold; height: 15vh; }}
        .box-count-cell {{ font-size: 5vw; font-weight: bold; height: 15vh; }}
        .car-cell {{ font-size: 22vw; font-weight: bold; height: 50vh; letter-spacing: 4vw; text-indent: 4vw; }}
        .client-cell {{ font-size: 4.8vw; font-weight: bold; height: 20vh; letter-spacing: 0; text-align: center; }}
        {seq_style}
        </style></head><body>"""
    
    for rec in records:
        pallet_count = int((rec['total_boxes'] - 1) // 50) + 1
        for _ in range(pallet_count * 2):
            if mode == "seed":
                cell_formatted = f"""<td colspan="4" class="client-cell"><span class="seq-text">[{rec['seq']}번]</span>{rec['client']}</td>"""
            else:
                cell_formatted = f"""<td colspan="4" class="client-cell">{rec['client']}</td>"""
            html += f"""<div class="label-container"><table class="label-table"><tr><td rowspan="2" class="date-cell">{rec['date']}</td><td rowspan="2" class="day-cell">{rec['day']}</td><td class="company-cell">피케이유통 주식회사</td><td class="barcode-cell">{rec['barcode']}</td></tr><tr><td class="box-title-cell">박스 수</td><td class="box-count-cell">{rec['total_boxes']}박스</td></tr><tr><td colspan="4" class="car-cell">{rec['clean_car']}</td></tr><tr>{cell_formatted}</tr></table></div>"""
    html += "</body></html>"
    return html

if st.session_state.current_page == "PK_출고작업":
    try:
        with open("C:/Users/user22073/.gemini/antigravity/brain/3531cf82-0de7-43ff-91de-92372ce6a25f/wine_logistics_banner_1783997018917.png", "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        banner_html = f"""
        <div style="
            background-image: linear-gradient(to right, rgba(255,255,255,1) 0%, rgba(255,255,255,0.7) 40%, rgba(255,255,255,0) 100%), url('data:image/png;base64,{img_b64}');
            background-size: cover;
            background-position: center;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        ">
            <h1 style="margin:0; color:#333; font-size: 32px;">✔️ 피케이유통 — 피킹 & 물표 출력</h1>
            <p style="margin:5px 0 0 0; color:#555; font-size: 16px;">WMS 로우 데이터를 업로드하고 피킹지와 물표를 생성하세요.</p>
        </div>
        """
        st.markdown(banner_html, unsafe_allow_html=True)
    except:
        st.header("✔️ 피케이유통 — 피킹 & 물표 출력")
    
    uploaded_file = st.file_uploader("WMS 로우 엑셀(또는 CSV) 파일을 올려주세요.", type=['xlsx', 'xls', 'csv'])
    chk_sum = st.checkbox("수량 합산 (중복 상품 합치기)", value=True)
    is_uploaded = uploaded_file is not None

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔍 데이터 검증", use_container_width=True, disabled=not is_uploaded):
            try:
                if uploaded_file.name.lower().endswith('.csv'):
                    try: df_raw = pd.read_csv(uploaded_file, encoding='cp949')
                    except: df_raw = pd.read_csv(uploaded_file, encoding='utf-8')
                else:
                    df_raw = pd.read_excel(uploaded_file)
                df_raw.columns = df_raw.columns.str.strip().str.replace('\n', '').str.replace('\r', '')
                
                if '수량' not in df_raw.columns or '납품처_약어' not in df_raw.columns:
                    st.error("원본 엑셀에서 '수량', '납품처_약어' 열을 찾을 수 없습니다.")
                else:
                    df_raw_clean = df_raw.dropna(subset=['납품처_약어'])
                    df_raw_clean = df_raw_clean[~df_raw_clean['납품처_약어'].astype(str).str.contains('소계', na=False)]
                    df_raw_clean = df_raw_clean[df_raw_clean['납품처_약어'].astype(str).str.strip() != '']
                    raw_total = pd.to_numeric(df_raw_clean['수량'], errors='coerce').fillna(0).astype(int).sum()
                    
                    df_client = process_data(df_raw, mode="client", chk_sum=chk_sum)
                    df_product = process_data(df_raw, mode="product", chk_sum=chk_sum)
                    
                    if df_client is not None and df_product is not None:
                        client_total, client_box = df_client['수량'].sum(), df_client['박스 수'].sum()
                        product_total = df_product['수량'].sum()
                        if raw_total == client_total == product_total:
                            st.success(f"✅ [검증 완료] 100% 일치! 원본: {raw_total:,}개 / 피킹지: {client_total:,}개 (총 {client_box:,}박스)")
                        else:
                            st.warning(f"❌ [검증 경고] 수량 불일치! 원본: {raw_total:,}개 / 피킹: {client_total:,}개. 확인해주세요.")
            except Exception as e:
                st.error(f"검증 중 에러 발생: {e}")

    with col2:
        if is_uploaded:
            try:
                if uploaded_file.name.lower().endswith('.csv'):
                    try: df_raw = pd.read_csv(uploaded_file, encoding='cp949')
                    except: df_raw = pd.read_csv(uploaded_file, encoding='utf-8')
                else:
                    df_raw = pd.read_excel(uploaded_file)
                df_raw.columns = df_raw.columns.str.strip().str.replace('\n', '').str.replace('\r', '')
                df_client = process_data(df_raw, mode="client", chk_sum=chk_sum)
                if df_client is not None:
                    summary_html = generate_summary_html(df_client)
                    st.download_button("📊 출고 요약 다운로드", data=summary_html, file_name="출고_총괄요약.html", mime="text/html", use_container_width=True)
            except Exception as e:
                st.error(f"요약표 생성 중 에러 발생: {e}")
        else:
            st.button("📊 출고 요약 다운로드", disabled=True, use_container_width=True)
            
    st.divider()
    st.write("### 🖨️ 출력물 다운로드")
    
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    
    if is_uploaded:
        try:
            if uploaded_file.name.lower().endswith('.csv'):
                try: df_raw = pd.read_csv(uploaded_file, encoding='cp949')
                except: df_raw = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df_raw = pd.read_excel(uploaded_file)
            df_raw.columns = df_raw.columns.str.strip().str.replace('\n', '').str.replace('\r', '')
            
            df_client = process_data(df_raw, mode="client", chk_sum=chk_sum)
            df_product = process_data(df_raw, mode="product", chk_sum=chk_sum)
            
            if df_client is not None:
                html_client = generate_pdf_client_html(df_client)
                with row1_col1: st.download_button("📄 거래처 피킹", data=html_client, file_name="피킹지_거래처별.html", mime="text/html", use_container_width=True)
                
                html_label = generate_labels_html(df_raw, mode="normal")
                with row1_col2: st.download_button("🖨️ 일반 물표", data=html_label, file_name="일반물표.html", mime="text/html", use_container_width=True)
                
            if df_product is not None:
                html_seed = generate_pdf_product_html(df_product)
                with row1_col3: st.download_button("📄 씨뿌리기 피킹", data=html_seed, file_name="피킹지_씨뿌리기용.html", mime="text/html", use_container_width=True)
                
                html_seed_bottom = generate_seed_label_html(df_product)
                with row2_col1: st.download_button("🖨️ 씨뿌리기 바닥", data=html_seed_bottom, file_name="씨뿌리기_바닥지.html", mime="text/html", use_container_width=True)
                
                html_seed_box = generate_labels_html(df_raw, mode="seed")
                with row2_col2: st.download_button("🖨️ 파렛트 물표", data=html_seed_box, file_name="씨뿌리기_박스물표.html", mime="text/html", use_container_width=True)
                
                html_seed_seq = generate_seed_sequence_html(df_product)
                with row2_col3: st.download_button("📄 씨뿌리기 순번표", data=html_seed_seq, file_name="씨뿌리기_순번요약.html", mime="text/html", use_container_width=True)
                
        except Exception as e:
            st.error(f"데이터 처리 중 에러가 발생했습니다: {e}")
    else:
        with row1_col1: st.button("📄 거래처 피킹", disabled=True, use_container_width=True)
        with row1_col2: st.button("🖨️ 일반 물표", disabled=True, use_container_width=True)
        with row1_col3: st.button("📄 씨뿌리기 피킹", disabled=True, use_container_width=True)
        with row2_col1: st.button("🖨️ 씨뿌리기 바닥", disabled=True, use_container_width=True)
        with row2_col2: st.button("🖨️ 파렛트 물표", disabled=True, use_container_width=True)
        with row2_col3: st.button("📄 씨뿌리기 순번표", disabled=True, use_container_width=True)

# ==========================================
# 3. 남양유업 기능 (뼈대)
# ==========================================
elif st.session_state.current_page == "NY_재고현황":
    st.header("📊 남양유업 - 재고현황")
    st.info("준비 중입니다.")
elif st.session_state.current_page == "NY_로케이션":
    st.header("📍 남양유업 - 로케이션 정보")
    st.info("준비 중입니다.")
elif st.session_state.current_page == "NY_물표":
    st.header("🖨️ 남양유업 - 물표 뽑기")
    st.info("준비 중입니다.")
elif st.session_state.current_page == "NY_입고":
    st.header("📥 남양유업 - 입고정보 (탈지분유 입고)")
    st.info("준비 중입니다.")
elif st.session_state.current_page == "NY_출고":
    st.header("📦 남양유업 - 출고 DATA 정리")
    st.info("준비 중입니다.")
elif st.session_state.current_page == "NY_마스터":
    st.header("✨ 남양유업 - 상품마스터")
    st.info("준비 중입니다.")