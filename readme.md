# MỘT BOT PHÁT NHẠC ĐƠN GIẢN HỖ TRỢ ĐA NGÔN NGỮ

---
![example_gif](https://i.ibb.co/gSjzpJ6/Thi-t-k-ch-a-c-t-n.gif)

### Cách cài đặt:

---
1. CLONE REPO NÀY VỀ
```
git clone -b Muti_language+database-support https://github.com/ShindouAris/ArisMusicBot.git
```
2. Cài đặt requirements
```
pip install -r requirements.txt
```
3. Đổi tên tệp example.env thành .env
```dotenv
# TOKEN của bot
TOKEN=ABC123456789
# Dùng để gọi bot: ?p <link>
PREFIX=?
# Để thành False nếu ko muốn sử dụng youtube
PLAY_YOUTUBE_SOURCE=True
# HIỂN THỊ ĐANG NGHE: ....
PRESENCE=ArisDev@MusicBot
```
4. Thêm lavalink vào bot của bạn (tệp lavalink.json)
```json
[
    {
      "name": "Example_lavalink WITHOUT SSL",
      "config": {
        "host": "lavalink.example.com",
        "port": 80,
        "password": "examplepassword",
        "secure": false
      }
    },
  {
    "name": "Example_lavalink WITH SSL",
    "config": {
      "host": "lavalink_ssl.example.com",
      "port": 443,
      "password": "examplepassword",
      "secure": true
    }
  }
]
```
5. Chạy bot và enjoy:

sử dụng
```
python3 main.py
```
hoặc
```
py main.py
```
