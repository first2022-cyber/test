
import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import quote

# ---------------------------------
# 기본 설정
# ---------------------------------
st.set_page_config(
    page_title="PubChem 분자 구조 탐험",
    page_icon="🧪",
    layout="wide"
)

BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
HEADERS = {
    "User-Agent": "MoleculeStructureExplorer/1.0"
}

# 예시 물질: 화면에 표시할 이름과 PubChem 검색 이름
SAMPLES = {
    "카페인": "caffeine",
    "물": "water",
    "포도당": "glucose",
    "아스피린": "aspirin",
    "비타민 C": "ascorbic acid",
    "에탄올": "ethanol",
    "아세트산": "acetic acid",
    "탄산칼슘": "calcium carbonate",
    "염화나트륨": "sodium chloride",
    "벤젠": "benzene",
}

# ---------------------------------
# PubChem API 함수
# ---------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_molecule_info(name):
    """물질 이름으로 CID, 분자식, 분자량을 조회한다."""
    encoded_name = quote(name.strip(), safe="")

    url = (
        f"{BASE_URL}/compound/name/{encoded_name}"
        "/property/MolecularFormula,MolecularWeight/JSON"
    )

    response = requests.get(
        url, headers=HEADERS, timeout=25
    )
    response.raise_for_status()

    data = response.json()
    props = data["PropertyTable"]["Properties"][0]

    return {
        "cid": props["CID"],
        "formula": props.get("MolecularFormula", "정보 없음"),
        "weight": props.get("MolecularWeight", "정보 없음"),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_2d_image(cid):
    """PubChem에서 2D 구조 PNG 이미지를 가져온다."""
    url = f"{BASE_URL}/compound/cid/{cid}/PNG"
    response = requests.get(
        url,
        params={"image_size": "large"},
        headers=HEADERS,
        timeout=25
    )
    response.raise_for_status()
    return response.content


@st.cache_data(ttl=86400, show_spinner=False)
def get_3d_sdf(cid):
    """PubChem에서 계산된 3D 구조 좌표를 SDF로 가져온다."""
    url = f"{BASE_URL}/compound/cid/{cid}/SDF"

    response = requests.get(
        url,
        params={"record_type": "3d"},
        headers=HEADERS,
        timeout=35
    )
    response.raise_for_status()

    sdf = response.text.strip()

    # 정상적인 SDF 데이터인지 간단히 확인한다.
    if not sdf or "M  END" not in sdf:
        raise ValueError("유효한 3D 구조 데이터가 없습니다.")

    return sdf


# ---------------------------------
# 3D 분자 뷰어
# ---------------------------------
def show_3d_structure(sdf):
    """3Dmol.js로 회전 가능한 3D 분자 구조를 표시한다."""

    # SDF 문자열을 안전하게 JavaScript 문자열로 전달한다.
    sdf_json = json.dumps(sdf)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://3dmol.org/build/3Dmol-min.js"></script>
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          font-family: sans-serif;
          background: #ffffff;
        }}
        #viewer {{
          width: 100%;
          height: 430px;
          position: relative;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          overflow: hidden;
        }}
        .help {{
          color: #555;
          font-size: 13px;
          padding: 8px 2px;
        }}
      </style>
    </head>
    <body>
      <div id="viewer"></div>
      <div class="help">
        마우스 드래그: 회전 · 휠: 확대/축소 · 오른쪽 버튼 드래그: 이동
      </div>

      <script>
        const sdfData = {sdf_json};

        const element = document.getElementById("viewer");
        const viewer = $3Dmol.createViewer(element, {{
          backgroundColor: "white"
        }});

        viewer.addModel(sdfData, "sdf");

        // 원소에 따른 CPK 색상으로 원자와 결합을 표시한다.
        viewer.setStyle({{}}, {{
          stick: {{ radius: 0.16 }},
          sphere: {{ scale: 0.24 }}
        }});

        viewer.zoomTo();
        viewer.zoom(0.85);
        viewer.render();

        window.addEventListener("resize", function() {{
          viewer.resize();
          viewer.render();
        }});
      </script>
    </body>
    </html>
    """

    components.html(html, height=475, scrolling=False)


# ---------------------------------
# 화면 구성
# ---------------------------------
st.title("🧪 PubChem 분자 구조 탐험")
st.write(
    "물질 이름을 선택하거나 입력하면 분자 정보와 "
    "2D·3D 구조를 확인할 수 있습니다."
)

st.info(
    "미국 NIH의 PubChem 데이터를 사용합니다. "
    "API 키는 필요하지 않지만 인터넷 연결이 필요합니다."
)

st.subheader("1. 물질 선택")

mode = st.radio(
    "검색 방법",
    ["예시 물질 선택", "물질 이름 직접 입력"],
    horizontal=True
)

if mode == "예시 물질 선택":
    selected_label = st.selectbox(
        "확인할 물질",
        list(SAMPLES.keys()),
        index=0
    )
    molecule_name = SAMPLES[selected_label]
else:
    molecule_name = st.text_input(
        "물질 이름 (영문 권장)",
        placeholder="예: caffeine, glucose, aspirin"
    ).strip()

search_clicked = st.button(
    "🔍 분자 구조 조회",
    type="primary",
    use_container_width=True
)

# 버튼을 눌렀을 때 검색어를 저장한다.
if search_clicked:
    if molecule_name:
        st.session_state["molecule_to_show"] = molecule_name
    else:
        st.session_state.pop("molecule_to_show", None)
        st.warning("물질 이름을 선택하거나 입력해 주세요.")

# ---------------------------------
# 조회 결과
# ---------------------------------
if "molecule_to_show" in st.session_state:
    query_name = st.session_state["molecule_to_show"]

    try:
        with st.spinner("PubChem에서 분자 정보를 가져오는 중..."):
            info = get_molecule_info(query_name)

        cid = info["cid"]

        st.divider()
        st.subheader(f"2. {query_name}의 분자 정보")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("분자식", info["formula"])

        with col2:
            st.metric(
                "분자량",
                f'{float(info["weight"]):,.3f} g/mol'
            )

        with col3:
            st.metric("PubChem CID", str(cid))

        st.caption(
            f"검색 결과: {query_name} · "
            "이름이 여러 물질을 가리키는 경우 첫 번째 일치 결과가 표시될 수 있습니다."
        )

        st.divider()

        # 2D 구조
        st.subheader("3. 2D 평면 구조")

        try:
            with st.spinner("2D 구조 이미지를 불러오는 중..."):
                image_bytes = get_2d_image(cid)

            st.image(
                image_bytes,
                caption="출처: PubChem",
                width=400
            )

        except requests.RequestException:
            st.warning("2D 구조 이미지를 불러오지 못했습니다.")

        # 3D 구조
        st.divider()
        st.subheader("4. 3D 입체 구조")
        st.write(
            "마우스로 분자를 회전하거나 확대해 입체적인 구조를 관찰해 보세요."
        )

        try:
            with st.spinner("3D 구조 좌표를 불러오는 중..."):
                sdf_data = get_3d_sdf(cid)

            show_3d_structure(sdf_data)

        except (requests.RequestException, ValueError):
            st.warning(
                "이 물질의 3D 구조 데이터를 가져오지 못했습니다. "
                "PubChem에 계산된 3D 구조가 없거나 일시적으로 "
                "서버에 연결할 수 없을 수 있습니다."
            )

        st.markdown(
            f"[🔗 PubChem에서 이 물질 자세히 보기]"
            f"(https://pubchem.ncbi.nlm.nih.gov/compound/{cid})"
        )

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            st.error(
                "해당 이름의 물질을 찾지 못했습니다. "
                "영문 물질 이름이나 다른 명칭으로 다시 검색해 보세요."
            )
        else:
            st.error(
                "PubChem 요청에 실패했습니다. "
                "잠시 후 다시 시도해 주세요."
            )

    except (requests.RequestException, KeyError, ValueError) as e:
        st.error(
            "분자 정보를 처리하지 못했습니다. "
            "인터넷 연결과 물질 이름을 확인해 주세요."
        )

st.divider()
st.caption(
    "데이터: PubChem · 3D 시각화: 3Dmol.js · "
    "분자량은 PubChem에서 제공하는 값입니다."
)
