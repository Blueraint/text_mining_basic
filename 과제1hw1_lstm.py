# Colab용 Blind 데이터 LSTM 감성분석 - KNU 감성사전 JSON 버전

# 1. 필수 라이브러리 설치
!pip install pandas tensorflow konlpy

# 2. 라이브러리 임포트
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout
from konlpy.tag import Okt
import json
import requests

# 3. KNU 감성사전 JSON 다운로드
json_url = "https://raw.githubusercontent.com/park1200656/knu_senti_dict/b0d535155374d4ca73d0fdcbf1cc6798f3bed6a6/SentiWord_info.json"
response = requests.get(json_url)
senti_data = json.loads(response.text)

# 4. JSON -> dict로 변환
senti_dict = {}
for k, v in senti_data.items():
    word = v['word']
    polarity = int(v['polarity'])
    senti_dict[word] = polarity

print(f"감성사전 로딩 완료, 단어 수: {len(senti_dict)}")

# 5. Blind 데이터 로딩
# CSV 예시: columns = ['id','body']
df = pd.read_csv('/content/blind_data.csv')

# 6. 감성 점수 기반 레이블 생성
okt = Okt()

def get_sentiment(text):
    tokens = okt.morphs(str(text))
    score_sum = 0
    for t in tokens:
        score_sum += senti_dict.get(t, 0)
    if score_sum > 0:
        return 1  # 긍정
    elif score_sum < 0:
        return 0  # 부정
    else:
        return 2  # 중립

df['label'] = df['body'].apply(get_sentiment)

# 중립 제거
df = df[df['label'] != 2]

# 데이터 분포 출력
print(df['label'].value_counts())

# 7. 토크나이저 처리
texts = df['body'].tolist()
labels = df['label'].values

tokenizer = Tokenizer(num_words=10000, oov_token="<OOV>")
tokenizer.fit_on_texts(texts)
sequences = tokenizer.texts_to_sequences(texts)

max_length = 100
X = pad_sequences(sequences, maxlen=max_length, padding='post')
y = np.array(labels)

# 8. 학습/검증 분리
from sklearn.model_selection import train_test_split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# 9. LSTM 모델 정의
model = Sequential([
    Embedding(input_dim=10000, output_dim=128, input_length=max_length),
    LSTM(64, return_sequences=False),
    Dropout(0.3),
    Dense(32, activation='relu'),
    Dense(1, activation='sigmoid')
])

# 10. 모델 컴파일
model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

# 11. 학습
history = model.fit(
    X_train, y_train,
    epochs=5,
    batch_size=32,
    validation_data=(X_val, y_val)
)

# 12. 평가
loss, acc = model.evaluate(X_val, y_val)
print(f"Validation Accuracy: {acc:.4f}")

# 13. 예측 예시
sample_texts = [
    "이자 부담이 너무 커서 매달 고통스럽습니다.",
    "이제는 조금 희망이 보입니다."
]
sample_seq = tokenizer.texts_to_sequences(sample_texts)
sample_pad = pad_sequences(sample_seq, maxlen=max_length, padding='post')
preds = model.predict(sample_pad)
for t, p in zip(sample_texts, preds):
    label = "긍정" if p > 0.5 else "부정"
    print(f"{t} => {label}")
