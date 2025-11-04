import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

# Open-Meteo API URL
# 404 오류 방지를 위해 URL을 다시 확인합니다.
REVERSE_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/reverse"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

def get_weather_info(code):
    """
    Open-Meteo 날씨 코드를 설명과 이모지로 변환합니다.
    """
    weather_codes = {
        0: ("맑음", "☀️"),
        1: ("대체로 맑음", "🌤️"),
        2: ("부분적으로 흐림", "⛅"),
        3: ("흐림", "☁️"),
        45: ("안개", "🌫️"),
        48: ("서리 안개", "🌫️"),
        51: ("가벼운 이슬비", "🌦️"),
        53: ("보통 이슬비", "🌦️"),
        55: ("강한 이슬비", "🌦️"),
        61: ("가벼운 비", "🌧️"),
        63: ("보통 비", "🌧️"),
        65: ("강한 비", "🌧️"),
        71: ("가벼운 눈", "🌨️"),
        73: ("보통 눈", "🌨️"),
        75: ("강한 눈", "🌨️"),
        80: ("가벼운 소나기", "🌧️"),
        81: ("보통 소나기", "🌧️"),
        82: ("강한 소나기", "🌧️"),
        95: ("뇌우", "⛈️"),
        96: ("가벼운 우박 뇌우", "⛈️"),
        99: ("강한 우박 뇌우", "⛈️"),
    }
    return weather_codes.get(code, ("알 수 없음", "❓"))

# --- Streamlit 앱 UI ---
st.set_page_config(page_title="클릭! 날씨 확인 앱", page_icon="🗺️")
st.title("🗺️ 클릭! 날씨 확인 앱")
st.write("지도에서 위치를 클릭하면 해당 지역의 날씨 정보를 불러옵니다.")

# 1. 세션 상태 초기화 (지도 중심, 줌 레벨, 마커 위치)
if 'center' not in st.session_state:
    st.session_state.center = [36.5, 127.8]  # 대한민국 중심
if 'zoom' not in st.session_state:
    st.session_state.zoom = 7
if 'clicked_location' not in st.session_state:
    st.session_state.clicked_location = None

# 2. Folium 지도 생성
st.subheader("1. 지역 선택 (지도를 클릭하세요)")
m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)

# 만약 이전에 클릭한 위치가 있다면 마커 추가
if st.session_state.clicked_location:
    folium.Marker(
        st.session_state.clicked_location,
        popup="선택한 위치",
        tooltip="선택한 위치"
    ).add_to(m)

# 3. Streamlit-Folium으로 지도 렌더링 및 클릭 데이터 받기
# returned_objects=[] 파라미터를 제거하여 last_clicked가 기본으로 반환되도록 수정
map_data = st_folium(m, width="100%", height=500, key="folium_map")

# 4. 지도 클릭 이벤트 처리
# map_data가 None이 아니고, "last_clicked" 키가 있는지 확인
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    
    # 세션 상태 업데이트 (클릭한 위치로 중심 이동 및 줌)
    # 클릭한 위치가 이전과 다를 경우에만 rerun
    if st.session_state.clicked_location != [lat, lon]:
        st.session_state.center = [lat, lon]
        st.session_state.zoom = 10
        st.session_state.clicked_location = [lat, lon]
        
        # 페이지를 새로고침하여 지도에 마커를 즉시 반영
        st.rerun()

# 5. 날씨 정보 표시 (클릭된 위치가 있을 경우)
if st.session_state.clicked_location:
    lat, lon = st.session_state.clicked_location

    with st.spinner("날씨 정보를 가져오는 중..."):
        try:
            # 5-1. 위도/경도 -> 지역 이름 변환 (Reverse Geocoding)
            geo_params = {"latitude": lat, "longitude": lon, "format": "json"}
            
            # 여기서 requests.get이 REVERSE_GEOCODING_URL을 사용합니다.
            geo_response = requests.get(REVERSE_GEOCODING_URL, params=geo_params)
            geo_response.raise_for_status() # 404가 발생한 지점
            geo_data = geo_response.json()
            
            # API 응답에서 지역 이름 추출
            location_name = geo_data.get('display_name', f"위도: {lat:.2f}, 경도: {lon:.2f}")
            if 'address' in geo_data and geo_data['address']:
                # 주소에서 구, 시, 도 순서로 이름 찾기
                addr = geo_data['address']
                location_name = addr.get('city_district', 
                                  addr.get('city', 
                                    addr.get('state', 
                                      addr.get('country', location_name))))

            st.subheader(f"📍 {location_name}의 날씨")

            # 5-2. 위도/경도 -> 날씨 정보 조회
            weather_params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                "timezone": "auto" # 시간대 자동 설정
            }
            weather_response = requests.get(WEATHER_URL, params=weather_params)
            weather_response.raise_for_status()
            weather_data = weather_response.json()

            # 5-3. 현재 날씨 표시
            st.header("현재 날씨")
            current = weather_data["current_weather"]
            current_temp = current["temperature"]
            current_code = current["weathercode"]
            current_desc, current_icon = get_weather_info(current_code)

            st.metric(label=f"{current_desc} {current_icon}", value=f"{current_temp}°C")

            # 5-4. 주간 예보 표시
            st.header("주간 예보")
            daily_data = weather_data["daily"]
            forecast_cols = st.columns(7)
            
            for i in range(7):
                with forecast_cols[i]:
                    day_str = pd.to_datetime(daily_data['time'][i]).strftime('%a')
                    code = daily_data['weathercode'][i]
                    _, icon = get_weather_info(code)
                    max_temp = daily_data['temperature_2m_max'][i]
                    min_temp = daily_data['temperature_2m_min'][i]

                    st.write(day_str)
                    st.markdown(f"<div style='font-size: 2rem; text-align: center;'>{icon}</div>", unsafe_allow_html=True)
                    st.write(f"{max_temp:.0f}° / {min_temp:.0f}°")

        except requests.exceptions.RequestException as e:
            # 404 오류가 여기에 해당됩니다.
            st.error(f"API 호출 중 오류가 발생했습니다: {e}")
        except Exception as e:
            st.error(f"알 수 없는 오류가 발생했습니다: {e}")

else:
    st.info("지도를 클릭하여 날씨를 확인할 위치를 선택해 주세요.")


