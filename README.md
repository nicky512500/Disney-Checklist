# Disney 宇宙片單 Checklist

可勾選追蹤觀影進度的 Disney / Pixar / Marvel / Star Wars / 20th Century / Searchlight / Disney Channel 片單。
進度存在瀏覽器 localStorage,各人獨立。

## 線上版

部署後請替換成你的網址。

## 本機開發

```bash
python3 fetch_disney.py        # 從 TMDb 抓取最新片單 → tmdb_data.json
python3 generate_checklist.py  # 生成 data.js
open index.html                # 本機預覽
```

`fetch_disney.py` 需要 `.env` 檔,內容:

```
TMDB_API_KEY=你的TMDb_API_KEY
```

## 部署的檔案

只有 `index.html` 與 `data.js` 會被部署。Python 腳本與原始 TMDb 資料只用於本機更新片單。
