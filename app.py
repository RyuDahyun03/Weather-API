# Weather-
import streamlit as st
import requests
import pandas as pd
import pydeck as pdk  # 지도 라이브러리 import
from datetime import datetime

# Open-Meteo API URL
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
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

def get_color_from_temp(temp):
    """
    온도에 따라 RGB 색상 코드를 반환합니다. (A=160, 반투명)
    """
    if temp <= 0:
        return [0, 0, 255, 160]  # 파랑
    elif temp <= 10:
        return [100, 149, 237, 160] # 연한 파랑
    elif temp <= 20:
        return [0, 255, 0, 160]  # 초록
    elif temp <= 25:
        return [255, 255, 0, 160] # 노랑
    elif temp <= 30:
        return [255, 165, 0, 160] # 주황
    else:
        return [255, 0, 0, 160]  # 빨강

# --- Streamlit 앱 UI ---
st.set_page_config(page_title="날씨 확인 앱", page_icon="☀️")
st.title("☀️ 날씨 확인 앱")

# 1. 도시 이름 입력
city = st.text_input("도시 이름을 영어로 입력하세요:", "Seoul")

if city:
    with st.spinner(f"'{city}'의 날씨 정보를 가져오는 중..."):
        try:
            # 2. 도시 이름 -> 위도/경도 변환 (Geocoding)
            geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
            geo_response = requests.get(GEOCODING_URL, params=geo_params)
            geo_response.raise_for_status()
            geo_data = geo_response.json()

            if not geo_data.get("results"):
                st.error(f"'{city}' 도시를 찾을 수 없습니다. 영문 이름을 확인해 주세요.")
            else:
                location = geo_data["results"][0]
                lat = location["latitude"]
                lon = location["longitude"]
                
                st.subheader(f"{location.get('name', city)}, {location.get('country_code', '')}의 날씨")

                # 3. 위도/경도 -> 날씨 정보 조회
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

                # 4. 현재 날씨 표시
                st.header("현재 날씨")
                current = weather_data["current_weather"]
                current_temp = current["temperature"]
                current_code = current["weathercode"]
                current_desc, current_icon = get_weather_info(current_code)

                st.metric(label=f"{current_desc} {current_icon}", value=f"{current_temp}°C")

                # --- (추가) Pydeck 지도로 위치 및 온도 표시 ---
                
                # 1. 지도용 데이터프레임 생성
                temp_color = get_color_from_temp(current_temp)
                map_df = pd.DataFrame({
                    'lat': [lat],
                    'lon': [lon],
                    'color': [temp_color],
                    'tooltip_text': [f"{city}: {current_temp}°C, {current_desc}"]
                })

                # 2. Pydeck 뷰 설정
                view_state = pdk.ViewState(
                    latitude=lat,
                    longitude=lon,
                    zoom=10,
                    pitch=50,
                )

                # 3. Pydeck 레이어 설정
                layer = pdk.Layer(
                    'ScatterplotLayer',
                    data=map_df,
                    get_position='[lon, lat]',
                    get_color='color',
                    get_radius=1000, # 미터 단위
                    pickable=True
                )
                
                # 4. 툴팁(tooltip) 설정
                tooltip = {
                   "html": "{tooltip_text}",
                   "style": {
                        "backgroundColor": "steelblue",
                        "color": "white"
                   }
                }

                # 5. Pydeck 맵 렌더링
                st.pydeck_chart(pdk.Deck(
                    map_style='mapbox://styles/mapbox/light-v9',
                    initial_view_state=view_state,
                    layers=[layer],
                    tooltip=tooltip
                ))
                # --- 지도 끝 ---

                # 5. 주간 예보 표시
                st.header("주간 예보")
                daily_data = weather_data["daily"]
                
                # 7일간의 예보를 컬럼으로 표시
                forecast_cols = st.columns(7)
                
                for i in range(7):
                    with forecast_cols[i]:
                        # 날짜를 '월(Mon)', '화(Tue)' 등으로 표시
                        day_str = pd.to_datetime(daily_data['time'][i]).strftime('%a')
                        
                        code = daily_data['weathercode'][i]
                        _, icon = get_weather_info(code)
                        
                        max_temp = daily_data['temperature_2m_max'][i]
                        min_temp = daily_data['temperature_2m_min'][i]

                        st.write(day_str)
                        st.markdown(f"<div style='font-size: 2rem; text-align: center;'>{icon}</div>", unsafe_allow_html=True)
                        st.write(f"{max_temp:.0f}° / {min_temp:.0f}°")

        except requests.exceptions.RequestException as e:
            st.error(f"API 호출 중 오류가 발생했습니다: {e}")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

