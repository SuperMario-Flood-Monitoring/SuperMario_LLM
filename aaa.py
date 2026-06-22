

import requests
import json

# URL 문자열
url = 'https://apihub.kma.go.kr/api/json?authKey=lRjlhdTnT5mY5YXU58-ZBg'


# GET 요청
response = requests.get(url)

# 응답을 JSON 형태로 변환
json_response = response.json()

print(json_response)

#테스트 안녕하세요